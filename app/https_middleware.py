from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from config.settings import settings


class HttpsMiddleware(BaseHTTPMiddleware):
    """Reject non-HTTPS requests when ``REQUIRE_HTTPS`` is enabled."""

    async def dispatch(self, request: Request, call_next):
        if settings.REQUIRE_HTTPS and request.url.scheme != "https":
            return JSONResponse({"detail": "HTTPS required"}, status_code=400)
        return await call_next(request)
