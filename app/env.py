from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent


class EnvSettings(BaseSettings):
    """Env Settings."""

    model_config = SettingsConfigDict(extra="ignore")

    ALLOWED_ORIGINS: list[str] = []

    DB_URL: PostgresDsn | str = ""

    REDIS_URL: str = ""

    JWT_ACCESS_SECRET: str = ""
    JWT_REFRESH_SECRET: str = ""

    OPENAI_API_KEY: str = ""

    EXAMPLE_WEBHOOK_SECRET: str = ""


settings = EnvSettings()
