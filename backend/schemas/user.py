from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    discord_id: int
    username: str
    favorite_genres: list[str] = []


class UserUpdate(BaseModel):
    username: str | None = None
    favorite_genres: list[str] | None = None


class UserResponse(BaseModel):
    discord_id: int
    username: str
    favorite_genres: list[str]
    total_queries: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
