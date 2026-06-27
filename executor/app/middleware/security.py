from __future__ import annotations

import secure
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# singleton — headers computed once at startup
_secure = secure.Secure()

# security headers middleware
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        _secure.framework.fastapi(response)
        return response
