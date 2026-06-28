from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

log = structlog.get_logger()


class AppError(Exception):
    # base for all domain errors — subclass to set status_code and error_code
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class InvalidTransitionError(AppError):
    # illegal state machine move
    status_code = status.HTTP_409_CONFLICT
    error_code = "INVALID_TRANSITION"


def _error_body(message: str, error_code: str) -> dict[str, str]:
    return {"detail": message, "error_code": error_code}


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.warning(
        "app.error",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.message, exc.error_code),
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # last resort — log traceback, return safe 500
    log.error(
        "unhandled.exception",
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("internal server error", "INTERNAL_ERROR"),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_error_handler)  # type: ignore[arg-type]
