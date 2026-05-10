"""
FastAPI dependencies shared across routers.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session per request and close it afterwards."""
    async with AsyncSessionLocal() as session:
        yield session
