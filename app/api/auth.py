from fastapi import APIRouter, Depends, HTTPException, Request

from schemas import LoginRequest, RegisterRequest, SendCodeRequest

from services import AuthService, EmailService
from deps import GetAuthService, GetEmailService

from utils import AppError, TokenPayload, get_token_payload

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/email-code")
async def send_email_code(
    data: SendCodeRequest,
    request: Request,
    service: EmailService = Depends(GetEmailService),
):
    """发送注册验证码。

    响应里**只有** ``expires_in``：验证码若回显，任何人填别人的邮箱就能拿码注册，
    邮箱验证就彻底失去意义（审核红线 S2）。
    """
    try:
        return await service.SendCode(data.email, request)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post("/register")
async def register(
    data: RegisterRequest,
    request: Request,
    service: AuthService = Depends(GetAuthService),
):
    """访客自助注册，成功即签发令牌（响应与登录同构）。"""
    try:
        return await service.Register(data, request)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    service: AuthService = Depends(GetAuthService),
):
    try:
        return await service.Login(data, request)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post("/logout")
async def logout(
    payload: TokenPayload = Depends(get_token_payload),
    service: AuthService = Depends(GetAuthService),
):
    try:
        return await service.Logout(payload)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)