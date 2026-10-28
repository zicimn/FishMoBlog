"""单张图片的 WEBP 转换与 Cloudinary 上传。

设计取舍：

- **只保留单图能力**。批量上传（原 convert_images_to_webp_bare /
  upload_images_to_cloudinary）已删除：现有调用方（文章封面、正文插图）都
  只需要一张；而批量路径还额外带两个坑——失败项被跳过会让返回下标与入参错位，
  且它只回传 url 把 public_id 丢了，资源此后再也删不掉。
- 入参是 base64 或 data-URI 字符串（前端 FileReader.readAsDataURL 的产物）。
- 上传是**同步阻塞**调用（cloudinary SDK 基于 urllib3 的 PoolManager），调用方
  必须放进线程池（见 services/image.py 的 run_in_threadpool），否则会阻塞整个
  事件循环。
- 失败一律返回 None，**不把上游异常原文交给调用方**：SDK 的异常消息里带
  Cloudinary 原始响应体与请求 URL，透传出去等于泄露 cloud_name 与内部参数。
"""

import base64
import io
import logging
import re
import warnings
from typing import Optional
from urllib.parse import unquote, urlsplit

from PIL import Image

from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
)

logger = logging.getLogger(__name__)

# 解码后的图片字节上限。
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# 像素上限。**必须同时赋给 Image.MAX_IMAGE_PIXELS**，否则这个常量只是一道事后
# 手写检查：PIL 在 open() 阶段用的是它自己的默认值（约 89.5M），且落在
# 89.5M~178M 之间时只发 DecompressionBombWarning、默认并不抛异常。实测一张
# 164KB 的 5000x10000 纯色 PNG 能解码出约 143MB 的 RGB 位图，而两道旧闸门都会放行。
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# base64 文本长度上限。必须在 b64decode **之前**检查：base64 比原始字节多出
# 1/3，若不前置拦截，一个巨大的字符串会先被完整解码进内存（峰值约为请求体的
# 2.75 倍），后面那道 5MB 的字节检查根本来不及拦。末尾留 1KB 余量给 data-URI 前缀。
MAX_IMAGE_B64_CHARS = (MAX_IMAGE_BYTES * 4) // 3 + 1024

# 上传/销毁超时（秒）。不给超时的话，线程池里被占住的工作线程可能长期挂死。
_REQUEST_TIMEOUT = 15

# 云端目录固定为模块常量：原实现由调用方传入且无任何校验，一旦接了用户输入
# 就是「在共享账号内任意命名空间写入」的越权面。
DEFAULT_FOLDER = "fishmo_upload"

_cloudinary_configured = False


def _get_cloudinary_uploader():
    """按需加载 cloudinary（惰性导入，未安装时仅在上传被调用时才报错）。"""
    global _cloudinary_configured
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError:
        raise ImportError(
            "使用 Cloudinary 上传功能需要安装依赖：pip install cloudinary"
        )
    if not _cloudinary_configured:
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET
        )
        _cloudinary_configured = True
    return cloudinary.uploader


def convert_image_to_webp(image: str, quality: int = 85, size: tuple = (800, 800)) -> Optional[str]:
    """将一张 base64（或 data-URI）图片转为 webp base64 字符串，任一环节不通过返回 None。

    注意返回值是 **base64 文本**而不是字节流，调用方需要自行拼 data-URI。
    """
    if not image:
        return None

    data = image.split(",", 1)[1] if "," in image else image

    # 前置长度闸：必须在 b64decode 之前，理由见 MAX_IMAGE_B64_CHARS。
    if len(data) > MAX_IMAGE_B64_CHARS:
        logger.warning("base64 输入过长（%d 字符），已拒绝", len(data))
        return None

    try:
        image_data = base64.b64decode(data)
    except Exception:
        # 用 validate=False 的默认行为即可；这里只记录「解码失败」，不回显原文
        logger.warning("base64 解码失败，已拒绝")
        return None

    if len(image_data) > MAX_IMAGE_BYTES:
        logger.warning("图片超过大小上限 %d 字节，已拒绝", MAX_IMAGE_BYTES)
        return None

    try:
        # simplefilter(error) 把 PIL 的 DecompressionBombWarning 升级成异常，配合
        # 上面已生效的 Image.MAX_IMAGE_PIXELS，把解压炸弹挡在真正解码之前。
        # load() 是为了在 try 内就把整个位图解出来：Image.open 是惰性的，若只是个
        # 损坏文件而不 load，异常会拖到后面才炸，报错位置就看不出真实原因了。
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(image_data))
            img.load()
            width, height = img.size

        # 纵深防御：PIL 的上限判定依赖 Image.MAX_IMAGE_PIXELS（模块级全局变量，
        # 可能被别处改写），这里再独立核一次像素数。
        if width * height > MAX_IMAGE_PIXELS:
            logger.warning("图片像素过大 %dx%d，已拒绝", width, height)
            return None

        # 带透明通道的模式统一走 RGBA，否则透明区会变成黑块；
        # P 模式只在真的带 transparency 时才需要保留 alpha，普通 P 图按 RGB 处理
        # （旧实现在这里把 L/P 一律转 RGBA，硬编码图会白白多出三个通道）。
        if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        img.thumbnail(size, Image.Resampling.LANCZOS)

        output = io.BytesIO()
        img.save(
            output, 
            format="WEBP", 
            quality=quality,
            method = 6,
            lossless = False
        )

        return base64.b64encode(output.getvalue()).decode("utf-8")

    except Exception:
        # 包含 DecompressionBombError / UnidentifiedImageError 等。一律不向调用方
        # 区分细节，避免把解析器内部信息带出去；堆栈只进日志。
        logger.warning("图片转换失败，已拒绝", exc_info=True)
        return None


def upload_image_to_cloudinary(image: str, folder: str = DEFAULT_FOLDER, size: tuple = (800, 800)) -> Optional[dict]:
    """上传单张图片到 Cloudinary。

    Returns:
        成功：``{"url": <secure_url>, "public_id": <public_id>}``；
        失败：``None``（原因只进日志，不外泄）。
    """
    webp_b64 = convert_image_to_webp(image=image, size=size)
    if not webp_b64:
        return None

    try:
        uploader = _get_cloudinary_uploader()
        result = uploader.upload(
            file=f"data:image/webp;base64,{webp_b64}",
            folder=folder,
            timeout=_REQUEST_TIMEOUT,
        )
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }
    except Exception:
        # 详细堆栈只进日志：SDK 异常消息里带 Cloudinary 原始响应体与请求 URL，
        # 透传给前端等于泄露 cloud_name 与内部参数（旧实现返回 str(e)）。
        logger.error("Cloudinary 上传失败", exc_info=True)
        return None


def destroy_image(public_id: str) -> bool:
    """销毁云端资源。

    Returns:
        成功 True；public_id 为空或销毁失败返回 False。

    刻意**不抛异常**：调用方是「换封面 / 删文章」这类主操作，云端清理失败不该
    把主操作一起带崩——残留一张孤儿图是可以接受的代价（只告警，便于运维补偿）。
    """
    if not public_id:
        return False
    try:
        uploader = _get_cloudinary_uploader()
        uploader.destroy(public_id, timeout=_REQUEST_TIMEOUT)
        return True
    except Exception:
        logger.warning("Cloudinary 资源清理失败（public_id 可能已不存在）", exc_info=True)
        return False


# 只认本应用上传产生的图片扩展名；末尾扩展名不属于 public_id，需要剥掉。
_IMAGE_EXT_RE = re.compile(r"\.(?:avif|gif|jpe?g|png|svg|webp)$", re.IGNORECASE)


def public_id_from_url(url: str) -> Optional[str]:
    """从本账号的 Cloudinary 图片 URL 反推 public_id；不认识的 URL 返回 None。

    正文 HTML 里只存了 URL（没有逐图的 public_id 列），编辑时对比新旧正文、
    清理被删掉/替换的图只能靠这一步反推。为免误删，判据是「三重归属」：

    1. 主机必须是 ``res.cloudinary.com``；
    2. 路径必须属于本账号（``/<cloud_name>/image/upload/``）；
    3. public_id 必须落在本应用的 ``fishmo_upload/`` 命名空间下。

    没有第 3 条的话，管理端正文里粘一条账号内其他资源的 URL 再删掉，就能销毁
    任意资产。这里与 ``ImageService.Delete`` 的前缀白名单是同一道闸。

    反推依赖 URL 拼接规则，**不能取代数据库里的 public_id 列**（封面仍用
    ``cover_public_id``）；它只服务「尽力清理孤儿图」，失败返回 None 即放弃。
    """
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or parts.netloc != "res.cloudinary.com":
        return None

    prefix = f"/{CLOUDINARY_CLOUD_NAME}/image/upload/"
    path = unquote(parts.path)
    if not path.startswith(prefix):
        return None

    # 我们的上传不带变换，URL 形如 /upload/v123/fishmo_upload/abc.webp；
    # 从 fishmo_upload/ 起截取，顺带容忍前面多出来的变换段与版本号。
    marker = f"{DEFAULT_FOLDER}/"
    rest = path[len(prefix):]
    index = rest.find(marker)
    if index < 0:
        return None

    tail = rest[index:]
    public_id = _IMAGE_EXT_RE.sub("", tail)
    # 只接受「本应用目录 + 资源名 + 图片扩展名」这一种形态：
    # - 只有目录（.../fishmo_upload/）或没有扩展名 → 不是完整资源，放弃；
    # - 目录项里出现空段 / . / .. → 可能是 %2F 之类的编码穿越，一律拒绝，
    #   否则「fishmo_upload/../other/x.webp」会绕过第 3 道归属检查。
    if not public_id or public_id == marker or public_id == tail:
        return None
    if "\\" in public_id or any(
        segment in ("", ".", "..") for segment in public_id.split("/")
    ):
        return None
    return public_id
