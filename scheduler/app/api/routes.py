from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_description="Service is up and reachable",
)
def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
