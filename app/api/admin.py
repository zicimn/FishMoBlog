from typing import Optional

from fastapi import Depends,APIRouter,HTTPException,Query

from deps import GetArticleService, GetAdminUser, GetImageService,GetComService
from services import ArticleService, ImageService,ComService
from utils import AppError
from schemas import ArticleSaveRequest,ArticleEditRequest,ImageUploadRequest

# 整个后台分组挂 GetAdminUser：五个端点都是管理操作，逐个加依赖容易漏。
# 用 router 级 dependencies 保证没有任何一个端点被裸奔注册。
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(GetAdminUser)],
)


@router.post("/article/save")
async def save(
    data: ArticleSaveRequest,
    service: ArticleService = Depends(GetArticleService),
):
    try:
        return await service.Save(data=data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code,detail=e.msg)


@router.delete("/article/remove/{id}")
async def delete(
    id:int,
    service:ArticleService = Depends(GetArticleService)
):
    try:
        return await service.Remove(id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code,detail=e.msg)


@router.put("/article/edit/{id}")
async def edit(
    id:int,
    data:ArticleEditRequest,
    service:ArticleService = Depends(GetArticleService)
):
    try:
        return await service.Edit(id,data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code,detail=e.msg)


# 列表端点必须注册在 /article/{id} 之前：Starlette 按注册顺序匹配，
# 排在后面的话 "list" 会被当作 {id} 去解析 int，直接 422。
@router.get("/article/list")
async def list_articles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[int] = Query(None, ge=1, le=3),
    keyword: Optional[str] = Query(None, max_length=100),
    category_name: Optional[str] = Query(None, max_length=200),
    service: ArticleService = Depends(GetArticleService),
):
    try:
        return await service.AdminList(page, size, status, keyword, category_name)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.get("/article/{id}")
async def get_article_by_id(
    id: int,
    service: ArticleService = Depends(GetArticleService),
):
    try:
        # status=True：后台要能读隐藏与草稿；前台「只看对外可见」的语义
        # 由 GetId 的默认参数保留给客户端详情使用。
        return await service.GetId(id, status=True)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)

# ---- 图片上传 / 删除 -------------------------------------------------------
# 放在 admin 分组下是刻意的：上传是写操作，必须要求管理员身份。
# 若挂到 api/article.py（公开无鉴权的读路由），等于开了一个匿名可用的上传口，
# 会被刷爆 Cloudinary 配额、变成免费图床，还可能被塞违规内容。
# 路径第二段是 upload，与 /article/... 不冲突，也不会被任何动态兜底路由吃掉。


@router.post("/upload/image")
async def upload_image(
    data: ImageUploadRequest,
    service: ImageService = Depends(GetImageService),
):
    # 管理守卫由 router 级 dependencies=[Depends(GetAdminUser)] 统一提供，
    # 这里不再注入 user —— 原先注入只是为了给「按用户限流」取 user.id，
    # 限流已撤掉，留一个没人用的参数只会让人以为这里另有一道校验。
    try:
        return await service.Upload(data.image)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


# public_id 形如 fishmo_upload/abc123，**含斜杠**，做不了路径参数，只能走 query。
# 前端需对它做 encodeURIComponent（useApi 的 query 通道已处理）。
@router.delete("/upload/image")
async def delete_image(
    public_id: str = Query(..., min_length=1, max_length=255),
    service: ImageService = Depends(GetImageService),
):
    try:
        return await service.Delete(public_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)



