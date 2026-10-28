from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_db
from models import User
from services import (
    ArticleService,
    AuthService,
    CatService,
    ComService,
    ImageService,
    EmailService,
)
from utils import TokenPayload, get_token_payload

async def GetCurrentUser(
    payload: TokenPayload = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """取当前登录用户实体，供需要登录态的端点使用。

    get_token_payload 只保证令牌本身（签名 / 有效期 / 黑名单）有效，账号可能
    已被禁用或删除，所以这里再查一次库。失败一律 401：调用方是无状态令牌，
    让前端统一走「重新登录」分支，不泄露账号是否存在。
    """
    user = await db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    # 用户表未导出状态常量，沿用 auth.py 的写法：1 为正常
    if user.status != 1:
        raise HTTPException(status_code=401, detail="账号已被禁用")
    return user


async def GetAdminUser(
    user: User = Depends(GetCurrentUser),
) -> User:
    """在 GetCurrentUser 之上再要求管理员身份（is_admin 为真）。

    后台写接口（api/admin.py）必须挂它：否则匿名请求即可增删改文章。
    非管理员返回 403 而非 401——调用方已通过令牌校验，缺的是权限不是身份。
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


async def GetArticleService(
    db: AsyncSession = Depends(get_db)
):
    return ArticleService(db)

async def GetAuthService(
    db:AsyncSession = Depends(get_db)
):
    return AuthService(db)

async def GetImageService(
    db: AsyncSession = Depends(get_db)
):
    return ImageService(db)

async def GetEmailService():
    """验证码服务不碰数据库，因此不注入 AsyncSession（少开一个连接）。"""
    return EmailService()


async def GetCatService(
    db:AsyncSession = Depends(get_db)
):
    return CatService(db)

async def GetComService(
    db:AsyncSession = Depends(get_db)
):
    return ComService(db)