import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import rate_limit
from models import Msg, User
from schemas import MsgCreateRequest, to_mdetail
from utils.responsed import Busy, Conflict, NotFound, OpError, info
from utils.sanitize import sanitize_html

logger = logging.getLogger(__name__)

# 留言频率限制：同一出口 IP 后面可能有很多人，放宽；单账号收紧。
# 一人一条已经限制了总量，这里主要挡批量注册后的瞬时刷写。
_MSG_RATE_WINDOW = 60
_MSG_RATE_MAX_IP = 10
_MSG_RATE_MAX_USER = 5


class MsgService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _allow_rate(self, client_ip: str, user_id: int) -> bool:
        """IP + 用户双维度固定窗口限流；Redis 故障失败开放（与评论一致）。"""
        try:
            results = await asyncio.gather(
                rate_limit(
                    f"msg:ip:{client_ip}",
                    max_attempts=_MSG_RATE_MAX_IP,
                    window_seconds=_MSG_RATE_WINDOW,
                ),
                rate_limit(
                    f"msg:uid:{user_id}",
                    max_attempts=_MSG_RATE_MAX_USER,
                    window_seconds=_MSG_RATE_WINDOW,
                ),
            )
            return all(results)
        except Exception:
            logger.error("留言限流检查失败（Redis 不可用），本次未限流", exc_info=True)
            return True

    async def MCreate(
        self,
        data: MsgCreateRequest,
        user: User,
        client_ip: str,
    ):
        """创建留言。作者身份与 IP 取自服务端，不接受请求体传入。"""
        # 一人一条：先做应用层检查，唯一索引（uk_msg_user）负责并发兜底。
        existing = await self.db.scalar(
            select(Msg.id).where(Msg.user_id == user.id).limit(1)
        )
        if existing is not None:
            raise Conflict("你已经创建过了")

        if not await self._allow_rate(client_ip, user.id):
            raise Busy("留言过于频繁，请稍后再试")

        # 先清洗再落库：留言与评论共用同一套 nh3 白名单，挡掉脚本 / 事件属性 /
        # javascript: 链接等存储型 XSS。清洗后为空（如只提交了 <script>）说明
        # 没有有效内容；AppError 体系没有 400，沿用评论的 OpError 处理。
        content = sanitize_html(data.content)
        if not content:
            raise OpError("留言内容不能为空")

        msg = Msg(
            user_id=user.id,
            username=user.username,
            avatar=user.avatar,
            content=content,
            ip=client_ip,
        )
        self.db.add(msg)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            logger.warning("创建留言完整性约束冲突: user_id=%r", user.id, exc_info=True)
            raise Conflict("你已经创建过了")

        return info(msg="留言成功", data=to_mdetail(msg))

    async def MGetList(
        self,
        page: int,
        size: int,
    ):
        skip = (page - 1) * size

        total = (await self.db.execute(select(func.count()).select_from(Msg))).scalar_one()

        rows = (
            await self.db.execute(
                select(Msg)
                # 与文章/评论一致：新留言在前；id 兜同一时刻的排序
                .order_by(Msg.created_at.desc(), Msg.id.desc())
                .limit(size)
                .offset(skip)
            )
        ).scalars().all()

        return info(data={"total": total, "items": [to_mdetail(m) for m in rows]})

    async def MRemove(
        self,
        msg_id: int,
        user: User,
    ):
        """删除留言：本人或管理员。账号已删除（user_id 为 NULL）的留言仅管理员可删。"""
        msg = await self.db.get(Msg, msg_id)
        if msg is None:
            raise NotFound("没有该留言")

        if msg.user_id != user.id and not user.is_admin:
            raise OpError("没有权限删除该留言")

        await self.db.delete(msg)
        await self.db.commit()

        return info(msg="删除成功")