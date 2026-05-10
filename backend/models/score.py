"""
Score and CommunityStats models.
"""

from datetime import datetime, timezone
from sqlalchemy import BigInteger, Integer, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Score(Base):
    """Cumulative trivia score per user per guild."""

    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("user_discord_id", "guild_id", name="uq_score_user_guild"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_discord_id: Mapped[int] = mapped_column(BigInteger, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CommunityStats(Base):
    """Aggregated usage statistics per guild."""

    __tablename__ = "community_stats"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    anime_queries: Mapped[int] = mapped_column(Integer, default=0)
    trivia_games_played: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
