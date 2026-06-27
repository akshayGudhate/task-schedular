from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = structlog.get_logger()

# app error
class AppError(Exception):
    # base for all domain errors — subclass to set status_code and error_code
    status_code: int = 500
    error_code:  str = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# not found error
class NotFoundError(AppError):
    status_code = 404
    error_code  = "NOT_FOUND"


# conflict error
class ConflictError(AppError):
    # valid op, wrong state — e.g. cancelling a task that's already done
    status_code = 409
    error_code  = "CONFLICT"


# bad request error
class BadRequestError(AppError):
    # domain-level bad input, distinct from pydantic's 422
    status_code = 400
    error_code  = "BAD_REQUEST"


# invalid transition error
class InvalidTransitionError(AppError):
    # illegal state machine move
    status_code = 409
    error_code  = "INVALID_TRANSITION"


# error body
def _error_body(message: str, error_code: str) -> dict:
    return {"detail": message, "error_code": error_code}


# app error handler
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


# unhandled error handler
async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # last resort — log traceback, return safe 500
    log.error(
        "unhandled.exception",
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body("internal server error", "INTERNAL_ERROR"),
    )


# register error handlers
def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)          # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_error_handler)   # type: ignore[arg-type]
