import asyncio
import logging

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import blacklist_token, rate_limit
from models import User
from schemas import LoginRequest, RegisterRequest, to_user_info
# 指向子模块而不是 services 包：services/__init__.py 会先 import .email 再 import
# .auth，若这里写 `from services import EmailService`，在包尚未初始化完时取属性
# 会触发循环导入（同一个坑在 services/article.py 顶部有说明）。
from services.email import EmailService
from utils import (
    DUMMY_PASSWORD_HASH,
    TokenPayload,
    create_access_token,
    hash_password,
    verify_password,
    Busy, PwdError, OpError,
    info
)

logger = logging.getLogger(__name__)

# IP 维度放宽（同一出口 IP 后面可能有很多人），账号维度收紧
_LOGIN_RATE_MAX_IP = 60
_LOGIN_RATE_MAX_ACCOUNT = 10
_LOGIN_RATE_WINDOW = 300

# 注册限流：只按 IP（注册没有「账号」维度可言），额度比登录更紧
_REGISTER_RATE_MAX_IP = 5
_REGISTER_RATE_WINDOW = 3600


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def Login(
        self,
        data: LoginRequest,
        request: Request,
    ):
        email = (data.email or "").strip()
        client_ip = request.client.host if request.client else "unknown"

        # IP 与账号双维度限流：只按 IP 时，单用户打满额度会把同 IP 的用户全部挡在门外，
        # 且换代理即可绕过；只按账号时挡不住分布式撞库。
        rate_keys = [f"login:ip:{client_ip}"]
        limits = [_LOGIN_RATE_MAX_IP]
        if email:
            rate_keys.append(f"login:acct:{email.lower()}")
            limits.append(_LOGIN_RATE_MAX_ACCOUNT)

        try:
            allowed = all(
                await asyncio.gather(
                    *(
                        rate_limit(key, max_attempts=limit, window_seconds=_LOGIN_RATE_WINDOW)
                        for key, limit in zip(rate_keys, limits)
                    )
                )
            )
        except Exception:
            # Redis 不可用不应该导致无法登录，但必须告警而不是静默降级
            logger.error("登录限流检查失败（Redis 不可用），本次未限流", exc_info=True)
            allowed = True

        if not allowed:
            raise Busy("尝试过于频繁，请稍后再试")

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().one_or_none()

        # 先统一校验密码再判断账号状态：账号不存在时也跑一次等价开销的校验，
        # 避免通过响应内容或响应时间差异探测出哪些邮箱已注册。
        password_ok = await verify_password(
            data.password or "",
            user.password_hash if user else DUMMY_PASSWORD_HASH,
        )
        if user is None or not password_ok:
            raise PwdError("邮箱或者密码错误")

        if user.status != 1:
            raise OpError("账号已被禁用")

        token = create_access_token(user.id, user.username)

        # token 走响应体而非 Authorization 响应头：跨源场景下自定义响应头默认对 JS
        # 不可见，必须额外声明 Access-Control-Expose-Headers，容易漏配。
        data = {"access_token": token, "token_type": "bearer", **to_user_info(user)}
        return info(data=data)

    async def Register(
        self,
        data: RegisterRequest,
        request: Request,
    ):
        """访客自助注册（硬注册：必须先通过邮箱验证码）。

        ``is_admin`` / ``status`` 一律在服务端写死（0 / 1），绝不取自请求体——
        RegisterRequest 里根本没有这两个字段，从源头堵住提权。
        密码强度由 RegisterRequest 在 Pydantic 层施加（此处只负责哈希存储）。

        验证码消费时机见 ``EmailService.VerifyCode`` 的说明（S7）：校验通过即
        删码，随后才建号；建号撞唯一索引时验证码已消耗，需要重新获取。
        """
        client_ip = request.client.host if request.client else "unknown"

        try:
            allowed = await rate_limit(
                f"register:ip:{client_ip}",
                max_attempts=_REGISTER_RATE_MAX_IP,
                window_seconds=_REGISTER_RATE_WINDOW,
            )
        except Exception:
            # Redis 不可用不应导致无法注册（与限流「失败开放」的既有取向一致），
            # 但必须告警，不能静默降级。
            logger.error("注册限流检查失败（Redis 不可用），本次未限流", exc_info=True)
            allowed = True

        if not allowed:
            raise Busy("注册过于频繁，请稍后再试")

        email = data.email.strip()
        username = data.username

        # 硬注册：先验码、再查重。顺序是刻意选的——若把查重放在前面，任何人都能
        # 在没拿到验证码的情况下用「邮箱或用户名已被注册」探测某个邮箱是否注册；
        # 放到验证码之后，探测者必须先真正控制该邮箱（收到码）才能得知结果。
        # 代价是「已注册用户」也会先消耗一个验证码，这个代价比开放枚举更可接受。
        await EmailService().VerifyCode(email, data.code)

        # 快路径：先查重，给出友好提示（同时命中任一唯一索引即拒）
        exists = await self.db.execute(
            select(User).where((User.email == email) | (User.username == username))
        )
        if exists.scalars().first() is not None:
            raise OpError("邮箱或用户名已被注册")

        # argon2 很慢，hash_password 内部走 run_in_threadpool，不能阻塞事件循环
        password_hash = await hash_password(data.password)

        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            is_admin=0,  # 服务端写死：人人都是访客
            status=1,    # 服务端写死：注册后立即可登录
        )
        self.db.add(user)

        try:
            # 显式 commit：get_db 只在 session 还有 new/dirty/deleted 时才提交，
            # 而 flush/commit 之后这些集合都会清空，靠 get_db 兜底会静默丢失。
            # 另：commit 会顺带 flush，user.id 在此行之后才可用（expire_on_commit=False，值不外抛后失效）。
            await self.db.commit()
        except IntegrityError:
            # 「先查后插」存在竞态，唯一索引才是最终防线；此处回滚并返回友好错误而不是 500。
            await self.db.rollback()
            logger.warning("注册唯一约束冲突（并发竞态）")
            raise OpError("邮箱或用户名已被注册")

        token = create_access_token(user.id, user.username)
        # 与登录同构：注册即签发令牌，省掉前端一次往返；响应里绝不含 password_hash。
        payload = {"access_token": token, "token_type": "bearer", **to_user_info(user)}
        return info(data=payload, msg="注册成功")

    async def Logout(
        self,
        payload: TokenPayload,
    ):
        try:
            await blacklist_token(payload.jti, payload.remaining_seconds())
        except Exception:
            # 拉黑失败却回「退出成功」等于骗用户，这里选择失败关闭
            logger.error("登出写入令牌黑名单失败（Redis 不可用）", exc_info=True)
            raise OpError("登出失败，请稍后重试")

        data = {"code": 200, "msg": "退出成功"}
        return info(data=data)