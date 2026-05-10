"""
AnimeHub FastAPI backend.
Run with: uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.database import create_tables
from backend.routers import users_router, guilds_router, scores_router, stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="AnimeHub API",
    description="Backend REST API for the AnimeHub Discord bot.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users_router)
app.include_router(guilds_router)
app.include_router(scores_router)
app.include_router(stats_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
