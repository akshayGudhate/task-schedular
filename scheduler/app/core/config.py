from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # required — pydantic raises ValidationError on startup if these are missing
    SCHEDULER_DB_URL: str
    EXECUTOR_BASE_URL: str  # e.g. http://executor:8090

    APP_NAME: str = "Task Scheduler"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    SCHEDULER_HOST: str = "0.0.0.0"
    SCHEDULER_PORT: int = 8080

    CORS_ALLOW_ORIGINS: str = "*"  # comma-separated, or "*" for open (dev default)

    DB_POOL_MIN_SIZE: int = 2
    DB_POOL_MAX_SIZE: int = 10

    RETRY_BASE_DELAY_SECONDS: int = 60  # doubles each attempt: 60, 120, 240…

    POLL_INTERVAL_SECONDS: int = 5  # how often to ping check_url
    POLL_MAX_ATTEMPTS: int = 60  # give up after 5 min (60 × 5s)

    WEBHOOK_TIMEOUT_SECONDS: int = 30

    MISFIRE_GRACE_TIME_SECONDS: int = 300  # how late a job can still fire


@lru_cache
def get_settings() -> Settings:
    return Settings()
