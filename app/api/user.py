from fastapi import APIRouter, Depends, HTTPException, Request

from deps import GetCurrentUser, GetEmailService, GetUserService
from models import User
from schemas import UserDeleteRequest, UserEditRequest
from services import EmailService, UserService
from utils import AppError

router = APIRouter(prefix="/user", tags=["user"])


@router.put("/profile")
async def edit_profile(
    data: UserEditRequest,
    user: User = Depends(GetCurrentUser),
    service: UserService = Depends(GetUserService),
):
    """修改当前登录用户的资料（用户名 / 头像 / 简介）。

    身份只取自 ``GetCurrentUser``：请求体里没有 user_id，改不到别人。
    """
    try:
        return await service.Edit(user, data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post("/delete-code")
async def send_delete_code(
    request: Request,
    user: User = Depends(GetCurrentUser),
    service: EmailService = Depends(GetEmailService),
):
    """向当前账号邮箱发送注销验证码（purpose=delete）。

    放在登录态下而不是复用公开的 ``POST /auth/email-code``：后者能向任意
    邮箱投递邮件，若放开 delete 用途，匿名请求就能给受害者发「注销账号」
    警告邮件。收件地址由服务端取 ``user.email``，不接受客户端指定。
    """
    try:
        return await service.SendCode(user.email, request, purpose="delete")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.delete("/self")
async def remove_self(
    data: UserDeleteRequest,
    user: User = Depends(GetCurrentUser),
    service: UserService = Depends(GetUserService),
):
    """凭邮箱验证码注销当前账号（不可恢复）。

    验证码必须与 ``POST /user/delete-code`` 同用途：注册码不能拿来注销。
    成功后前端应清掉本地令牌；服务端不额外拉黑 jti，下一请求查不到用户会 401。
    """
    try:
        return await service.RemoveSelf(user, data.code)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)