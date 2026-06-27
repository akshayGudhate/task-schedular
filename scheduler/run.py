import sys
import uvicorn
from dotenv import load_dotenv
from app.core.config import check_required_env_vars, get_settings

# load .env before checking — vars might be in file but not shell
load_dotenv()

# fail fast if any required env vars are missing
missing = check_required_env_vars()
if missing:
    print("\n[ERROR] Required environment variables are not set:\n")
    for var in missing:
        print(f"  {var}")
    print("\nCopy .env.example to .env and fill in the required values.\n")
    sys.exit(1)

# get settings
settings = get_settings()

# entry point for the scheduler service
if __name__ == "__main__":
    # run the FastAPI app using uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SCHEDULER_HOST,
        port=settings.SCHEDULER_PORT,
        reload=True,
    )
