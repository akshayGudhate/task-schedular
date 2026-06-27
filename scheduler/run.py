import uvicorn
from dotenv import load_dotenv
from app.core.config import get_settings

load_dotenv()

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SCHEDULER_HOST,
        port=settings.SCHEDULER_PORT,
        reload=True,
    )
