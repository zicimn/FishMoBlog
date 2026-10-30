from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import Msg


class MsgCreateRequest(BaseModel):
    """留言入参。

    作者身份与来源 IP 一律由服务端填充（登录态 + 连接信息），前端只传内容。
    内容在 service 层经 ``sanitize_html`` 白名单消毒后落库（与评论同一套规则），
    因此返回的 ``content`` 是安全 HTML 子集，前端可按评论的方式用 ``v-html`` 渲染。
    """

    # 拒绝 user_id / ip 等多余字段：身份与来源只能由服务端填充，
    # 客户端再传直接 422，避免「看起来能指定作者」的误解。
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        stripped = (v or "").strip()
        if not stripped:
            raise ValueError("留言内容不能为空")
        return stripped


def to_mdetail(msg: Msg) -> dict:
    """公开留言结构。

    刻意不返回 ``ip``：它是只用于审计的库内字段，公开列表匿名可读，
    把它带出去等于把留言者的网络地址交给任何爬虫。
    """
    return {
        "id": msg.id,
        "user_id": msg.user_id,
        "content": msg.content,
        "username": msg.username,
        "avatar": msg.avatar,
        "created_at": msg.created_at,
    }