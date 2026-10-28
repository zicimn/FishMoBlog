from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from utils.responsed import NotFound,info


class CatService:

    def __init__(self,db:AsyncSession):
        self.db = db

    async def GetByName(self, name: str) -> Optional[int]:
        """只读解析分类名 → id，未命中返回 None。

        专供 GET 查询路径：读接口不得顺手建分类（GetOrSave 在 status=True 时会
        写库），且「未命中」必须能区分于「查到 id」——否则调用方会把 None 当
        有效 id 用，`Article.category_id == None` 会误匹配「未分类」文章。
        """
        return await self.db.scalar(
            select(Category.id).where(Category.name == name)
        )
        

    async def GetOrSave(
        self,
        name:str,
        status:bool,
    ):
        query = await self.db.execute(select(Category).where(Category.name == name))
        result = query.scalar_one_or_none()
        
        if status and (not result):#如果不再确认为true则创建
            cat = Category(name=name)
            self.db.add(cat)
            await self.db.commit()
            await self.db.refresh(cat)
            id = cat.id
        else:
            id = result.id
        
        data = {"id":id}
        return info(data=data)

        
        

        
        

