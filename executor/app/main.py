from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.db.database import create_pool, close_pool
from app.middleware.setup import register_middleware

settings = get_settings()

# must run before any structlog call in the process
setup_logging(debug=settings.DEBUG)

log = structlog.get_logger()

_tags = [
    {
        "name": "webhooks",
        "description": "Simulated webhook endpoints — sync (200) and async (202).",
    },
    {
        "name": "status",
        "description": "Poll execution status for async webhooks.",
    },
    {
        "name": "health",
        "description": "Liveness check — confirms the service is up and reachable.",
    },
]

_description = """
Receives webhook execution requests from the scheduler, runs them synchronously or
asynchronously, and records the outcome.

**Sync endpoints (return 200 immediately)**
- `POST /send-welcome` — sends a welcome email
- `POST /security-alert` — dispatches a security alert

**Async endpoints (return 202 + check_url)**
- `POST /notify-admin` — notifies admin dashboard (~3s processing)
- `POST /daily-report` — generates daily summary report (~5s processing)

**Polling**
- `GET /status/{execution_id}` — poll until `COMPLETED` or `FAILED`
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    log.info("executor.starting", version=settings.APP_VERSION)
    yield
    await close_pool()
    log.info("executor.stopped")


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
