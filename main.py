"""FastAPI application entry point.

This module creates the ``FastAPI`` application instance, configures logging,
rate limiting and metrics middleware, and registers the API routes used by the
webhook service.
"""

from fastapi import FastAPI
from app.api.routes import router as webhook_router
from app.identity.routes import router as identity_router
import logging
from app.utils import setup_logger
from app.rate_limiter import limiter
from app.https_middleware import HttpsMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.dashboard.metrics import MetricsMiddleware, metrics
from app.identity.permissions import PermissionMiddleware

# Initialize application and configure logging
app = FastAPI()
setup_logger()

# Register rate limiter and error handling middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(PermissionMiddleware)
app.add_middleware(HttpsMiddleware)

# Mount application routes
app.include_router(webhook_router)
app.include_router(identity_router)

@app.get("/")
async def health_check() -> dict:
    """Health check endpoint used by monitoring systems.

    Returns:
        dict: Service status message.
    """
    return {"status": "running", "message": "Webhook server ready"}


@app.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics collected by the ``MetricsMiddleware``.

    Returns:
        Any: Text metrics in Prometheus format.
    """
    return metrics()
