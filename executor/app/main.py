from fastapi import FastAPI
from app.core.config import get_settings

# get settings
settings = get_settings()

# entry point for the executor service
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


# just a pulse check — confirms the service is up and reachable
@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
