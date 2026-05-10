"""
User endpoints — registration, profile, and genre preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.dependencies import get_db
from backend.models import User
from backend.schemas import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user or update their username if they already exist."""
    result = await db.execute(select(User).where(User.discord_id == payload.discord_id))
    user = result.scalar_one_or_none()

    if user:
        user.username = payload.username
    else:
        user = User(**payload.model_dump())
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{discord_id}", response_model=UserResponse)
async def get_user(discord_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a user's profile by their Discord ID."""
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.patch("/{discord_id}", response_model=UserResponse)
async def update_user(discord_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update a user's preferences (e.g. favorite genres)."""
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{discord_id}/query", status_code=status.HTTP_204_NO_CONTENT)
async def increment_query_count(discord_id: int, db: AsyncSession = Depends(get_db)):
    """Increment the anime query counter for a user (called after each /anime command)."""
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.total_queries += 1
    await db.commit()
