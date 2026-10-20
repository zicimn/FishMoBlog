from datetime import datetime
from typing import Optional,List

from pydantic import BaseModel

class ArticleCard(BaseModel):
    id : int
    title : str
    description: str
    thumbnail: str
    style : Optional[str] = None
    views: int
    time: datetime

class ArticleCardList(BaseModel):
    items: List[ArticleCard]