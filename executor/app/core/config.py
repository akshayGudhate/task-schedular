import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# add to this list as new required vars are introduced
REQUIRED_ENV_VARS = [
    "EXECUTOR_DB_URL",
]

# check if all required env vars are set
def check_required_env_vars() -> list[str]:
    # returns names of any required vars that are missing or empty
    return [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]


# settings for the executor service
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # required — no default, must be in .env
    EXECUTOR_DB_URL: str

    # optional — have sensible defaults
    APP_NAME: str = "Task Executor"
    APP_VERSION: str = "1.0.0"
    EXECUTOR_HOST: str = "0.0.0.0"
    EXECUTOR_PORT: int = 8090


@lru_cache
def get_settings() -> Settings:
    return Settings()
