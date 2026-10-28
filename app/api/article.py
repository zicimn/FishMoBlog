from fastapi import APIRouter, Depends, Query, HTTPException

from deps import GetArticleService
from utils import AppError
from services import ArticleService

from typing import Optional

router = APIRouter(prefix="/article", tags=["article"])


@router.get("/")
async def list_articles(
    page: int = Query(1, ge=1),
    size: int = Query(16, ge=1, le=50),
    category_name: Optional[str] = Query(None,max_length=200),
    service: ArticleService = Depends(GetArticleService),
):
    try:
        return await service.GetList(page, size,category_name)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)



# 通过 path(slug) 获取。动态兜底路由必须注册在最后。
@router.get("/{path}")
async def get_article_by_path(
    path: str,
    service: ArticleService = Depends(GetArticleService),
):
    try:
        return await service.GetSlug(path)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)