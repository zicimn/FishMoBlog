from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession,create_async_engine
from sqlalchemy.orm import declarative_base
from config.security import ASYNC_DATABASE_URL

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size = 10,
    max_overflow = 20,
    pool_recycle = 3600, #1小时回收
    pool_timeout = 30,
    pool_pre_ping = True, #执行前测ping
    connect_args = {"connect_timeout": 10}  # 连接超时（秒）
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # 只读请求没有待写变更，无需提交（避免 GET 也开写事务）。
            if session.new or session.dirty or session.deleted:
                await session.commit()
        except Exception:
            await session.rollback()
            raise