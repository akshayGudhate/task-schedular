from fastapi import APIRouter

from app.core.config import get_settings

# router
router = APIRouter()

# get settings
settings = get_settings()

# health route
@router.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}