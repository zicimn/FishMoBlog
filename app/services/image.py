"""图片上传 / 删除的业务逻辑（Cloudinary）。

分层与并发约定：

- 抛 AppError 子类，绝不碰 HTTPException（与全项目一致）。
- PIL 解码与 Cloudinary 上传/销毁**都是同步阻塞**调用（后者基于 urllib3），
  必须走 run_in_threadpool；直接在协程里调用会把整个事件循环卡住，表现为
  「上传期间所有请求一起变慢」。
- 对外错误一律泛化：真实原因（太大的像素、损坏的文件、SDK 抛的响应体）
  只进日志。SDK 异常消息里带 cloud_name 与请求 URL，透传给前端等于泄露。

**关于限流**：这里原有一条「按用户 20 次/分钟」的限流，已按用户要求撤掉——
发布端只有管理员在用，账号本身可信，额度消耗由 Cloudinary 账户侧兜底。
撤掉后残余风险：管理员令牌若泄露，攻击者可无限量上传刷爆配额（原先限流能把它
压到 20/分钟）。补偿手段是 Cloudinary 的用量告警与令牌轮换，而不是再在代码里
加一道人人都会撞上的闸。
"""

import logging

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from utils import AppError, info
from utils.cloudinary import DEFAULT_FOLDER, destroy_image, upload_image_to_cloudinary

logger = logging.getLogger(__name__)

# 只允许销毁本应用命名空间下的资源。public_id 由前端回传，而 Cloudinary 账号
# 可能同时托管别的资源；不加前缀校验，等于「任何管理员都能删掉账号内任意资产」。
_ALLOWED_PREFIX = f"{DEFAULT_FOLDER}/"


class ImageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def Upload(self, image_b64: str):
        """校验并上传一张图片，返回 {"url", "public_id"}。"""
        result = await run_in_threadpool(
            upload_image_to_cloudinary, image_b64, DEFAULT_FOLDER
        )
        if not result:
            # 不区分「超像素 / 超体积 / 格式不支持 / 云端失败」：这些细节只留在
            # utils.cloudinary 的日志里，对外给一句可操作的提示即可。
            raise AppError("图片上传失败，请确认是有效的图片文件且不超过 5MB")

        return info(msg="上传成功", data=result)

    async def Delete(self, public_id: str):
        """销毁一张云端图片。幂等：资源不存在也按成功返回。"""
        if not public_id or not public_id.startswith(_ALLOWED_PREFIX):
            # 刻意不报错：调用方（前端）此时已经不再引用这张图，回错只会让用户
            # 重试一个本就不可能成功的操作。跨命名空间/空值一律只告警、不动手。
            logger.warning("拒绝销毁非本应用命名空间的资源: %r", public_id)
            return info(msg="删除成功")

        # destroy_image 内部不抛异常，失败只返回 False（清理是尽力而为）
        ok = await run_in_threadpool(destroy_image, public_id)
        if not ok:
            logger.warning("云端销毁未成功（可能已不存在）: public_id=%s", public_id)

        return info(msg="删除成功")
