import sys
import os
import pytest
import time
import json
import hmac
import hashlib
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
from config.settings import settings
from httpx import AsyncClient, ASGITransport

transport = ASGITransport(app=app)

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

@pytest.mark.asyncio
async def test_missing_auth():
    """
    Sends a valid payload but no signature or token to simulate unauthorized access.
    Expects a 403 Forbidden from your webhook logic.
    """
    payload = {
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 403
        assert "unauthorized" in response.text.lower()

@pytest.mark.asyncio
async def test_invalid_token():
    payload = {
        "token": "wrong_token",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_expired_timestamp():
    payload = {
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000
    }
    timestamp = str(int(time.time()) - 600)
    body = json.dumps(payload).encode()
    signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "Content-Type": "application/json"
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", content=body, headers=headers)
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_invalid_signature():
    payload = {
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000
    }
    timestamp = str(int(time.time()))
    bad_signature = "deadbeef"
    headers = {
        "X-Signature": bad_signature,
        "X-Timestamp": timestamp,
        "Content-Type": "application/json"
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload, headers=headers)
        assert response.status_code == 403
