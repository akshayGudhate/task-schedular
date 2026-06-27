from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
import structlog

from app.core.config import get_settings

log = structlog.get_logger()

# module-level pool — assigned in create_pool(), used everywhere else
_pool: Optional[asyncpg.Pool] = None

# create a pool of connections to the database
async def create_pool() -> None:
    global _pool
    s = get_settings()
    _pool = await asyncpg.create_pool(
        s.SCHEDULER_DB_URL,
        min_size=s.DB_POOL_MIN_SIZE,
        max_size=s.DB_POOL_MAX_SIZE,
        command_timeout=60,
    )
    log.info("db.pool.ready", min_size=s.DB_POOL_MIN_SIZE, max_size=s.DB_POOL_MAX_SIZE)

# close the pool of connections to the database
async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log.info("db.pool.closed")

# get a connection from the pool
@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    # acquire a connection from the pool — connection returns automatically on exit
    if _pool is None:
        raise RuntimeError("db pool not initialized — call create_pool() in app lifespan first")
    async with _pool.acquire() as conn:
        yield conn
