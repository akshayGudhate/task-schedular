from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security import SecureHeadersMiddleware


def register_middleware(app: FastAPI) -> None:
    # last added = outermost (first to receive the request)
    # request flow: CORS → GZip → SecureHeaders → RequestId → routes
    settings = get_settings()
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecureHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
