from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
import structlog

from app.core.config import get_settings

log = structlog.get_logger()

_pool: Optional[asyncpg.Pool] = None


def get_pool() -> asyncpg.Pool:
    # mirrors get_settings() — fails fast if create_pool() wasn't called in lifespan
    if _pool is None:
        raise RuntimeError(
            "db pool not initialized — call create_pool() in lifespan first"
        )
    return _pool


async def create_pool() -> None:
    global _pool
    s = get_settings()
    _pool = await asyncpg.create_pool(
        s.EXECUTOR_DB_URL,
        min_size=s.DB_POOL_MIN_SIZE,
        max_size=s.DB_POOL_MAX_SIZE,
        command_timeout=60,
    )
    log.info("db.pool.ready", min_size=s.DB_POOL_MIN_SIZE, max_size=s.DB_POOL_MAX_SIZE)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("db.pool.closed")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    async with get_pool().acquire() as conn:
        yield conn
