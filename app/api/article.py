from fastapi import APIRouter,Depends,Query,HTTPException

from deps import GetArticleService
from err import AppError
from services import ArticleService


router = APIRouter(prefix="/articles",tags=["blog:article"])

@router.get("/")
async def list_articles(
    page:int = Query(1),
    size:int = Query(16,),
    service: ArticleService = Depends(GetArticleService)
):
    try:
        return await service.GetList(page,size)
    except AppError as e:
        raise HTTPException(status_code=e.status_code,detail=e.msg)


@router.get("/{id}")
async def list_articles(
    id:int,
    service: ArticleService = Depends(GetArticleService)
):
    try:
        return await service.Get(id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code,detail=e.msg)
