from fastapi import FastAPI, Request
from app.routes import router as webhook_router
import logging
from app.utils import setup_logger
from app.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

app = FastAPI()
setup_logger()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(webhook_router)

@app.get("/")
async def health_check():
    return {"status": "running", "message": "Webhook server ready"}
