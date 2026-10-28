import logging
import re

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from models import Article, STATUS_PUBLIC
from schemas import (
    to_preview,
    to_detail,
    to_admin_preview,
    to_admin_detail,
    ArticleSaveRequest,
    ArticleEditRequest,
)
# 指向子模块而不是 services 包：services/__init__.py 第 1 行就 import 了 .article，
# 此时 services 包尚未初始化完，`from services import CatService` 会触发循环导入。
from services.category import CatService


def _conflict_detail(exc: IntegrityError) -> str:
    """把 MySQL 错误码翻成给用户看的话。

    只认「路径被占用」是不够的：同一个 IntegrityError 还可能来自 NOT NULL 违例
    （实测 path=NULL → 1048，而此时回「该访问路径已被占用」会让人去改一个根本
    不存在的冲突路径）、数据超长（1406）等。这里分三类，未知错误给一句可行动的兜底。
    """
    args = getattr(getattr(exc, "orig", None), "args", None)
    errno = args[0] if args else None
    if errno == 1062:      # ER_DUP_ENTRY
        return "该访问路径已被占用，请换一个"
    if errno in (1048, 1364):  # ER_BAD_NULL_ERROR / ER_NO_DEFAULT_FOR_FIELD
        return "必填字段为空，请检查后重试"
    if errno in (1406, 1265):  # ER_DATA_TOO_LONG / ER_WARN_DATA_OUT_OF_RANGE
        return "字段内容过长，请精简后重试"
    logger.warning("未识别的完整性约束错误 errno=%r", errno, exc_info=True)
    return "数据写入冲突，请检查必填项后重试"
from utils.cloudinary import destroy_image, public_id_from_url
from utils.responsed import Conflict,NotFound,info
from utils.counter import ArticleViewCounter

from typing import Optional

logger = logging.getLogger(__name__)

# 正文里只存了图片 URL（没有逐图的 public_id 列）：编辑/删除文章时，用新旧 HTML
# 的 <img src> 差集找出「本次不再被引用」的图，再反推 public_id 清理云端资源。
# 只匹配 src 属性；双引号、单引号、无引号三种写法都兜住（源码视图可能手改过）。
_IMG_SRC_RE = re.compile(
    # (?<![\w-]) 是为了不把 data-src / srcset 里的 src 当成真地址
    r"""<img\b[^>]*?(?<![\w-])src\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""",
    re.IGNORECASE,
)


def _image_sources(html: Optional[str]) -> set[str]:
    """取出 HTML 里所有 <img src>，用于做差集；不是完整 HTML 解析。"""
    sources: set[str] = set()
    for match in _IMG_SRC_RE.finditer(html or ""):
        src = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if src:
            sources.add(src)
    return sources


async def _is_still_referenced(db: AsyncSession, src: str) -> bool:
    """这张图是否还被别的文章引用（正文或封面）。

    同一张图可能被多篇文章共用（管理员从源码里复制过 URL）。只按本文差集清理
    会在这种情况下删掉别人还在用的图，所以删云端前先确认没有其他引用。
    此时本文的新 content 已提交（删文场景则是整行已删），命中的只可能是别的文章。
    """
    query = (
        select(Article.id)
        .where(
            or_(
                Article.content.contains(src, autoescape=True),
                Article.cover == src,
            )
        )
        .limit(1)
    )
    return (await db.execute(query)).scalar_one_or_none() is not None


class ArticleService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def GetList(
        self,
        page: int,
        size: int,
        category_name: Optional[str] = None
    ):
        skip = (page - 1) * size
        filters = [Article.status.in_(STATUS_PUBLIC)]

        # 用 falsy 判断而非 `is not None`：?category_name= 传空串时不应加过滤条件。
        if category_name:
            # 只读解析，不建分类：列表查询是 GET，未命中应返回空列表，而不是
            # 顺手写库、更不该把 None 当成有效 id 去匹配 category_id IS NULL。
            cid = await CatService(db=self.db).GetByName(category_name)
            if cid is None:
                return info(data={"total": 0, "items": []})
            filters.append(Article.category_id == cid)

        total = (
            await self.db.execute(
                select(func.count())
                .select_from(Article)
                .where(*filters)
            )
        ).scalar_one()

        #大致应该是卡片形式显示=>封面+悬浮粗体标题+简要+时间
        query = await self.db.execute(
            select(
                Article.id,
                Article.title,
                Article.description,
                Article.cover,
                Article.views,
                Article.style,
                Article.path,
                Article.created_at,
            )
            .where(*filters)
            .order_by(Article.created_at.desc())
            .offset(skip)
            .limit(size)
        )

        # 空列表是正常业务结果，不是错误，交给前端走空态
        data = {"total": total, "items": [to_preview(r) for r in query.all()]}
        return info(data=data)

    #后台列表：结构移植自前台 GetList，唯一实质差异是「不加可见性过滤」——
    # 后台必须能看到隐藏与草稿，否则管理端等于半个盲区。
    async def AdminList(
        self,
        page: int,
        size: int,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        category_name: Optional[str] = None,
    ):
        skip = (page - 1) * size
        filters = []

        if status:
            filters.append(Article.status == status)

        if keyword:
            # LIKE 元字符必须转义：否则搜 "%" 会退化成全表匹配、"_" 会变成任意单字符通配。
            # 反斜杠要最先替换，否则会把后面新加进去的转义反斜杠再转一遍。
            escaped = (
                keyword.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            filters.append(Article.title.like(f"%{escaped}%", escape="\\"))

        if category_name:
            # 与前台 GetList 同语义：列表是 GET，未命中返回空列表，不顺手建分类
            cid = await CatService(db=self.db).GetByName(category_name)
            if cid is None:
                return info(data={"total": 0, "items": []})
            filters.append(Article.category_id == cid)

        total = (
            await self.db.execute(
                select(func.count())
                .select_from(Article)
                .where(*filters)
            )
        ).scalar_one()

        query = await self.db.execute(
            select(
                Article.id,
                Article.title,
                Article.description,
                Article.cover,
                Article.style,
                Article.path,
                Article.status,
                Article.category_id,
                Article.views,
                Article.created_at,
                Article.updated_at,
            )
            .where(*filters)
            .order_by(Article.created_at.desc())
            .offset(skip)
            .limit(size)
        )

        # 空列表是正常业务结果，交给前端走空态
        data = {"total": total, "items": [to_admin_preview(r) for r in query.all()]}
        return info(data=data)

    async def GetId(
        self,
        id: int,
        status: bool = False,
    ):
        # 参数 status 的语义是「是否放开状态过滤」，不是「按状态查」：
        #   False（默认）＝前台语义，只认对外可见状态，既有行为原样保留；
        #   True ＝后台语义，不做状态过滤，管理员才能读到隐藏/草稿。
        # 调用方只有 api/admin.py 一处，默认值保证前台不受影响。
        filters = [Article.id == id]
        if not status:
            filters.append(Article.status.in_(STATUS_PUBLIC))

        query = await self.db.execute(
            select(Article)
            .where(*filters)
            # 详情不需要 category 关系数据，避免多打一条 selectin 查询。
            # 不能再写 noload(Article.columns)：专栏功能已删，Article 上已无 columns 关系，
            # 引用它会在构造查询时直接抛 AttributeError。
            .options(noload(Article.category))
        )

        result = query.scalar_one_or_none()

        if not result:
            raise NotFound("没有该文章")

        # 后台语义下多带 status/category_id：否则编辑表单回填不了状态
        return to_admin_detail(result) if status else to_detail(result)

    #客户端访问
    async def GetSlug(
        self,
        path: str,
    ):
        query = await self.db.execute(
            select(Article)
            .where(Article.path == path)
            .where(Article.status.in_(STATUS_PUBLIC))
            # 同上：Article 已无 columns 关系，只能 noload(category)
            .options(noload(Article.category))
        )

        result = query.scalar_one_or_none()

        if not result:
            raise NotFound("没有该文章")

        # 详情页被访问即计一次浏览量：先自增、再读总数，让本次访问体现在返回值里。
        # Redis 不可用时 incr 内部降级返回 0，不会把详情页带崩（与既有降级取向一致）。
        # 注意：评论列表不得复用本方法，否则刷评论页会连带刷高浏览量
        # （ComService.GetList 已改为走自己的只读解析）。
        await ArticleViewCounter.incr(result.id)

        data = to_detail(result)
        # get_total 是 async，漏 await 会把 coroutine 塞进响应体 → 序列化直接 500
        data["views"] = await ArticleViewCounter.get_total(result.id, result.views)
        return info(data=data)


    async def Save(
        self,
        data:ArticleSaveRequest,
    ):
        # 先查重再插：命中就明确回 409 并给出「路径被占用」，不必等数据库抛异常
        # 再回头猜是哪条约束炸的。**这只是快速路径，不是并发保护** —— 两个请求同时
        # 查重都通过、再一起插入时，仍然靠下面的唯一索引兜底（所以 except 必须留着）。
        if data.path:
            exists = (await self.db.execute(
                select(Article.id).where(Article.path == data.path)
            )).scalar_one_or_none()
            if exists is not None:
                logger.warning("创建文章：路径已存在 path=%r (article_id=%s)", data.path, exists)
                raise Conflict("该访问路径已被占用，请换一个")

        cat = CatService(db=self.db)
        id = (await cat.GetOrSave(data.category_name,True)).get("data").get("id")

        article = Article(
            title = data.title,
            path = data.path,
            description = data.description,
            # 空串一律归一成 NULL：否则库里会同时存在 "" 和 NULL 两种「没有封面」，
            # 前端判断与后续清理逻辑都得各自兼容两套表达。
            cover = data.cover or None,
            cover_public_id = data.cover_public_id or None,
            content = data.content,
            status = data.status,
            category_id = id
        )

        self.db.add(article)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            # 走到这里说明上面的查重没拦住：并发提交，或不是 path 上的冲突。
            # 原实现让异常直接穿到路由层变成 500，前端只能靠猜；这里明确回 409，
            # 并按错误码给出准确原因（见 _conflict_detail）。
            await self.db.rollback()
            logger.warning("创建文章完整性约束冲突: path=%r", data.path)
            raise Conflict(_conflict_detail(exc))

        await self.db.refresh(article)

        # 回带 id：前端建完要能跳到该文章的编辑页继续写，只回 msg 做不到
        return info(msg="创建文章成功", data={"id": article.id})


    async def Remove(
        self,
        id:int,      
    ):
        exist = await self.db.execute(select(Article).where(Article.id == id))
        result = exist.scalar_one_or_none()

        if result is None:
            raise NotFound("没有该文章")

        # 必须在 delete 之前记下：commit 之后该行已从库里消失，
        # 再去读 cover_public_id / content 会触发懒加载（异步 session 下直接报错）。
        cover_public_id = result.cover_public_id
        cover_url = result.cover
        content_sources = _image_sources(result.content)

        await self.db.delete(result)
        # 必须显式 commit：get_db 只在 session.new/dirty/deleted 非空时才提交，
        # 而 flush() 会把这三个集合清空，只 flush 的话删除会在请求结束时被静默回滚。
        await self.db.commit()

        # 先提交、后清理云端。若反过来（先删图再提交），commit 失败回滚后库里文章还在、
        # 封面指向的图却已被销毁 → 前台裂图且无法自愈。
        # 清理是尽力而为：destroy_image 内部不抛异常，不会反过来带崩删除操作。
        if cover_public_id:
            still_used = bool(cover_url) and await _is_still_referenced(self.db, cover_url)
            if not still_used:
                await run_in_threadpool(destroy_image, cover_public_id)

        # 正文插图同理：文章没了，正文里的图若没有别处引用，也一并清理，
        # 否则每删一篇文章都会在云端留一批孤儿图。
        for src in content_sources:
            public_id = public_id_from_url(src)
            if not public_id or public_id == cover_public_id:
                continue
            if await _is_still_referenced(self.db, src):
                continue
            await run_in_threadpool(destroy_image, public_id)

        return info(msg="删除成功")



    async def Edit(
        self,
        id:int,
        data:ArticleEditRequest
    ):
        exist = await self.db.execute(select(Article).where(Article.id == id))
        result = exist.scalar_one_or_none()

        if result is None:
                raise NotFound("没有该文章")

        old_public_id = result.cover_public_id
        # 旧封面 URL 也要留：正文可能复用了同一张图（管理员把封面地址粘进正文），
        # 换封面时不能连坐删掉正文还在引用的资源。
        old_cover_url = result.cover
        # 编辑前的正文：提交成功后要拿它和新正文做差集，清理被删掉/替换的插图。
        # 必须在赋值 result.content 之前取，commit 之后再读就已经是新内容了。
        old_content = result.content or ""

        # 可空字段靠 model_fields_set 区分「未传」与「显式传 null」，而不是真值判断：
        #   键不在请求体里 → 未传，保持原值；
        #   键在、值是 null 或 "" → 显式清空。
        # 原实现一律 `if data.xxx:`，导致编辑永远无法清空字段——「留空提交」与
        # 「不改」不可区分，摘要/封面填错就只能去改数据库。
        provided = data.model_fields_set

        try:
            # NOT NULL 列（title / path / content）：空值没有「清空」语义，留空即不改
            if data.title:
                result.title = data.title
            if data.path:
                result.path = data.path
            if data.content:
                result.content = data.content

            # 可空列：键在就改，null / "" 归一成 None
            if "description" in provided:
                result.description = data.description or None
            if "cover" in provided:
                result.cover = data.cover or None
            if "cover_public_id" in provided:
                result.cover_public_id = data.cover_public_id or None

            # status 用 is not None 而非真值：语义与上面「键在就改」一致，
            # 也不会把合法值悄悄吞掉。
            if data.status is not None:
                result.status = data.status

            if data.category_name:
                cat = CatService(db=self.db)
                # 必须 await 并逐层取 id：GetOrSave 是协程，漏 await 会把 coroutine
                # 直接塞进 category_id 列（赋值成功、落库时才炸）。
                cid = (await cat.GetOrSave(data.category_name, True))["data"]["id"]
                result.category_id = cid

            # 注意 GetOrSave 内部也会 commit（顺带把上面这些脏字段一起刷库），
            # 所以 path 撞唯一索引的 IntegrityError 可能从那一行抛出来，
            # try 必须把 GetOrSave 也包进来，否则照样穿成 500。
            # 同上：只 flush 不会落库（get_db 的提交条件在 flush 后为 False）
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            logger.warning("编辑文章完整性约束冲突: id=%s path=%r", id, data.path)
            raise Conflict(_conflict_detail(exc))

        # 云端清理必须在 commit 成功之后：先删图再提交的话，commit 一失败，
        # 库里就指向一张已被销毁的图 → 前台裂图。destroy_image 内部不抛异常，
        # 清理失败最多留一张孤儿图，不会反过来让「保存成功」变失败。
        new_public_id = result.cover_public_id

        # 1) 换过封面（含被清空）→ 旧封面可以销毁，但要先确认它没有同时被
        #    正文（本文或其他文章）引用：封面地址完全可能被粘进正文复用。
        destroyed_cover = (
            old_public_id if old_public_id and old_public_id != new_public_id else None
        )
        if destroyed_cover:
            still_used = bool(old_cover_url) and await _is_still_referenced(
                self.db, old_cover_url
            )
            if not still_used:
                await run_in_threadpool(destroy_image, destroyed_cover)
            else:
                destroyed_cover = None

        # 2) 正文插图：只处理「本次确实提交了 content 且内容变了」的情况。
        #    对比新旧 HTML 的 <img src>，把不再被引用的图一并销毁 —— 这是
        #    「二次编辑时删图/换图 → 旧图变孤儿」的修复点。已入库的图当初上传后
        #    只把 URL 写进了正文，没有留下 public_id，所以这里靠 URL 反推。
        if data.content and data.content != old_content:
            removed_sources = _image_sources(old_content) - _image_sources(data.content)
            for src in removed_sources:
                public_id = public_id_from_url(src)
                if not public_id:
                    continue
                # 仍被当前封面引用（正文和封面指向同一张图）→ 不能删
                if public_id == new_public_id or public_id == destroyed_cover:
                    continue
                # 仍被别的文章引用 → 不能删
                if await _is_still_referenced(self.db, src):
                    continue
                await run_in_threadpool(destroy_image, public_id)

        return info(msg="编辑成功")

        
    
        
