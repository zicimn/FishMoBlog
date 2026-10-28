"""图片接口的入参模型。

上传走 base64 JSON（前端 FileReader.readAsDataURL 的产物），不引入 multipart：
现有 useApi 只有 JSON body 通道，multipart 要另起一套请求逻辑。

max_length 这里是**服务端兜底**，真正的前置长度闸在
utils/cloudinary.MAX_IMAGE_B64_CHARS（约 7.0M 字符），比这里更严；Pydantic 这层
仍要留着——它在请求体解析之后、进入业务之前生效，能拦住超长字符串继续往下流。
"""

from pydantic import BaseModel, Field


class ImageUploadRequest(BaseModel):
    image: str = Field(
        max_length=8 * 1024 * 1024,
        description="base64 或 data-URI 图片字符串",
    )
