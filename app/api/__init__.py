from fastapi import APIRouter

from .article import router as article_router

service_router = APIRouter()

for r in (
    article_router,
):
    service_router.include_router(r)

__all__ = ["service_router"] 
