"""
Community statistics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.dependencies import get_db
from backend.models import CommunityStats
from backend.schemas import CommunityStatsResponse

router = APIRouter(prefix="/stats", tags=["Stats"])


async def _get_or_create_stats(guild_id: int, db: AsyncSession) -> CommunityStats:
    result = await db.execute(select(CommunityStats).where(CommunityStats.guild_id == guild_id))
    stats = result.scalar_one_or_none()
    if not stats:
        stats = CommunityStats(guild_id=guild_id)
        db.add(stats)
        await db.commit()
        await db.refresh(stats)
    return stats


@router.get("/{guild_id}", response_model=CommunityStatsResponse)
async def get_stats(guild_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve aggregated community stats for a guild."""
    stats = await _get_or_create_stats(guild_id, db)
    return stats


@router.post("/{guild_id}/query", status_code=204)
async def increment_queries(guild_id: int, db: AsyncSession = Depends(get_db)):
    """Increment the anime query counter for a guild."""
    stats = await _get_or_create_stats(guild_id, db)
    stats.anime_queries += 1
    await db.commit()


@router.post("/{guild_id}/trivia", status_code=204)
async def increment_trivia(guild_id: int, db: AsyncSession = Depends(get_db)):
    """Increment the trivia games counter for a guild."""
    stats = await _get_or_create_stats(guild_id, db)
    stats.trivia_games_played += 1
    await db.commit()


@router.post("/{guild_id}/active_user", status_code=204)
async def increment_active_users(guild_id: int, db: AsyncSession = Depends(get_db)):
    """Increment the active users counter for a guild."""
    stats = await _get_or_create_stats(guild_id, db)
    stats.active_users += 1
    await db.commit()
