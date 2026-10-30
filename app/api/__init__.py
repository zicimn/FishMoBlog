from fastapi import APIRouter

from .article import router as article_router
from .auth import router as auth_router
from .user import router as user_router
from .comments import router as comments_router
from .admin import router as admin_router
from .msg import router as msg_router

service_router = APIRouter()

# 顺序说明：article 的 `/{path}` 是动态兜底路由，已由 article_router 内部保证
# 排在最后；各 router 前缀互不相同（/article、/auth、/comments、/admin），
# 跨 router 不会互相吞路径。这里按「前台 → 后台」排布。
for r in (
    article_router,
    auth_router,
    user_router,
    comments_router,
    admin_router,
    msg_router,
):
    service_router.include_router(r)

__all__ = ["service_router"]