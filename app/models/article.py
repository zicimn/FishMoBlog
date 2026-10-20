from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.db import Base

if TYPE_CHECKING:
    from .category import Category
    from .column import BlogColumn

# status 取值（与前端 articleStatusMap 一致）
STATUS_NORMAL = 1  # 正常，对外可见
STATUS_HIDDEN = 2  # 隐藏，仅后台可见
STATUS_DRAFT = 3  # 草稿，仅后台可见

# 对博客端可见的状态集合
STATUS_PUBLIC = (STATUS_NORMAL,)

 
class Article(Base):

    __tablename__ = "article"
    __table_args__ = (
        Index("idx_article_category", "category_id"),
        Index("idx_article_status", "status"),
        Index("idx_article_created", "created_at"),
        # Index("idx_article_weight", "weight"),
        {"comment": "文章表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, comment="访问路径(slug)")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="摘要")
    thumbnail: Mapped[Optional[str]] = mapped_column(String(500), comment="封面图")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="正文 HTML")
    # 文章页自定义背景色（CSS 颜色值），留空则用主题默认背景
    style: Mapped[Optional[str]] = mapped_column(String(50), comment="文章背景色")

    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("category.id", ondelete="SET NULL"), comment="分类ID"
    )

    status: Mapped[int] = mapped_column(Integer, nullable=False, default=STATUS_NORMAL, comment="1正常 2隐藏 3草稿")
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="浏览量")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    category: Mapped[Optional["Category"]] = relationship(
        "Category", lazy="selectin", passive_deletes=True
    )
    columns: Mapped[List["BlogColumn"]] = relationship(
        "BlogColumn",
        secondary="article_column",
        back_populates="articles",
        lazy="selectin",
        passive_deletes=True,
    )