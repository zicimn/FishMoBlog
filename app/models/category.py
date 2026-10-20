from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.db import Base

if TYPE_CHECKING:
    from .column import BlogColumn


class Category(Base):

    __tablename__ = "category"

    # __table_args__ = (
    #     Index("idx_category_weight", "weight"),
    #     {"comment": "分类表"},
    # )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="分类名")
   
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    # 删除分类时不需要先加载专栏，关联表的清理由数据库外键级联完成
    columns: Mapped[List["BlogColumn"]] = relationship(
        "BlogColumn",
        secondary="column_category",
        back_populates="categories",
        lazy="raise",
        passive_deletes=True,
    )