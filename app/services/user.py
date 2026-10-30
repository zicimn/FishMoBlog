"""用户资料与账号自注销。

本 service 刻意只做三件事，接口层不要再往里塞别的职责：

1. ``Edit``        —— 登录用户修改自己的资料（用户名 / 头像 / 简介）；
2. ``AdminList``   —— 管理端分页读取全量用户；
3. ``RemoveSelf``  —— 登录用户凭邮箱验证码注销自己的账号。

边界约定：

- **身份只认调用方传进来的 ``User``**（路由层由 ``GetCurrentUser`` 提供），
  service 不接受「用户 id」参数，杜绝把越权判断下放给请求体；
- 邮箱、密码、``is_admin`` / ``status`` 都不在可改字段里：邮箱是登录标识与
  验证码收件地址，密码走独立的重置流程，权限与状态只能由后台改动；
- 所有写操作显式 ``commit``，不能依赖 ``get_db`` 兜底（``flush`` 会清空
  ``session.new/dirty/deleted``，只看这三个集合的兜底提交会静默丢写入）。
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from schemas import UserEditRequest, to_admin_user, to_user_profile
# 指向子模块而不是 services 包：services/__init__.py 会先 import .email 再 import
# 本模块，若这里写 `from services import EmailService` 会触发循环导入（与
# services/auth.py 顶部的说明同源）。
from services.email import EmailService
from utils import BadRequest, Conflict, info

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ 1. 修改资料
    async def Edit(
        self,
        user: User,
        data: UserEditRequest,
    ):
        """修改当前登录用户的资料。

        可空字段按 ``data.model_fields_set`` 判断，语义与文章编辑一致：
        **键不出现 = 不改，键出现且为 null / 空串 = 清空**。若改回真值判断，
        「清空头像 / 简介」会永久失效。

        用户名改名后，历史评论与留言仍展示发布当时的快照，不会跟着变——
        这是既有设计（``Comment.user_name`` / ``Msg.username`` 是快照列）。
        """
        # rollback 会 expire 所有持久化实例，之后再读 user.id 会触发同步懒加载，
        # 在 AsyncSession 下变成 StatementError(MissingGreenlet)。异常路径里
        # 只能使用这里提前取好的局部主键。
        user_id = user.id
        fields = data.model_fields_set

        if "username" in fields and data.username != user.username:
            # 先查重给出友好提示；并发竞态由唯一索引 + IntegrityError 兜底。
            # 不回显当前用户名之外的信息，避免借改名接口做账号探测。
            taken = await self.db.scalar(
                select(User.id)
                .where(User.username == data.username, User.id != user.id)
                .limit(1)
            )
            if taken is not None:
                raise Conflict("用户名已被占用")
            user.username = data.username

        if "avatar" in fields:
            # 空串与 null 等价：清空头像，不落空字符串。
            user.avatar = (data.avatar or "").strip() or None

        if "bio" in fields:
            user.bio = (data.bio or "").strip() or None

        if not fields:
            # 没有任何可改字段：不制造一次无意义的 UPDATE，直接回当前资料。
            return info(data=to_user_profile(user))

        try:
            await self.db.commit()
        except IntegrityError:
            # 「先查后改」存在竞态，唯一索引才是最终防线。
            await self.db.rollback()
            logger.warning("修改资料唯一约束冲突: user_id=%r", user_id)
            raise Conflict("用户名已被占用")

        return info(msg="修改成功", data=to_user_profile(user))

    # ------------------------------------------------------------------ 2. 管理端列表
    async def AdminList(
        self,
        page: int,
        size: int,
    ):
        """后台用户列表：按自增 id 倒序分页（与注册时间单调一致）。

        ！！！永远不要把 ``password_hash`` 放进返回值：这里用列投影，只取
        ``to_admin_user`` 需要的列，连 ORM 实体都不加载，从源头避免整行序列化。
        """
        # 路由层应当用 Query(ge=1/le=100) 校验；service 再兜一层，防止绕过
        # 路由直接调用时 page=0 产生负 OFFSET（MySQL 语法错误 → 500）。
        page = max(1, page)
        size = min(max(1, size), 100)

        total = (await self.db.execute(
            select(func.count()).select_from(User)
        )).scalar_one()

        rows = (await self.db.execute(
            select(
                User.id,
                User.email,
                User.username,
                User.avatar,
                User.bio,
                User.is_admin,
                User.status,
                User.created_at,
            )
            # id 是自增主键，倒序即注册顺序倒序，且直接走 PK 索引；
            # 按 created_at 排会 filesort（该列无索引）。
            .order_by(User.id.desc())
            .limit(size)
            .offset((page - 1) * size)
        )).all()

        return info(data={"total": total, "items": [to_admin_user(u) for u in rows]})

    # ------------------------------------------------------------------ 3. 自注销
    async def RemoveSelf(
        self,
        user: User,
        code: str,
    ):
        """凭邮箱验证码注销当前账号。

        验证码由 ``POST /user/delete-code`` 发到账号邮箱（路由层取
        ``user.email``，不接受客户端指定地址），与注册码在 Redis 里分
        命名空间：注册码不能拿来注销，反之亦然。service 层只校验、一次性
        消费（见 ``EmailService.VerifyCode``），
        校验失败抛 ``BadRequest``(400)，而不是 401 —— 填错验证码不该让前端
        误判为令牌失效并把用户踢回登录页。

        先验码、后删行：验证码一旦通过就已被消费，若删除失败（例如库里仍有
        未处理的外键约束）用户需要重新获取验证码。评论 / 留言的 ``user_id``
        是 ``ON DELETE SET NULL``，删号只断开关联，正文与昵称快照保留。

        管理员自删额外要求「至少还剩一个可用管理员」：项目没有提升/新增
        管理员的接口，唯一管理员一旦删掉，后台就永久锁死，只能进库改。
        不额外拉黑当前令牌：下一请求 ``GetCurrentUser`` 查不到用户会回 401，
        与「用户已删除」的既有处理一致。
        """
        # rollback 会 expire 持久化实例，异常路径里只能读局部主键（见 Edit）。
        user_id = user.id

        # 与 RegisterRequest.code 同一套格式约束。路由若漏了 Pydantic 校验，
        # compare_digest(stored, None/超长串) 会变成 TypeError 或无意义的比较。
        if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
            raise BadRequest("验证码错误，请重新输入")

        await EmailService().VerifyCode(user.email, code, purpose="delete")

        if user.is_admin:
            # FOR UPDATE 锁住所有「可用管理员」行，堵住「两个管理员同时自删、
            # 各自看到对方还在」的竞态。个人博客量级，锁到 commit 的开销可忽略。
            active_admin_ids = (
                await self.db.execute(
                    select(User.id)
                    .where(User.is_admin == 1, User.status == 1)
                    .with_for_update()
                )
            ).scalars().all()
            if len(active_admin_ids) <= 1 and user_id in active_admin_ids:
                raise Conflict("不能注销唯一的管理员账号，请先指定其他管理员")

        await self.db.delete(user)
        try:
            await self.db.commit()
        except IntegrityError:
            # 正常路径不该走到这里（评论 / 留言都是 SET NULL）。若未来新增了
            # RESTRICT 外键，回滚并明确告知，而不是把 500 抛给前端。
            await self.db.rollback()
            logger.warning("注销账号触发外键约束: user_id=%r", user_id, exc_info=True)
            raise Conflict("账号仍有关联数据，暂时无法注销")

        logger.info("用户已注销账号: user_id=%r", user_id)
        return info(msg="账号已注销")