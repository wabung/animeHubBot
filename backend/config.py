"""
Application settings loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/animehub"
    debug: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
