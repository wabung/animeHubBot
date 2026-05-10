from datetime import datetime
from pydantic import BaseModel


class GuildConfigCreate(BaseModel):
    guild_id: int
    guild_name: str
    prefix: str = "!"
    games_channel_id: int | None = None
    polls_channel_id: int | None = None
    language: str = "en"


class GuildConfigUpdate(BaseModel):
    guild_name: str | None = None
    prefix: str | None = None
    games_channel_id: int | None = None
    polls_channel_id: int | None = None
    language: str | None = None


class GuildConfigResponse(BaseModel):
    guild_id: int
    guild_name: str
    prefix: str
    games_channel_id: int | None
    polls_channel_id: int | None
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
