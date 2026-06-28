from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # required — pydantic raises ValidationError on startup if these are missing
    EXECUTOR_DB_URL: str

    APP_NAME:    str  = "Task Executor"
    APP_VERSION: str  = "1.0.0"
    DEBUG:       bool = False

    EXECUTOR_HOST: str = "0.0.0.0"
    EXECUTOR_PORT: int = 8090

    CORS_ALLOW_ORIGINS: str = "*"  # comma-separated, or "*" for open (dev default)

    DB_POOL_MIN_SIZE: int = 2
    DB_POOL_MAX_SIZE: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
