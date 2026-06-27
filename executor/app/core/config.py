import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# add here whenever a new required var is introduced
REQUIRED_ENV_VARS = [
    "EXECUTOR_DB_URL",
]


def check_required_env_vars() -> list[str]:
    return [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # required
    EXECUTOR_DB_URL: str

    # identity
    APP_NAME:    str = "Task Executor"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    # server
    EXECUTOR_HOST: str = "0.0.0.0"
    EXECUTOR_PORT: int = 8090

    # cors — comma-separated origins, or "*" for open (dev default)
    CORS_ALLOW_ORIGINS: str = "*"

    # db pool
    DB_POOL_MIN_SIZE: int = 2
    DB_POOL_MAX_SIZE: int = 10

    # execution
    EXECUTION_TIMEOUT_SECONDS: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
