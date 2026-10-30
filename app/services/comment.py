import asyncio
import logging
import re
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import rate_limit
from models import Comment,Article,COMMENT_STATUS_NORMAL,STATUS_PUBLIC,User
from utils.responsed import Busy,NotFound,OpError,info
from utils.sanitize import sanitize_html
from schemas import to_item,to_top_item,to_admin_comment,CommentCreateRequest,to_comment_result

logger = logging.getLogger(__name__)

# 侧边栏「最新评论」展示条数
_TOP_COMMENT_LIMIT = 5
# 同一 IP 的评论频率限制
_COMMENT_RATE_MAX = 5
_COMMENT_RATE_WINDOW = 60
# 登录用户发布评论的限流：IP 维度放宽（同一出口 IP 后面可能有很多人），
# 用户维度收紧（单个账号刷屏才是要拦的目标），取向与 services/auth.py 一致。
_COMMENT_RATE_MAX_IP = 10
_COMMENT_RATE_MAX_USER = 5

# 把 HTML 粗略转成纯文本，用于 content_text 列（查重/后台预览）。不用第三方清洗库，
# 真正的 HTML 清洗（XSS）是待定的遗留问题。
_TAG_RE = re.compile(r"<[^>]+>")
_PLAIN_TEXT_LIMIT = 500


def _plain_text(html: str, limit: int = _PLAIN_TEXT_LIMIT) -> str:
    return _TAG_RE.sub("", html or "").strip()[:limit]


class ComService:

    def __init__(self,db:AsyncSession):
        self.db = db


    async def GetList(
        self,
        path:str,
        page:int,
        size:int
    ):
        # 用本类的只读解析（slug 或数字 id），不要走 ArticleService.GetSlug：
        # 后者现在会累加浏览量，打开一次评论列表就会把文章浏览量刷高一次。
        article = await self._resolve_article(path)
        article_id = article.id

        skip = (page - 1)*size
        cquery = await self.db.execute(
            select(Comment)
            .where(
                Comment.article_id == article_id,
                Comment.parent_id.is_(None),
                Comment.status == COMMENT_STATUS_NORMAL
            )
            .order_by(Comment.created_at.desc(),Comment.id.desc())
            .offset(skip)
            .limit(size)
        )
        result = cquery.scalars().all()
        roots = list(result)

        # key 必须是父评论 id（int）：下面按 reply.parent_id（int）写入、按 root.id（int）读取，
        # 之前写入用 int、读取时却 get(str(root.id))，导致 child 恒为空。
        replies_by_parent: dict[int, list] = {}
        root_ids = [c.id for c in roots]
        if root_ids:
            reply_result = await self.db.execute(
                select(Comment)
                .where(
                    Comment.parent_id.in_(root_ids),
                    Comment.status == COMMENT_STATUS_NORMAL
                )
                .order_by(Comment.created_at.asc(),Comment.id.asc())
            )
            all_replies = list(reply_result.scalars().all())

            # name_by_id 同时收录顶层评论与回复，回复的 parent_id 才能解析出昵称
            name_by_id = {c.id: c.user_name for c in roots}
            name_by_id.update({c.id : c.user_name for c in all_replies})

            for reply in all_replies:
                parent_name = name_by_id.get(reply.parent_id, "")
                replies_by_parent.setdefault(reply.parent_id,[]).append(
                    to_item(reply,reply_name=parent_name)
                )

        data = [
            to_item(root,children=replies_by_parent.get(root.id,[]))
            for root in roots
        ]

        return info(data=data)

    async def GetTop(self, limit: int = _TOP_COMMENT_LIMIT):
        """侧边栏「最新评论」：按时间倒序取少量正常评论（不分页、不带回复树）。

        必须带出所属文章的 path/title：侧边栏条目要能点回文章，而前端路由走
        slug，只有 ``comment.article_id`` 拼不出链接。用一次 join 取回，
        不做「每条评论再查一次文章」的 N+1。
        """
        result = await self.db.execute(
            select(Comment, Article.path, Article.title)
            .join(Article, Article.id == Comment.article_id)
            .where(Comment.status == COMMENT_STATUS_NORMAL)
            .order_by(Comment.created_at.desc(), Comment.id.desc())
            .limit(limit)
        )
        items = [
            to_top_item(comment, article_path, article_title)
            for comment, article_path, article_title in result.all()
        ]
        return info(data=items)

    async def AdminList(
        self,
        page: int,
        size: int,
        status: Optional[int] = None,
    ):
        """后台评论列表：全部评论（含回复）按时间倒序，扁平分页。

        与 ``GetList`` 的区别：不按文章过滤、不带回复树，也不限制 status ——
        后台要能看见待审核与已屏蔽的评论，否则没法审核。
        一次 join 带出文章 path/title，避免逐条再查文章（N+1）。
        """
        conditions = []
        if status is not None:
            conditions.append(Comment.status == status)

        count_query = select(func.count()).select_from(Comment)
        if conditions:
            count_query = count_query.where(*conditions)
        total = (await self.db.execute(count_query)).scalar_one()

        skip = (page - 1) * size
        query = (
            select(Comment, Article.path, Article.title)
            .join(Article, Article.id == Comment.article_id)
            .where(*conditions)
            .order_by(Comment.created_at.desc(), Comment.id.desc())
            .limit(size)
            .offset(skip)
        )
        rows = (await self.db.execute(query)).all()

        items = [
            to_admin_comment(comment, article_path, article_title)
            for comment, article_path, article_title in rows
        ]
        return info(data={"total": total, "items": items})

    async def _allow_rate(self, client_ip: str, user_id: int) -> bool:
        """IP + 用户双维度固定窗口限流；Redis 故障失败开放（与既有取向一致）。"""
        try:
            results = await asyncio.gather(
                rate_limit(
                    f"comment:ip:{client_ip}",
                    max_attempts=_COMMENT_RATE_MAX_IP,
                    window_seconds=_COMMENT_RATE_WINDOW,
                ),
                rate_limit(
                    f"comment:uid:{user_id}",
                    max_attempts=_COMMENT_RATE_MAX_USER,
                    window_seconds=_COMMENT_RATE_WINDOW,
                ),
            )
            return all(results)
        except Exception:
            logger.error("评论限流检查失败（Redis 不可用），本次未限流", exc_info=True)
            return True

    async def _resolve_article(self, article_ref: str) -> Article:
        """把前端传来的文章标识解析成文章实体。

        先按 slug（``Article.path``）精确匹配，查不到再退化为数字 id，
        顺序固定以避免数字型 slug 与 id 撞车时的歧义。
        """
        article = (
            await self.db.execute(
                select(Article).where(
                    Article.path == article_ref,
                    Article.status.in_(STATUS_PUBLIC),
                )
            )
        ).scalar_one_or_none()

        if article is None:
            try:
                article_id = int(article_ref)
            except (TypeError, ValueError):
                article_id = None
            if article_id is not None:
                article = (
                    await self.db.execute(
                        select(Article).where(
                            Article.id == article_id,
                            Article.status.in_(STATUS_PUBLIC),
                        )
                    )
                ).scalar_one_or_none()

        if article is None:
            raise NotFound("文章不存在")
        return article

    async def Create(
        self,
        article_ref: str,
        data: CommentCreateRequest,
        user: User,
        client_ip: str,
    ):
        """发表评论（必须是已登录用户）。作者身份全部取自登录态。

        ``article_ref`` 是文章标识（slug 或数字 id）。解析放在 service 而非路由：
        解析要查库，而路由层拿不到 session，只有 service 持有 AsyncSession。
        """
        if not await self._allow_rate(client_ip, user.id):
            raise Busy("评论过于频繁，请稍后再试")

        article = await self._resolve_article(article_ref)

        parent_id = data.parent_id
        if parent_id is not None:
            # 只允许回复同一篇文章下、且仍然可见的评论，防止跨文章挂载评论树；
            # 父评论被屏蔽时对外等同于不存在，不额外泄露它的状态。
            parent = await self.db.get(Comment, parent_id)
            if (
                parent is None
                or parent.article_id != article.id
                or parent.status != COMMENT_STATUS_NORMAL
            ):
                raise NotFound("被回复的评论不存在")

        # 必须先清洗再落库：content 存清洗后的 HTML，content_text 再由清洗后的结果派生。
        # 否则纯文本列会残留被剥离的脚本内容，与对外展示的 content 不一致。
        content = sanitize_html(data.content)
        if not content:
            # 内容只剩标签/脚本，清洗后为空（如原本只有 <script>...</script>）。
            # AppError 体系没有 400，这里借 OpError（403，「这次操作不被接受」）。
            # 原始入参的空白/长度仍由 CommentCreateRequest 在 Pydantic 层拦掉（422）。
            raise OpError("评论内容不能为空")

        comment = Comment(
            article_id=article.id,
            parent_id=parent_id,
            user_id=user.id,
            # 快照：用户日后改名/换头像不影响历史评论
            user_name=user.username,
            user_avatar=user.avatar,
            # 刻意不落 user_email：评论表是半公开数据，账号邮箱不外泄，身份靠 user_id 关联
            content=content,
            content_text=_plain_text(content),
            status=COMMENT_STATUS_NORMAL,
        )
        self.db.add(comment)
        # 必须显式 commit：get_db 只在 session.new/dirty/deleted 非空时才提交，
        # 而 flush() 会把这三个集合清空 → 只 flush 的写入会被静默回滚。
        # expire_on_commit=False，commit 后 comment 的属性（含自增 id）仍可读。
        await self.db.commit()

        return info(data=to_comment_result(comment), msg="评论成功")

    async def Remove(
        self,
        comment_id: int,
        user: User,
    ):
        """删除评论及其全部子孙评论（硬删）。仅作者本人或管理员可删。"""
        comment = await self.db.get(Comment, comment_id)
        if comment is None:
            raise NotFound("评论不存在")

        # user_id 为 NULL 的历史/访客评论只有管理员能删
        if comment.user_id != user.id and not user.is_admin:
            raise OpError("没有权限删除该评论")

        # 逐层 BFS 收集所有后代，不依赖 MySQL 递归 CTE（保证版本兼容）。
        # 必须拿到 ORM 对象逐个 db.delete()：bulk delete 不走 ORM 状态跟踪，
        # 依赖 get_db 兜底提交不可靠（见下方 commit 处的说明）。
        to_delete = [comment]
        frontier = [comment.id]
        while frontier:
            children = list(
                (
                    await self.db.execute(
                        select(Comment).where(Comment.parent_id.in_(frontier))
                    )
                ).scalars().all()
            )
            if not children:
                break
            to_delete.extend(children)
            frontier = [c.id for c in children]

        # 由深到浅删除：先子孙后自身，避免与 parent_id 的 ON DELETE CASCADE 抢同一批行
        for item in reversed(to_delete):
            await self.db.delete(item)
        # 必须显式 commit：flush() 之后 session.deleted 会被清空（实测 new/dirty/deleted
        # 三者全为 0），而 get_db 正是靠这三个集合决定要不要提交 → 只 flush 的话
        # 删除会在请求结束时被静默回滚，接口却回「删除成功」。
        await self.db.commit()

        return info(msg="删除成功")
