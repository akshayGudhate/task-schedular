import uvicorn
from app.core.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.EXECUTOR_HOST,
        port=settings.EXECUTOR_PORT,
        reload=True,
    )
