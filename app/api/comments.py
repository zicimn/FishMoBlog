from fastapi import APIRouter, Depends, HTTPException, Query, Request

from deps import GetComService, GetCurrentUser
from models import User
from schemas import CommentCreateRequest
from services.comment import ComService
from utils import AppError

router = APIRouter(prefix="/comments", tags=["comment"])


# 注意顺序：/top 是具体路径，必须注册在动态兜底 /{path} **之前**。
# Starlette 按注册顺序匹配，排后面的话 "top" 会被当成文章 path（同 /article 的约束）。
@router.get("/top", summary="最新评论（侧边栏，公开）")
async def top_comments(
    limit: int = Query(5, ge=1, le=20),
    service: ComService = Depends(GetComService),
):
    """按时间倒序取少量正常评论，供侧边栏展示。"""
    try:
        return await service.GetTop(limit)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.get("/{path}", summary="文章的评论列表（公开）")
async def list_comments(
    path: str,
    p: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=50),
    service: ComService = Depends(GetComService),
):
    """返回该文章下的评论树（顶层评论分页，回复一次性带出）。

    不需要登录：访客也要能看评论，因此这里不挂 GetCurrentUser。
    文章标识接受 slug 或数字 id（由 service 层先按 path、再退化为 id 解析）。
    """
    try:
        return await service.GetList(path, p, size)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post("", summary="发表评论（需登录）")
async def create_comment(
    data: CommentCreateRequest,
    request: Request,
    service: ComService = Depends(GetComService),
    user: User = Depends(GetCurrentUser),
):
    """文章标识从 body 取（``article_id`` / ``articleId`` / ``path``，slug 或数字 id 皆可）。

    body 只带 content / 文章标识 / parent_id，作者取自登录态；
    ``GetCurrentUser`` 未登录/账号不可用时抛 401。
    """
    if not data.article:
        # 校验期挡掉「body 里没带文章标识」，语义同 422
        raise HTTPException(
            status_code=422,
            detail="缺少文章标识（article_id / articleId / path）",
        )

    client_ip = request.client.host if request.client else "unknown"
    try:
        return await service.Create(data.article, data, user, client_ip)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post(
    "/{path}",
    summary="发表评论（路径参数版，兼容旧前端）",
    deprecated=True,
)
async def create_comment_by_path(
    path: str,
    data: CommentCreateRequest,
    request: Request,
    service: ComService = Depends(GetComService),
    user: User = Depends(GetCurrentUser),
):
    """旧形态：文章 slug 在路径参数上，body 只需 content / parent_id。

    保留它只是为了那批「前端还没确认」的调用方；等前端切到 ``POST /comments``
    后即可整段删除。
    """
    client_ip = request.client.host if request.client else "unknown"
    try:
        return await service.Create(path, data, user, client_ip)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.delete("/{comment_id}", summary="删除评论（作者本人或管理员，级联删子孙）")
async def delete_comment(
    comment_id: int,
    service: ComService = Depends(GetComService),
    user: User = Depends(GetCurrentUser),
):
    try:
        return await service.Remove(comment_id, user)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)