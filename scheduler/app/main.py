from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.db.database import create_pool, close_pool
from app.middleware.setup import register_middleware
from app.services import scheduler_service

settings = get_settings()

# must run before any structlog call in the process
setup_logging(debug=settings.DEBUG)

log = structlog.get_logger()

_tags = [
    {
        "name": "tasks",
        "description": "Create and manage scheduled tasks.",
    },
    {
        "name": "health",
        "description": "Liveness check — confirms the service is up and reachable.",
    },
]

_description = """
Accepts tasks via REST API, fires outbound webhooks at their scheduled time via
APScheduler, and records every attempt with HTTP status and duration.

**Task lifecycle**
- `POST /tasks` — persists the task and schedules it immediately via `DateTrigger`
- At `execution_time` — scheduler calls the `webhook_url` and records the attempt
- Status flow: `CREATED → RUNNING → SUCCESS / FAILED`
- Non-2xx or timeout → exponential-backoff retry (`RETRYING`) up to `max_retries`
  - Delays double each attempt: 60 s → 120 s → 240 s…
- 202 response → polls `check_url` every `POLL_INTERVAL_SECONDS` until `COMPLETED` or `FAILED`
- `PATCH /tasks/{id}/cancel` — removes the pending job and marks the task `CANCELLED`
- Jobs survive restarts — `CREATED`, `PENDING`, and `RETRYING` tasks reload on startup
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    await scheduler_service.start()
    log.info("scheduler.starting", version=settings.APP_VERSION)
    yield
    await scheduler_service.stop()
    await close_pool()
    log.info("scheduler.stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=_description,
    contact={"name": "Akshay Gudhate", "email": "akshay.gudhate@gmail.com"},
    openapi_tags=_tags,
    lifespan=lifespan,
)

register_middleware(app)
register_error_handlers(app)
app.include_router(router)
