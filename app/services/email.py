"""邮箱验证码的发送与校验（硬注册的核心）。

设计约定（逐条对应审核要求）：

- **S1 随机数用 ``secrets``**：``random`` 是 Mersenne Twister，观察若干输出即可
  推算出内部状态；用在验证码上等于没有验证码。
- **S2 验证码绝不出现在 HTTP 响应里**：本模块对外只返回 ``expires_in``。
  回显验证码 = 任何人填别人的邮箱就能拿码注册。
- **S3 先发送成功、再写缓存**：反过来的话，Resend 失败会留下「缓存有码但用户
  从没收到」的死状态，用户只能在 5 分钟后重来。
- **S4 限制试错次数**：6 位码只有 100 万种，5 分钟不限次数暴力枚举完全可行。
  同一 email 连错 5 次即作废验证码，强制重新获取；比对用 ``secrets.compare_digest``。
- **S5 发送接口双维度限流**（email + IP），另加 60 秒冷却，防止被当邮件轰炸机。
  限流检查失败时**失败开放**（与 ``AuthService`` 的既有取向一致）；但验证码的
  读写失败必须**失败关闭**——缓存挂了就无法验证，绝不能放行注册。
- **S6 日志里不出现验证码明文**：只记录「给某个邮箱发了码」这类元信息。
  Resend SDK 的异常原文也不外传（会带请求细节 / API key 相关线索）。

并发与阻塞：

- Resend SDK 是**同步**实现（基于 requests），必须走 ``run_in_threadpool``，
  否则会把事件循环卡住（同一个坑见 ``utils/cloudinary.py``）。
- 冷却键同时充当「同一 email 的发送闸门」：用 ``SET NX`` 抢占，既防连点也防
  两个并发请求各自生成一个不同的码（后者会让先收到的那封邮件里的码失效）。
"""

import asyncio
import logging
import secrets

import resend
from fastapi import Request
from fastapi.concurrency import run_in_threadpool

from config import RESEND_API_KEY, RESEND_FROM, rate_limit, redis_client
from utils import AppError, BadRequest, Busy, info

logger = logging.getLogger(__name__)

# 验证码有效期：需求指定 5 分钟。
CODE_TTL_SECONDS = 300
# 同一验证码允许的错误次数，达到即作废（S4）。
CODE_MAX_ATTEMPTS = 5
# 同一 email 的重发冷却：缓存命中也要等冷却结束，避免被当作邮件轰炸机（S5）。
RESEND_COOLDOWN_SECONDS = 60

# 发送限流：email 维度收紧（真正被轰炸的是收件人），IP 维度放宽但要能兜住
# 「换一批邮箱地址」的分布式扫射。
_SEND_RATE_MAX_EMAIL = 5
_SEND_RATE_MAX_IP = 10
_SEND_RATE_WINDOW = 3600

# key 集中成常量，避免各调用点手拼字符串时拼歪。
#
# email 部分**只在拼 Redis key 时**统一 ``.strip().lower()``（见 ``_key_email``），
# 落库与投递仍用用户原样输入。理由：
#   - MySQL 的 utf8mb4 ci 排序规则本就不区分大小写，``User.email == "Foo@x.com"``
#     能命中库里存的 ``foo@x.com``；若 Redis key 区分大小写，用户前后两次输入
#     大小写不同就会「明明收到码却报验证码已过期」；
#   - 同理，email 维度的限流/冷却若区分大小写，换个大小写就能绕过 5 次/小时。
# 反过来（只在一处 lower）才是真正会算出两套 key 的写法。
_CODE_KEY = "email:code:{email}"
_ATTEMPTS_KEY = "email:code:attempts:{email}"
_COOLDOWN_KEY = "email:code:cooldown:{email}"


def _key_email(email: str) -> str:
    """Redis key 用的 email 形态（小写归一）。落库与投递不受影响。"""
    return (email or "").strip().lower()

# 「比较 + 删除」用 Lua 保证原子性：先 GET 再 DEL 之间存在竞态，两个并发请求
# 可能都通过校验。这里在 Python 侧先用 compare_digest 做恒定时间比较（S4），
# 再由脚本原子地「值仍等于提交值才删」，把重放窗口压到 0。
_CONSUME_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

# 错误计数同样用 Lua（INCR + 首次设 TTL）。不用 ``EXPIRE ... NX`` 的原因见
# config/cache.py 的 _RATE_LIMIT_SCRIPT：那是 Redis 7+ 才支持的语法，而本机
# 服务跑的是 3.0.504；一旦抛错，S4 的「连错 5 次作废」会静默失效。
_FAILURE_SCRIPT = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return n
"""


def _render_html(code: str) -> str:
    """简单邮件模板：只做内联样式，不引外部脚本/图片（邮件客户端会拦截外链）。"""
    return (
        '<div style="max-width:480px;margin:0 auto;padding:24px;'
        'font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#222">'
        '<h2 style="margin:0 0 12px;font-size:20px">注册验证码</h2>'
        '<p style="margin:0 0 16px;line-height:1.6">你正在注册本站账号，'
        "请在注册页面填写以下验证码：</p>"
        f'<p style="margin:0 0 16px;font-size:32px;font-weight:700;'
        f'letter-spacing:8px">{code}</p>'
        '<p style="margin:0;color:#888;font-size:13px;line-height:1.6">'
        "验证码 5 分钟内有效，请勿转发给他人。若非本人操作，请忽略本邮件。</p>"
        "</div>"
    )


def _send_email_sync(to_email: str, code: str) -> None:
    """同步发送验证码邮件（仅允许在 threadpool 中调用）。

    异常**不在这里吞掉**：调用方需要知道「没发出去」从而跳过写缓存（S3）。
    但异常原文不会传给客户端，只由调用方 ``logger.error(..., exc_info=True)``。
    """
    resend.api_key = RESEND_API_KEY
    resend.Emails.send(
        {
            "from": RESEND_FROM,
            "to": [to_email],
            "subject": "注册验证码",
            "html": _render_html(code),
        }
    )


class EmailService:
    async def SendCode(self, email: str, request: Request):
        """发送注册验证码。

        缓存命中时**复用**已有验证码、不重新生成、不续期 TTL（重发只重复投递
        同一封内容），避免前端显示的倒计时被一次重发悄悄拉回 300 秒。
        """
        email = (email or "").strip()
        key_email = _key_email(email)
        client_ip = request.client.host if request.client else "unknown"

        code_key = _CODE_KEY.format(email=key_email)
        attempts_key = _ATTEMPTS_KEY.format(email=key_email)
        cooldown_key = _COOLDOWN_KEY.format(email=key_email)

        # S5：email 与 IP 双维度限流。Redis 不可用时失败开放（沿用项目既定取向），
        # 但必须留下 error 级别告警，不能静默降级。
        try:
            allowed = all(
                await asyncio.gather(
                    rate_limit(
                        f"email:acct:{key_email}",
                        max_attempts=_SEND_RATE_MAX_EMAIL,
                        window_seconds=_SEND_RATE_WINDOW,
                    ),
                    rate_limit(
                        f"email:ip:{client_ip}",
                        max_attempts=_SEND_RATE_MAX_IP,
                        window_seconds=_SEND_RATE_WINDOW,
                    ),
                )
            )
        except Exception:
            logger.error("发送验证码限流检查失败（Redis 不可用），本次未限流", exc_info=True)
            allowed = True

        if not allowed:
            raise Busy("发送过于频繁，请稍后再试")

        # 冷却 + 并发闸门。这里读写 Redis 失败必须失败关闭：验证码压根存不进去，
        # 再回「已发送」就是骗人。
        try:
            cached, ttl = await self._read_code(code_key)
            gate = await redis_client.set(
                cooldown_key, "1", ex=RESEND_COOLDOWN_SECONDS, nx=True
            )
        except Exception:
            logger.error("验证码缓存不可用（Redis）", exc_info=True)
            raise AppError("验证码服务暂时不可用，请稍后再试")

        if not gate:
            raise Busy(f"发送过于频繁，请 {RESEND_COOLDOWN_SECONDS} 秒后再试")

        if cached and ttl > 0:
            # 缓存命中：直接复用原码，不续期。若这里重发失败，原码仍然有效，
            # 只释放冷却让用户能立刻重试，不删除缓存。
            try:
                await run_in_threadpool(_send_email_sync, email, cached)
            except Exception:
                logger.error("重发注册验证码邮件失败: to=%s", email, exc_info=True)
                await self._release_cooldown(cooldown_key)
                raise AppError("验证码发送失败，请稍后再试")

            logger.info("已向 %s 重发注册验证码（缓存命中，未续期）", email)
            return info(msg="验证码已发送", data={"expires_in": ttl})

        # 缓存未命中 / 已过期：生成新码。S1：secrets，不是 random。
        code = str(secrets.randbelow(900000) + 100000)

        # S3：先发送，成功后才写缓存。发送失败时缓存里不会留下任何东西。
        try:
            await run_in_threadpool(_send_email_sync, email, code)
        except Exception:
            logger.error("发送注册验证码邮件失败: to=%s", email, exc_info=True)
            await self._release_cooldown(cooldown_key)
            raise AppError("验证码发送失败，请稍后再试")

        # 写缓存失败同样要释放冷却，否则用户既收不到可用的码、又要干等 60 秒。
        try:
            pipe = redis_client.pipeline()
            pipe.set(code_key, code, ex=CODE_TTL_SECONDS)
            # 新码对应全新的重试额度，顺手清掉上一轮遗留的次数
            pipe.delete(attempts_key)
            await pipe.execute()
            expires_in = await redis_client.ttl(code_key)
        except Exception:
            logger.error("写入验证码缓存失败（Redis 不可用）", exc_info=True)
            await self._release_cooldown(cooldown_key)
            raise AppError("验证码服务暂时不可用，请稍后再试")

        logger.info("已向 %s 发送注册验证码", email)
        return info(
            msg="验证码已发送",
            data={"expires_in": expires_in if expires_in > 0 else CODE_TTL_SECONDS},
        )

    async def VerifyCode(self, email: str, code: str) -> None:
        """校验并**一次性消费**验证码，失败抛 ``BadRequest``(400)。

        消费时机（S7）：校验通过即原子删码，随后才由调用方建号。若建号恰好撞上
        并发唯一索引冲突，用户需要重新获取验证码（受 60 秒冷却约束）。
        选择「先删码」而不是「建号成功后再删」的理由：

        - 一次性语义没有回放窗口。反过来做的话，删码失败会让一个仍然有效的
          验证码在缓存里多留最多 5 分钟；
        - 建号失败的概率很低——Register 里在调用本方法前已经查过重（虽然仍有
          并发竞态），而验证码泄漏 / 重放的概率与后果都更严重。

        调用方**必须**先确认要建号再调用本方法：这里一旦成功，码就没了。
        """
        email = (email or "").strip()
        key_email = _key_email(email)
        code_key = _CODE_KEY.format(email=key_email)
        attempts_key = _ATTEMPTS_KEY.format(email=key_email)

        try:
            stored, ttl = await self._read_code(code_key)
        except Exception:
            # 失败关闭：读不到缓存就无法验证，不能放行注册
            logger.error("读取验证码缓存失败（Redis 不可用）", exc_info=True)
            raise AppError("验证码服务暂时不可用，请稍后再试")

        if not stored:
            raise BadRequest("验证码已过期，请重新获取")

        # S4：恒定时间比较，避免通过响应时间逐位猜码
        if not secrets.compare_digest(stored, code):
            exhausted = await self._record_failure(attempts_key, ttl)
            if exhausted:
                # 达到上限：立刻作废，强制重新获取，不给继续爆破的窗口
                await self._delete_quietly(code_key, attempts_key)
                logger.warning("验证码错误次数达到上限，已作废: %s", email)
                raise BadRequest("验证码错误次数过多，请重新获取验证码")
            raise BadRequest("验证码错误，请重新输入")

        try:
            consumed = await redis_client.eval(_CONSUME_SCRIPT, 1, code_key, code)
        except Exception:
            logger.error("消费验证码失败（Redis 不可用）", exc_info=True)
            raise AppError("验证码服务暂时不可用，请稍后再试")

        if not consumed:
            # 并发场景：另一个请求已经用掉了同一个码
            raise BadRequest("验证码已使用，请重新获取")

        # 计数清理是锦上添花，失败不影响「码已被消费」这一事实
        await self._delete_quietly(attempts_key)
        logger.info("邮箱验证码校验通过: %s", email)

    # ------------------------------------------------------------------ utils

    @staticmethod
    async def _read_code(code_key: str) -> tuple[str | None, int]:
        """一次 pipeline 取回验证码与剩余 TTL。"""
        pipe = redis_client.pipeline()
        pipe.get(code_key)
        pipe.ttl(code_key)
        value, ttl = await pipe.execute()
        return value, int(ttl)

    @staticmethod
    async def _record_failure(attempts_key: str, ttl: int) -> bool:
        """记录一次错误；返回是否已达上限。

        计数键与验证码同 TTL（TTL 只在第一次错误时设置，否则每次错误都会把
        窗口续期，等于给爆破续命）。Redis 出错时返回 False——计数失败不该让
        整个校验流程 500，真正的兜底是 5 分钟 TTL。
        """
        try:
            attempts = await redis_client.eval(
                _FAILURE_SCRIPT,
                1,
                attempts_key,
                ttl if ttl > 0 else CODE_TTL_SECONDS,
            )
        except Exception:
            logger.error("写入验证码错误计数失败（Redis 不可用）", exc_info=True)
            return False

        return int(attempts) >= CODE_MAX_ATTEMPTS

    @staticmethod
    async def _delete_quietly(*keys: str) -> None:
        try:
            await redis_client.delete(*keys)
        except Exception:
            logger.warning("清理验证码相关 key 失败: %s", keys, exc_info=True)

    @staticmethod
    async def _release_cooldown(cooldown_key: str) -> None:
        """发送失败时撤销冷却闸门（尽力而为；Redis 已挂时这里同样会失败）。"""
        try:
            await redis_client.delete(cooldown_key)
        except Exception:
            logger.warning("撤销验证码发送冷却失败", exc_info=True)