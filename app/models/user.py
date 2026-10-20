from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, SmallInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped,mapped_column
from typing import Optional
from config.db import Base

class User(Base):
    __tablename__ = "user"  # 数据库表名
    
    id : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，自增ID
    username : Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # 用户名，唯一，必填，有索引
    email : Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)  # 邮箱，唯一，必填，有索引 
    password_hash : Mapped[str] = mapped_column(String(255), nullable=False)  # 密码哈希，必填
    avatar : Mapped[Optional[str]] = mapped_column(String(255))  # 头像URL，可选
    bio : Mapped[Optional[str]] = mapped_column(Text)  # 个人简介，长文本，可选
    status : Mapped[int] = mapped_column(SmallInteger, default=1, comment="0-禁用 1-正常")  # 状态，默认正常
    is_admin : Mapped[Optional[int]] = mapped_column(SmallInteger, default=0)  # 是否管理员，默认否
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")