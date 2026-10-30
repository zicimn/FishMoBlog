from fastapi import APIRouter, Depends, HTTPException, Query, Request

from deps import GetMsgService, GetCurrentUser
from models import User
from schemas import MsgCreateRequest
from services import MsgService
from utils import AppError

router = APIRouter(prefix="/msg", tags=["msg"])


@router.get("/list")
async def list_msg(
    p: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=50),
    service: MsgService = Depends(GetMsgService),
):
    try:
        return await service.MGetList(page=p, size=size)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.post("")
async def save(
    data: MsgCreateRequest,
    request: Request,
    service: MsgService = Depends(GetMsgService),
    user: User = Depends(GetCurrentUser),
):
    client_ip = request.client.host if request.client else "unknown"
    try:
        return await service.MCreate(data, user, client_ip)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)


@router.delete("/del")
async def dele(
    id: int = Query(..., ge=1, description="留言 ID"),
    service: MsgService = Depends(GetMsgService),
    user: User = Depends(GetCurrentUser),
):
    try:
        return await service.MRemove(id, user)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.msg)