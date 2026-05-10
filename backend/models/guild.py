"""
GuildConfig model — per-server bot configuration.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_name: Mapped[str] = mapped_column(String(100))
    prefix: Mapped[str] = mapped_column(String(10), default="!")
    games_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    polls_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
