from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.db.database import create_pool, close_pool
from app.db.seed import seed
from app.middleware.setup import register_middleware
from app.services import job_runner

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
- `POST /tasks` — persists the task (`CREATED`) and arms the APScheduler `DateTrigger`
- At `execution_time` — task moves to `PENDING`, then immediately `RUNNING` as the webhook fires
- Status flow: `CREATED → PENDING → RUNNING → SUCCESS / FAILED`
- Non-2xx or timeout → exponential-backoff retry (`RETRYING`) up to `max_retries`
  - Delays double each attempt: 60 s → 120 s → 240 s…
- 202 response → polls `check_url` every `POLL_INTERVAL_SECONDS` until `COMPLETED` or `FAILED`
- `PATCH /tasks/{id}/cancel` — only allowed from `CREATED` or `PENDING`; removes the job and marks `CANCELLED`

**Recurring tasks**
Set `recurrence` to `HOURLY`, `DAILY`, or `CUSTOM_CRON` when creating a task.
After each successful execution the scheduler automatically clones the task with the next
`execution_time` and schedules it — the chain continues indefinitely.
`CUSTOM_CRON` requires a `cron_expression` (standard 5-field cron syntax).

**Seed data**
On first startup, 4 sample tasks are pre-loaded and fire within 2 minutes:
`Send Welcome Email` (30 s), `Notify Admin` (60 s), `Daily Summary Report` (90 s, recurring daily),
`Security Alert` (120 s).

**Reliability**
- Jobs survive restarts — `CREATED`, `PENDING`, and `RETRYING` tasks reload on startup
- Tasks stuck in `RUNNING` at restart are recovered: retried if budget remains, otherwise `FAILED`
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    await seed()  # inserts 4 sample tasks on first startup; no-op if data already exists
    await job_runner.start()  # seed runs first so tasks are in DB when job_runner reloads them
    log.info("scheduler.starting", version=settings.APP_VERSION)
    yield
    await job_runner.stop()
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
