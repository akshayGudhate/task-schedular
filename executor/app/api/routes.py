from fastapi import APIRouter

from app.api import webhooks
from app.api import status as status_api

router = APIRouter()

router.include_router(webhooks.router, tags=["webhooks"])
router.include_router(status_api.router, tags=["status"])


@router.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Returns `ok` when the service is up and the DB pool is initialized.",
)
def health():
    from app.core.config import get_settings

    s = get_settings()
    return {"status": "ok", "service": s.APP_NAME, "version": s.APP_VERSION}
