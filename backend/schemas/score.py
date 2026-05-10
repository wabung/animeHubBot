from datetime import datetime
from pydantic import BaseModel


class ScoreUpsert(BaseModel):
    user_discord_id: int
    guild_id: int
    username: str
    points_to_add: int
    correct: bool = True


class ScoreResponse(BaseModel):
    user_discord_id: int
    guild_id: int
    total_points: int
    games_played: int
    correct_answers: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class RankingEntry(BaseModel):
    position: int
    user_discord_id: int
    username: str
    total_points: int
    games_played: int
    correct_answers: int


class CommunityStatsResponse(BaseModel):
    guild_id: int
    anime_queries: int
    trivia_games_played: int
    active_users: int
    last_updated: datetime

    model_config = {"from_attributes": True}
