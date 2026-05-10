"""
Guild configuration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.dependencies import get_db
from backend.models import GuildConfig
from backend.schemas import GuildConfigCreate, GuildConfigUpdate, GuildConfigResponse

router = APIRouter(prefix="/guilds", tags=["Guilds"])


@router.post("/", response_model=GuildConfigResponse, status_code=status.HTTP_201_CREATED)
async def register_guild(payload: GuildConfigCreate, db: AsyncSession = Depends(get_db)):
    """Register a guild or refresh its name if already stored."""
    result = await db.execute(select(GuildConfig).where(GuildConfig.guild_id == payload.guild_id))
    guild = result.scalar_one_or_none()

    if guild:
        guild.guild_name = payload.guild_name
    else:
        guild = GuildConfig(**payload.model_dump())
        db.add(guild)

    await db.commit()
    await db.refresh(guild)
    return guild


@router.get("/{guild_id}", response_model=GuildConfigResponse)
async def get_guild_config(guild_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a guild's configuration."""
    result = await db.execute(select(GuildConfig).where(GuildConfig.guild_id == guild_id))
    guild = result.scalar_one_or_none()

    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    return guild


@router.patch("/{guild_id}", response_model=GuildConfigResponse)
async def update_guild_config(guild_id: int, payload: GuildConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Update a guild's bot configuration (prefix, channels, language)."""
    result = await db.execute(select(GuildConfig).where(GuildConfig.guild_id == guild_id))
    guild = result.scalar_one_or_none()

    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(guild, field, value)

    await db.commit()
    await db.refresh(guild)
    return guild
