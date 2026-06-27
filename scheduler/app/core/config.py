import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# add to this list as new required vars are introduced
REQUIRED_ENV_VARS = [
    "SCHEDULER_DB_URL",
]


def check_required_env_vars() -> list[str]:
    # returns names of any required vars that are missing or empty
    return [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # required — no default, must be in .env
    SCHEDULER_DB_URL: str

    # optional — have sensible defaults
    APP_NAME: str = "Task Scheduler"
    APP_VERSION: str = "1.0.0"
    SCHEDULER_HOST: str = "0.0.0.0"
    SCHEDULER_PORT: int = 8080


@lru_cache
def get_settings() -> Settings:
    return Settings()
