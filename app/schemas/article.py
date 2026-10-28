#文章列表页面
from pydantic import BaseModel, field_validator
from typing import Optional



# —— 「本地占位图」防漏闸 ——
# 前端正文插图与封面都改成「点保存时才上传」：选图阶段先在本地下 objectURL 占位
# （正文里的 <img src="blob:..." data-pending-upload="k1">），点保存时才 flush 上传、
# 把 src 换成真实 url 再提交。若哪条路径漏了这一步（比如编辑器组件卸载、fire-and-forget
# 的提交分支），库里就会存下 blob: URL —— 它只对创建它的那个浏览器会话有效，前台渲染必然
# 404，而且事后修不回来（原始文件在用户机器上，云端没有任何副本）。
# 这里硬拦一道，让「漏 flush」变成一次可见的 422，而不是一次静默的数据损坏。
_PENDING_MARKER = "data-pending-upload"
_BLOB_SRC_MARKERS = ('src="blob:', "src='blob:")
_BLOB_SCHEME = "blob:"


def _reject_pending_images(value: Optional[str]) -> Optional[str]:
    """拒绝含有未上传占位标记的字段值。

    两类字段的形态不同，故分两种判据：

    - **正文（HTML 片段）**：占位图长成 ``<img src="blob:..." data-pending-upload="k1">``，
      按「属性形态」匹配（``data-pending-upload`` / ``src="blob:``）。
      刻意不用「正文里出现 blob: 就拒绝」这种宽判据 —— 一篇讲 objectURL 的文章
      在代码块里正常带着 ``blob:`` 文本，宽判据会把正常内容一起拦下。
    - **封面（裸 URL）**：值本身就是 url，没有 HTML 外壳，故按「scheme 前缀」匹配。

    误伤评估：`data-pending-upload` 是本项目自造属性；裸值以 `blob:` 开头只可能是
    objectURL。两者都只在「漏了 flush」这一种情况下命中。
    """
    if not value:
        return value
    if _PENDING_MARKER in value or any(m in value for m in _BLOB_SRC_MARKERS):
        raise ValueError("检测到未上传的本地图片占位，请重新选择图片后再保存")
    if value.lstrip().lower().startswith(_BLOB_SCHEME):
        raise ValueError("检测到未上传的本地图片占位，请重新选择图片后再保存")
    return value


class ArticleSaveRequest(BaseModel):
    title: str
    path: Optional[str] = None
    description: str
    # 封面改为可选：正文可以先没图，也可以是纯外链。空串 / null 由 service 归一成
    # None，避免库里出现 "" 与 NULL 两种「没有封面」的表达。
    cover: Optional[str] = None
    # 前端上传成功后回带的云端资源标识，用于日后换图/删文时清理
    cover_public_id: Optional[str] = None
    content: str
    status: int = 1
    category_name : str

    @field_validator("content", "cover")
    @classmethod
    def _no_pending_images(cls, value: Optional[str]) -> Optional[str]:
        return _reject_pending_images(value)


class ArticleEditRequest(BaseModel):
    title: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None
    # 注意语义：这是**可空字段**，service 侧按「键是否出现在请求体里」判断要不要改
    # （显式传 null = 清空，键不传 = 保持原值）。前端要清空封面必须显式发 cover: null。
    cover: Optional[str] = None
    cover_public_id: Optional[str] = None
    content: Optional[str] = None
    # 与 Article.status(int) 对齐：类型写成 str 会让 "1" 进 int 列，
    # MySQL 宽松模式下静默转换、严格模式下报错，两种都不该发生。
    status: Optional[int] = None
    category_name : Optional[str] = None

    @field_validator("content", "cover")
    @classmethod
    def _no_pending_images(cls, value: Optional[str]) -> Optional[str]:
        return _reject_pending_images(value)



def to_preview(article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "path": article.path,
        "description": article.description,
        "cover": article.cover,
        "style": article.style,
        "views": article.views,
        "created_at": article.created_at,
    }


#文章详情页面
def to_detail(article) -> dict:
    return {
        "id": article.id,
        "path": article.path,
        "cover": article.cover,
        "title": article.title,
        "description": article.description,
        "content": article.content,
        "style": article.style or None,
        "views":article.views,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


#后台文章列表：与前台 to_preview 的差异只在多带 status / category_id / updated_at，
# 管理端要靠它们区分正常、隐藏、草稿并做筛选展示。
def to_admin_preview(article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "path": article.path,
        "description": article.description,
        "cover": article.cover,
        "style": article.style,
        "status": article.status,
        "category_id": article.category_id,
        "views": article.views,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


#后台文章详情：to_detail 不含 status，编辑表单就回填不了「正常/隐藏/草稿」，
# 这里补上 status 与 category_id。
# 刻意不给分类名：GetId 带了 noload(Article.category)，异步下访问
# article.category.name 会触发懒加载直接报错；需要名字由前端用 category_id 映射。
def to_admin_detail(article) -> dict:
    data = to_detail(article)
    data["status"] = article.status
    data["category_id"] = article.category_id
    # to_detail 是前台详情用的，签名里没有封面；后台编辑表单必须能回填封面，
    # 否则每次编辑都在「看不见封面」的状态下提交，一保存就把封面覆盖掉。
    data["cover_public_id"] = article.cover_public_id
    return data