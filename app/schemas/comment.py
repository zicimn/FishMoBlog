from typing import Optional,List

from pydantic import AliasChoices, BaseModel, Field, field_validator


class CommentCreateRequest(BaseModel):
    """发表评论入参。作者身份一律取自登录态，前端不得传昵称/邮箱/头像。

    宽容解析：前端是独立仓库、无法核实其字段命名，所以文章标识同时接受
    ``article_id`` / ``articleId`` / ``path``，父评论同时接受 ``parent_id`` /
    ``parentId``（``AliasChoices`` 只作用于入参校验，不影响序列化——本模型
    从不出现在响应里）。等前端确认后可删掉多余别名，只留一种。
    """

    content: str = Field(min_length=1, max_length=2000)
    # slug 或数字 id 都接受，最终由 service 层解析（先查 path 再退化为 id）。
    # 这里设为可选：兼容旧的「路径参数版」端点（文章标识在 URL 上），
    # 由新端点在路由层强制要求 body 里必须带上标识。
    article: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("article_id", "articleId", "path"),
    )
    parent_id: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("parent_id", "parentId"),
    )

    @field_validator("content")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        # 纯空白内容等价于空评论；挡在 Pydantic 层，由 FastAPI 统一返回 422，
        # 避免在 service 里再造一个 400 类异常（AppError 体系没有 400）。
        stripped = (v or "").strip()
        if not stripped:
            raise ValueError("评论内容不能为空")
        return stripped


def to_comment_result(comment) -> dict:
    """发表/删除评论接口的返回结构。

    刻意不复用 ``to_item``：后者读取模型上不存在的 ``user_website`` / ``area``，
    调用会直接抛 AttributeError。
    """
    return {
        "id": comment.id,
        "articleId": comment.article_id,
        "parentId": comment.parent_id if comment.parent_id else "",
        "userName": comment.user_name,
        "userAvatar": comment.user_avatar or "",
        "content": comment.content,
        "contentText": comment.content_text or "",
        "status": comment.status,
        "createdDate": comment.created_at,
    }


def to_item(comment, children: Optional[List[dict]] = None, reply_name: Optional[str] = None) -> dict:
    """博客端评论结构（``CommentItemInterface``）。

    ``userWebsite`` / ``area`` 是前端已在消费的响应键，但模型上并没有对应列
    （也不打算新增）。这里恒返回空字符串，保证键存在、类型稳定，且**不再**
    访问不存在的 ``comment.user_website`` / ``comment.area``（原写法调用即
    AttributeError）。
    """
    return {
        "id": comment.id,
        "userName": comment.user_name,
        "userWebsite": "",
        "userAvatar": comment.user_avatar or "",
        "content": comment.content,
        "parentId": comment.parent_id if comment.parent_id else "",
        "replyName": reply_name or "",
        "createdDate": comment.created_at,
        "area": "",
        "child": children or [],
    }


def to_top_item(comment, article_path: str = "", article_title: str = "") -> dict:
    """侧边栏「最新评论」条目：在 ``to_item`` 基础上补上所属文章信息。

    ``articleId`` / ``articlePath`` / ``articleTitle`` 是本次新增的键——没有它们
    侧边栏就没法拼出跳转链接（前端路由走 slug，不是数字 id）。若前端已约定
    别的键名，改这里即可。
    """
    item = to_item(comment)
    item.update(
        articleId=comment.article_id,
        articlePath=article_path or "",
        articleTitle=article_title or "",
    )
    return item