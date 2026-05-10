"""
HTTP client for communicating with the AnimeHub FastAPI backend.
All bot cogs should use this instead of calling the DB directly.
"""

import logging
import aiohttp
from typing import Any

logger = logging.getLogger(__name__)

BACKEND_URL = "http://127.0.0.1:8000"


class BackendClient:
    """Async HTTP client wrapping all backend API endpoints."""

    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=self.base_url)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, path: str, **kwargs) -> Any | None:
        session = await self._get_session()
        try:
            async with session.request(method, path, **kwargs) as resp:
                if resp.status == 204:
                    return True
                if resp.ok:
                    return await resp.json()
                logger.error(f"Backend {method} {path} returned {resp.status}: {await resp.text()}")
                return None
        except Exception as e:
            logger.error(f"Backend request failed [{method} {path}]: {e}")
            return None

    # --- Users ---

    async def register_user(self, discord_id: int, username: str, favorite_genres: list[str] = []):
        return await self._request("POST", "/users/", json={
            "discord_id": discord_id,
            "username": username,
            "favorite_genres": favorite_genres,
        })

    async def get_user(self, discord_id: int):
        return await self._request("GET", f"/users/{discord_id}")

    async def update_user_genres(self, discord_id: int, genres: list[str]):
        return await self._request("PATCH", f"/users/{discord_id}", json={"favorite_genres": genres})

    async def increment_user_queries(self, discord_id: int):
        return await self._request("POST", f"/users/{discord_id}/query")

    # --- Guilds ---

    async def register_guild(self, guild_id: int, guild_name: str):
        return await self._request("POST", "/guilds/", json={
            "guild_id": guild_id,
            "guild_name": guild_name,
        })

    async def get_guild_config(self, guild_id: int):
        return await self._request("GET", f"/guilds/{guild_id}")

    async def update_guild_config(self, guild_id: int, **fields):
        return await self._request("PATCH", f"/guilds/{guild_id}", json=fields)

    # --- Scores ---

    async def add_score(self, user_discord_id: int, guild_id: int, username: str, points: int, correct: bool = True):
        return await self._request("POST", "/scores/", json={
            "user_discord_id": user_discord_id,
            "guild_id": guild_id,
            "username": username,
            "points_to_add": points,
            "correct": correct,
        })

    async def get_ranking(self, guild_id: int, limit: int = 10):
        return await self._request("GET", f"/scores/ranking/{guild_id}", params={"limit": limit})

    async def get_user_score(self, guild_id: int, discord_id: int):
        return await self._request("GET", f"/scores/{guild_id}/{discord_id}")

    # --- Stats ---

    async def get_stats(self, guild_id: int):
        return await self._request("GET", f"/stats/{guild_id}")

    async def increment_queries(self, guild_id: int):
        return await self._request("POST", f"/stats/{guild_id}/query")

    async def increment_trivia(self, guild_id: int):
        return await self._request("POST", f"/stats/{guild_id}/trivia")

    async def increment_active_users(self, guild_id: int):
        return await self._request("POST", f"/stats/{guild_id}/active_user")
