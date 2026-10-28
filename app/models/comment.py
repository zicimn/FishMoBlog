from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from config.db import Base

# status 取值
STATUS_PENDING = 0  # 待审核，不对外展示
STATUS_NORMAL = 1  # 正常
STATUS_HIDDEN = 2  # 已屏蔽


class Comment(Base):

    __tablename__ = "comment"
    __table_args__ = (
        Index("idx_comment_article", "article_id"),
        Index("idx_comment_parent", "parent_id"),
        Index("idx_comment_user", "user_id"),
        Index("idx_comment_status", "status"),
        {"comment": "评论表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("article.id", ondelete="CASCADE"), nullable=False, comment="关联文章ID"
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("comment.id", ondelete="CASCADE"), comment="父评论ID，NULL 表示顶层评论"
    )

    # 已登录用户的评论关联到 user.id；访客评论与本次改造前的存量行均为 NULL。
    # ON DELETE SET NULL：删号时保留评论正文，仅断开链接，昵称/头像靠下面的快照字段兜底。
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        comment="评论者用户ID（NULL 表示访客或历史评论）",
    )

    # user_name / user_avatar 是发布当时的快照，用户日后改名/换头像不影响历史评论展示。
    user_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="评论者昵称")
    user_email: Mapped[Optional[str]] = mapped_column(String(100), comment="评论者邮箱（不公开）")
    user_avatar: Mapped[Optional[str]] = mapped_column(String(500), comment="评论者头像")

    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容 HTML")
    content_text: Mapped[Optional[str]] = mapped_column(Text, comment="评论内容纯文本，用于查重")

    status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=STATUS_NORMAL, comment="0待审核 1正常 2屏蔽"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="评论时间")