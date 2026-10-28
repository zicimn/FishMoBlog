"""文章浏览量的 Redis 增量计数。

写入路径（``incr``）与读取路径（``get_total``）都对 Redis 故障做了降级：
Redis 挂掉时浏览量只会「暂时不涨」，不会让文章详情页 500。

Redis 里的增量由 ``sync_to_db`` 回写 MySQL，再由 ``periodic_sync_to_db``
作为后台任务周期驱动（在 main.py 的 lifespan 里启动）。
"""

import asyncio
import logging

from sqlalchemy import bindparam, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import AsyncSessionLocal, redis_client
from models import Article

logger = logging.getLogger(__name__)

# 增量回写间隔（秒）。浏览量是弱一致指标，分钟级足够，没必要频繁打库。
SYNC_INTERVAL_SECONDS = 300


class ArticleViewCounter:
    HASH_KEY = "article_views"

    @classmethod
    async def incr(cls, article_id: int) -> int:
        """累加一次浏览量，返回当前未回写的增量（Redis 不可用时返回 0）。"""
        try:
            return int(await redis_client.hincrby(cls.HASH_KEY, str(article_id), 1))
        except Exception:
            logger.warning("浏览量累加失败（Redis 不可用？）", exc_info=True)
            return 0

    @classmethod
    async def get(cls, article_id: int) -> int:
        """读取尚未回写数据库的增量。"""
        try:
            val = await redis_client.hget(cls.HASH_KEY, str(article_id))
        except Exception:
            logger.warning("浏览量读取失败（Redis 不可用？）", exc_info=True)
            return 0
        return int(val) if val else 0

    @classmethod
    async def get_total(cls, article_id: int, db_views: int) -> int:
        """真实浏览量 = 数据库里的值 + Redis 里尚未回写的增量。"""
        return (db_views or 0) + await cls.get(article_id)

    @classmethod
    async def sync_to_db(cls, db: AsyncSession) -> None:
        """把 Redis 中的增量批量回写数据库。

        顺序刻意是「先读 → 写库 → 成功后再删」，不能反过来：

        - 原实现是 pipeline 里 hgetall+delete 一次性执行，Redis 增量在 UPDATE
          **之前**就被清空；一旦 UPDATE/commit 失败，增量已永久丢失，与
          「失败保留、下轮重试」的初衷相悖。这里改为写库成功后才 HDEL。
        - 按 field 精确 HDEL 而不是整表 DELETE：hgetall 与 hdel 之间新进来的
          incr 不会被连带清掉（代价是这段窗口内该文章 1~2 次浏览会被覆盖，
          对浏览量这种弱一致指标可接受）。
        - 无法解析的脏 field 也一并清掉：它们永远不能转成数值，留着只会
          每轮重复读、重复告警。
        """
        try:
            all_delta = await redis_client.hgetall(cls.HASH_KEY)
        except Exception:
            logger.warning("读取浏览量增量失败（Redis 不可用？），本轮跳过", exc_info=True)
            return

        if not all_delta:
            return

        params = []
        consumed_fields = []  # 本轮读到的全部 field，写库成功后逐个 HDEL
        for article_id, delta in all_delta.items():
            consumed_fields.append(article_id)
            try:
                params.append({"b_id": int(article_id), "b_delta": int(delta)})
            except (TypeError, ValueError):
                logger.warning("跳过无法解析的浏览量记录: %s=%s", article_id, delta)

        if params:
            # 三个坑都得躲，缺一不可：
            # 1) 必须显式带 WHERE。缺 WHERE 时 SQLAlchemy 会把未被引用的绑定折进
            #    SET，实跑为 `UPDATE article SET id=?, views=(article.views + ?)`，
            #    会改到全表 → UNIQUE 冲突（IntegrityError），回写每轮必失败。
            # 2) 绑定名不能与列名同名。executemany 带 params 执行时，名为 "id"
            #    的绑定会被当成 SET 子句的隐式赋值并直接抛 CompileError
            #    （bindparam() name 'id' is reserved），故改用 b_id / b_delta。
            # 3) 必须走 Core 的 __table__，不能传 ORM 实体（这条最隐蔽，实测踩过）：
            #    传「列表」params 时 SQLAlchemy 会把语句改写成「ORM Bulk UPDATE by
            #    Primary Key」（bulk_persistence.orm_pre_session_exec 改写
            #    _dml_strategy，**与 synchronize_session 无关**，加 sync=False
            #    挡不住），随后按「映射属性名」去 params 里找主键；我们的键是
            #    b_id/b_delta，交集为空 → InvalidRequestError: No primary key value
            #    supplied for column(s) article.id。这个 raise 发生在编译之前，
            #    stmt.compile() 完全测不出，且会被下方 except 吞掉 →
            #    表现为「回写每轮静默失败、Redis 哈希无限堆积、库值永不增长」，
            #    而详情页走 db+delta 所以看起来一切正常。
            stmt = (
                update(Article.__table__)
                .where(Article.__table__.c.id == bindparam("b_id"))
                .values(views=Article.__table__.c.views + bindparam("b_delta"))
            )
            try:
                await db.execute(
                    stmt,
                    params,
                    execution_options={"synchronize_session": False},
                )
                await db.commit()
            except Exception:
                # 关键：不回滚 Redis。增量仍留在哈希里，下一轮会重新读到并重试。
                logger.exception("浏览量回写数据库失败，增量保留待下轮重试")
                return

        # 走到这里说明要么已提交成功，要么本轮只有脏数据（无需写库）。
        # 只有此时才把消费掉的 field 摘掉，保证「删」永远发生在「写成功」之后。
        try:
            await redis_client.hdel(cls.HASH_KEY, *consumed_fields)
        except Exception:
            # 清理失败最坏是下一轮把同一批增量再写一次（浏览量略微偏高），
            # 远好过反过来丢数据。
            logger.warning("清理已回写的浏览量增量失败（下轮可能重复累加）", exc_info=True)

        logger.info("已回写 %d 篇文章的浏览量", len(params))

    @classmethod
    async def periodic_sync_to_db(cls, interval_seconds: int = SYNC_INTERVAL_SECONDS) -> None:
        """周期执行 ``sync_to_db``，由 main.py 的 lifespan 起一个 task 调用。

        单轮内部已各自吞掉 Redis / DB 异常，这里只负责按间隔驱动，并保证
        能被取消（应用关闭时 task.cancel() 会打断 sleep 并正常退出）。
        """
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    await cls.sync_to_db(session)
            except Exception:
                # sync_to_db 自身已兜底，这里是最后一道防线，避免单轮异常打死整个循环。
                logger.exception("浏览量周期回写任务异常，跳过本轮")
            await asyncio.sleep(interval_seconds)