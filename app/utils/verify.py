import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import ALGORITHM, SECRET_KEY, is_token_blacklisted

logger = logging.getLogger(__name__)


# auto_error=False：未带令牌时返回 None 而不是直接 403，
# 便于把「缺少令牌」和「令牌无效」统一成同一种 401 响应。
security = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# 令牌有效期（天）
TOKEN_EXPIRE_DAYS = 7

# 进程启动时算一次的假哈希：账号不存在时也跑一遍等价开销的校验，
# 否则「邮箱不存在」会微秒级返回、而「存在」要走完整 argon2id（数十毫秒），
# 响应时间差 3 个数量级，足以被用来枚举已注册邮箱。
DUMMY_PASSWORD_HASH = pwd_context.hash("timing-equalization-placeholder")


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    jti: str
    exp: datetime

    def remaining_seconds(self) -> int:
        return int((self.exp - datetime.now(timezone.utc)).total_seconds())


def create_access_token(user_id: int, username: str) -> str:
    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail="服务端未配置 SECRET_KEY")

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": uuid4().hex,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[TokenPayload]:
    if not SECRET_KEY:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    jti = payload.get("jti")
    if not jti:
        return None

    exp = payload.get("exp")
    try:
        expire_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None

    return TokenPayload(user_id=user_id, jti=str(jti), exp=expire_at)


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenPayload:
    """解析并校验令牌，返回其载荷（含 jti，供登出时拉黑）。"""
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    try:
        revoked = await is_token_blacklisted(payload.jti)
    except Exception:
        # Redis 不可用时不阻断正常请求，但必须告警，否则登出静默失效无人知晓。
        logger.error("令牌黑名单查询失败（Redis 不可用），本次未做登出校验", exc_info=True)
        revoked = False

    if revoked:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    return payload


async def verify_login(
    payload: TokenPayload = Depends(get_token_payload),
) -> int:
    return payload.user_id


async def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return await run_in_threadpool(pwd_context.verify, plain, hashed)
    except Exception:
        return False


async def hash_password(plain: str) -> str:
    return await run_in_threadpool(pwd_context.hash, plain)