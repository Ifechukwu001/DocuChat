from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent


class EnvSettings(BaseSettings):
    """Env Settings."""

    model_config = SettingsConfigDict(extra="ignore")

    IS_PRODUCTION: bool = False

    ALLOWED_ORIGINS: list[str] = []

    DB_URL: PostgresDsn | str = ""

    REDIS_URL: str = ""

    JWT_ACCESS_SECRET: str = ""
    JWT_REFRESH_SECRET: str = ""

    OPENAI_API_KEY: str = ""

    EXAMPLE_WEBHOOK_SECRET: str = ""

    HITL_CONFIDENCE_THRESHOLD: float = 0.6
    HITL_ESCALATION_ENABLED: bool = True
    HITL_REVIEW_MAX_QUEUE_SIZE: int = 100
    HITL_SLA_MINUTES: int = 60


settings = EnvSettings()
