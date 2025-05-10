from fastapi import FastAPI, Request
from app.routes import router as webhook_router
import logging
from app.utils import setup_logger

app = FastAPI()
setup_logger()

app.include_router(webhook_router)

@app.get("/")
async def health_check():
    return {"status": "running", "message": "Webhook server ready"}
