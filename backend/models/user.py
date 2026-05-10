"""
User model — maps a Discord user to their preferences and activity.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    discord_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100))
    favorite_genres: Mapped[list] = mapped_column(JSON, default=list)
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
