from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.db import Base

if TYPE_CHECKING:
    from .article import Article
    from .category import Category


class BlogColumn(Base):
    

    __tablename__ = "blog_column"
    # __table_args__ = (
    #     Index("idx_column_weight", "weight"),
    #     {"comment": "专栏表"},
    # )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="专栏名")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="专栏简介")
    thumbnail: Mapped[Optional[str]] = mapped_column(String(500), comment="专栏封面图")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    # 专栏下的文章可能很多，禁止隐式加载，需要时显式 selectinload
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        secondary="article_column",
        back_populates="columns",
        lazy="raise",
        passive_deletes=True,
    )
    # 分类数量少且基本每次都要展示，随查询一并拉取
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        secondary="column_category",
        back_populates="columns",
        lazy="selectin",
        passive_deletes=True,
    )