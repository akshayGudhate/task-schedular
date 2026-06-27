from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings, check_required_env_vars
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.middleware.setup import register_middleware

settings = get_settings()

# must run before any structlog call in the process
setup_logging(debug=settings.DEBUG)

log = structlog.get_logger()

# context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = check_required_env_vars()
    if missing:
        raise RuntimeError(f"missing required env vars: {missing}")
    log.info("executor.starting", version=settings.APP_VERSION)
    yield
    log.info("executor.stopped")

# main app
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

# register middleware
register_middleware(app)
register_error_handlers(app)
app.include_router(router)
