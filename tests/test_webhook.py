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
import app.exchange_factory as exchange_factory
import app.routes as routes
from app.auth import verify_token

transport = ASGITransport(app=app)


def test_verify_token_valid():
    assert verify_token(settings.WEBHOOK_SECRET) is True


def test_verify_token_invalid():
    assert verify_token("bad_token") is False

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


@pytest.mark.asyncio
async def test_valid_token_order(monkeypatch):
    dummy_order = {"id": "order1", "status": "filled"}

    class DummyExchange:
        async def load_markets(self):
            return {"SOL/USDT": {"type": "future"}}

        async def create_market_order(self, symbol, side, amount):
            return dummy_order

        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    payload = {
        "token": settings.WEBHOOK_SECRET,
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
        assert response.status_code == 200
        assert response.json()["order"] == dummy_order


@pytest.mark.asyncio
async def test_signature_reuse_rejected(monkeypatch):
    dummy_order = {"id": "order1", "status": "filled"}

    class DummyExchange:
        async def load_markets(self):
            return {"SOL/USDT": {"type": "future"}}

        async def create_market_order(self, symbol, side, amount):
            return dummy_order

        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    payload = {
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "Content-Type": "application/json",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/webhook", content=body, headers=headers)
        assert first.status_code == 200
        second = await client.post("/webhook", content=body, headers=headers)
        assert second.status_code == 403

