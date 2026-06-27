import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# extend when adding required vars
REQUIRED_ENV_VARS = [
    "SCHEDULER_DB_URL",
    "EXECUTOR_BASE_URL",
]

# check required env vars
def check_required_env_vars() -> list[str]:
    return [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]


# settings
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # required
    SCHEDULER_DB_URL:  str
    EXECUTOR_BASE_URL: str  # e.g. http://executor:8090

    # identity
    APP_NAME:    str = "Task Scheduler"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    # server
    SCHEDULER_HOST: str = "0.0.0.0"
    SCHEDULER_PORT: int = 8080

    # cors — comma-separated origins, or "*" for open (dev default)
    CORS_ALLOW_ORIGINS: str = "*"

    # db pool
    DB_POOL_MIN_SIZE: int = 2
    DB_POOL_MAX_SIZE: int = 10

    # retry
    RETRY_BASE_DELAY_SECONDS: int = 60   # doubles each attempt: 60, 120, 240…

    # polling
    POLL_INTERVAL_SECONDS: int = 5    # how often to ping check_url
    POLL_MAX_ATTEMPTS:     int = 60   # give up after 5 min (60 × 5s)

    # webhook
    WEBHOOK_TIMEOUT_SECONDS: int = 30

    # apscheduler
    MISFIRE_GRACE_TIME_SECONDS: int = 300  # how late a job can still fire


# cache settings
@lru_cache
def get_settings() -> Settings:
    return Settings()
