import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "path"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Record request latency and continue processing.

        Args:
            request: Incoming ``Request`` object.
            call_next: Function that executes the next middleware/endpoint.

        Returns:
            Response: The response returned by ``call_next``.
        """
        start_time = time.perf_counter()
        response = await call_next(request)
        latency = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(latency)
        return response

def metrics():
    """Expose collected Prometheus metrics as an HTTP response.

    Returns:
        Response: Metrics in Prometheus text format.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
