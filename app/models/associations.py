from sqlalchemy import Column, ForeignKey, Integer, Table

from config.db import Base

# 文章 ↔ 专栏
article_column = Table(
    "article_column",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("article.id", ondelete="CASCADE"), primary_key=True),
    Column("column_id", Integer, ForeignKey("blog_column.id", ondelete="CASCADE"), primary_key=True),
    comment="文章-专栏关联表",
)

# 专栏 ↔ 分类
column_category = Table(
    "column_category",
    Base.metadata,
    Column("column_id", Integer, ForeignKey("blog_column.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("category.id", ondelete="CASCADE"), primary_key=True),
    comment="专栏-分类关联表",
)