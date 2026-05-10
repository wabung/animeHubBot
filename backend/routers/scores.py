"""
Score and ranking endpoints.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.dependencies import get_db
from backend.models import Score, User
from backend.schemas import ScoreUpsert, ScoreResponse, RankingEntry

router = APIRouter(prefix="/scores", tags=["Scores"])


@router.post("/", response_model=ScoreResponse, status_code=status.HTTP_200_OK)
async def upsert_score(payload: ScoreUpsert, db: AsyncSession = Depends(get_db)):
    """
    Add points to a user's score in a guild.
    Creates the score record if it doesn't exist yet.
    Also ensures the user exists in the users table.
    """
    # Ensure user exists
    user_result = await db.execute(select(User).where(User.discord_id == payload.user_discord_id))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(discord_id=payload.user_discord_id, username=payload.username)
        db.add(user)

    # Upsert score
    result = await db.execute(
        select(Score).where(
            Score.user_discord_id == payload.user_discord_id,
            Score.guild_id == payload.guild_id,
        )
    )
    score = result.scalar_one_or_none()

    if not score:
        score = Score(
            user_discord_id=payload.user_discord_id,
            guild_id=payload.guild_id,
            total_points=0,
            games_played=0,
            correct_answers=0,
        )
        db.add(score)
        await db.flush()  # Get the generated ID for the new score

    score.total_points += payload.points_to_add
    score.games_played += 1
    if payload.correct:
        score.correct_answers += 1
    score.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(score)
    return score


@router.get("/ranking/{guild_id}", response_model=list[RankingEntry])
async def get_ranking(guild_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Return the top N users by score in a guild."""
    result = await db.execute(
        select(Score, User.username)
        .join(User, User.discord_id == Score.user_discord_id)
        .where(Score.guild_id == guild_id)
        .order_by(desc(Score.total_points))
        .limit(limit)
    )
    rows = result.all()

    return [
        RankingEntry(
            position=idx + 1,
            user_discord_id=score.user_discord_id,
            username=username,
            total_points=score.total_points,
            games_played=score.games_played,
            correct_answers=score.correct_answers,
        )
        for idx, (score, username) in enumerate(rows)
    ]


@router.get("/{guild_id}/{discord_id}", response_model=ScoreResponse)
async def get_user_score(guild_id: int, discord_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific user's score in a guild."""
    result = await db.execute(
        select(Score).where(
            Score.guild_id == guild_id,
            Score.user_discord_id == discord_id,
        )
    )
    score = result.scalar_one_or_none()

    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    return score
