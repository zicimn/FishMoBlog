from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_db
from services.article import ArticleService

async def GetArticleService(
    db: AsyncSession = Depends(get_db)
):
    return ArticleService(db)