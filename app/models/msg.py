from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from config.db import Base


class Msg(Base):
    """留言表：每个用户最多一条（唯一约束 + 应用层检查）。"""

    __tablename__ = "msg"
    __table_args__ = (
        # 一人一条；MySQL 的唯一索引允许多个 NULL，删号后的历史留言互不冲突。
        UniqueConstraint("user_id", name="uk_msg_user"),
        {"comment": "留言表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ON DELETE SET NULL：删号后保留留言正文与昵称快照，仅断开用户关联。
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        comment="留言者用户ID（NULL 表示账号已删除）",
    )

    # 昵称/头像为发布当时的快照，用户日后改名换头像不影响历史留言。
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="昵称快照")
    avatar: Mapped[Optional[str]] = mapped_column(String(500), comment="头像快照")

    content: Mapped[str] = mapped_column(Text, nullable=False, comment="留言内容（入库前经 nh3 白名单消毒）")
    ip: Mapped[str] = mapped_column(String(255), nullable=False, comment="来源 IP（不对外返回）")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")