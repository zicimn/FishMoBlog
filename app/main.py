import asyncio
import contextlib
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import service_router
from utils.counter import ArticleViewCounter


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    sync_task = asyncio.create_task(ArticleViewCounter.periodic_sync_to_db())
    try:
        yield
    finally:
        sync_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sync_task


app = FastAPI(lifespan=lifespan)


# 默认同时放行博客前台(3000)与管理端(3001)。注意 getenv 只收 1~2 个参数，
# 且 CORS_ORIGINS 的约定格式是「逗号分隔的单字符串」，故这里给整串、下一行 split。
# .env 里若显式配了 CORS_ORIGINS，会整体覆盖这里的默认值。
cors_origins_str = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
)
cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(service_router)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, reload_excludes=["*.log", "__pycache__/*"])