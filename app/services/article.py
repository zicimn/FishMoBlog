from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from err import NotFound
from models.article import Article
from schema.article import ArticleCard,ArticleCardList

from typing import Optional

STATUS_NORMAL = 1  # 正常，对外可见
STATUS_HIDDEN = 2  # 隐藏，仅后台可见
STATUS_DRAFT = 3  # 草稿，仅后台可见


class ArticleService:

    def __init__(self,db:AsyncSession):
        self.db = db

    async def GetList(
        self,
        page:int,
        size:int,
    )-> ArticleCardList:
        skip = (page - 1) * size
        #大致应该是卡片形式显示=>封面+悬浮粗体标题+简要+时间
        query = await self.db.execute(
            select(Article.id,Article.title,Article.description,Article.thumbnail,Article.views,Article.style,Article.created_at)
            .where(Article.status == STATUS_NORMAL)
            .order_by(Article.created_at)
        )

        result = query.all()

        if not result:
            raise NotFound("列表为空")

        items = [
            ArticleCard(
                id = r.id,
                title= r.title,
                description= r.description,
                thumbnail=r.thumbnail,
                views= r.views,
                style= r.style,
                time = r.created_at
            )
            for r in result
        ]

        data = ArticleCardList(items=items)
        return data


    async def Get(
        self,
        id:int
    ) ->Optional[Article]:
        
        query = await self.db.execute(
            select(Article)
            .where(Article.id == id)
            .where(Article.status == 1)
        )

        result = query.scalar_one_or_none()

        if not result:
            raise NotFound("没有该文章")
        return result


    

        