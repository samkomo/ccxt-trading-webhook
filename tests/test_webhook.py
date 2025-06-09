import sys
import os
import asyncio
import pytest
import time
import json
import hmac
import hashlib
from fastapi import HTTPException
from unittest.mock import MagicMock
from ccxt.base.errors import ExchangeError, NetworkError

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
from config.settings import settings
from httpx import AsyncClient, ASGITransport
import app.exchange_factory as exchange_factory
import app.routes as routes
from app.auth import verify_token
from app.token_store import issue_token, revoke_token, DB_PATH
from app.rate_limiter import limiter

transport = ASGITransport(app=app)


@pytest.fixture(autouse=True)
def reset_rate_limit():
    limiter.reset()
    if DB_PATH.exists():
        DB_PATH.unlink()
    yield
    limiter.reset()
    if DB_PATH.exists():
        DB_PATH.unlink()


def test_verify_token_valid():
    token = issue_token(ttl=5)
    assert verify_token(token, "nA") is True
    revoke_token(token)


def test_verify_token_invalid():
    assert verify_token("bad_token", "nB") is False


def test_verify_token_expired():
    token = issue_token(ttl=-1)
    assert verify_token(token, "nC") is False


def test_verify_token_missing_fields():
    """Token verification should fail if token or nonce is missing."""
    valid_token = issue_token(ttl=5)
    try:
        assert verify_token(None, "nD") is False
        assert verify_token(valid_token, None) is False
    finally:
        revoke_token(valid_token)

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
        "nonce": "n1",
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
async def test_get_exchange_invalid_id():
    with pytest.raises(HTTPException) as exc:
        await exchange_factory.get_exchange("nosuch", "k", "s")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_invalid_exchange_route():
    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "nx1",
        "exchange": "nosuch",
        "apiKey": "key",
        "secret": "secret",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 1,
        "price": 30000,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 400
    revoke_token(token)


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

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "nvalid1",
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
    revoke_token(token)


@pytest.mark.asyncio
async def test_valid_signature_order(monkeypatch):
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
        "amount": 0.02,
        "price": 31000,
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
        response = await client.post("/webhook", content=body, headers=headers)
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


@pytest.mark.asyncio
async def test_nonce_reuse_rejected(monkeypatch):
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

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "replay1",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/webhook", json=payload)
        assert first.status_code == 200
        second = await client.post("/webhook", json=payload)
        assert second.status_code == 403
    revoke_token(token)


@pytest.mark.asyncio
async def test_invalid_side_rejected():
    payload = {
        "token": settings.WEBHOOK_SECRET,
        "nonce": "bad1",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "hold",
        "amount": 0.01,
        "price": 30000,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_symbol_rejected():
    payload = {
        "token": settings.WEBHOOK_SECRET,
        "nonce": "bad2",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTCUSDT",  # missing slash
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_negative_amount_rejected():
    payload = {
        "token": settings.WEBHOOK_SECRET,
        "nonce": "bad3",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": -1,
        "price": 30000,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_zero_price_rejected():
    payload = {
        "token": settings.WEBHOOK_SECRET,
        "nonce": "bad4",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 0,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_key_required(monkeypatch):
    settings.REQUIRE_API_KEY = True
    settings.STATIC_API_KEY = "testkey"

    dummy_order = {"id": "order1"}

    class DummyExchange:
        async def load_markets(self):
            return {}
        async def create_market_order(self, symbol, side, amount):
            return dummy_order
        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "api1",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 401
    revoke_token(token)
    settings.REQUIRE_API_KEY = False
    settings.STATIC_API_KEY = ""


@pytest.mark.asyncio
async def test_api_key_valid(monkeypatch):
    settings.REQUIRE_API_KEY = True
    settings.STATIC_API_KEY = "testkey"

    dummy_order = {"id": "order1"}

    class DummyExchange:
        async def load_markets(self):
            return {}
        async def create_market_order(self, symbol, side, amount):
            return dummy_order
        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "api2",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }
    headers = {"X-API-Key": "testkey"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload, headers=headers)
        assert response.status_code == 200
    revoke_token(token)
    settings.REQUIRE_API_KEY = False
    settings.STATIC_API_KEY = ""


@pytest.mark.asyncio
async def test_webhook_queue(monkeypatch):
    """Ensure orders are queued when QUEUE_ORDERS is enabled."""
    settings.QUEUE_ORDERS = True

    mock_task = MagicMock()
    monkeypatch.setattr(routes, "place_order_task", mock_task)

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "q1",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "queued"}

    mock_task.delay.assert_called_once_with(payload)
    revoke_token(token)
    settings.QUEUE_ORDERS = False


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Ensure the metrics endpoint returns Prometheus metrics."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "request_latency_seconds" in response.text


@pytest.mark.asyncio
async def test_signature_valid_token_ignored(monkeypatch):
    """A valid HMAC signature should succeed even with an invalid token."""

    dummy_order = {"id": "order1", "status": "ok"}

    class DummyExchange:
        async def load_markets(self):
            return {}

        async def create_market_order(self, symbol, side, amount):
            return dummy_order

        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    payload = {
        "token": "bad",  # invalid token should be ignored
        "nonce": "sig1",
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
        response = await client.post("/webhook", content=body, headers=headers)
        assert response.status_code == 200
        assert response.json()["order"] == dummy_order


@pytest.mark.asyncio
async def test_signature_invalid_overrides_token(monkeypatch):
    """If a signature header is present, token auth is ignored."""

    dummy_order = {"id": "order1", "status": "ok"}

    class DummyExchange:
        async def load_markets(self):
            return {}

        async def create_market_order(self, symbol, side, amount):
            return dummy_order

        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    valid_token = issue_token(ttl=30)
    payload = {
        "token": valid_token,
        "nonce": "sig2",
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
    headers = {
        "X-Signature": "badsignature",
        "X-Timestamp": timestamp,
        "Content-Type": "application/json",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", content=body, headers=headers)
        assert response.status_code == 403
    revoke_token(valid_token)


@pytest.mark.asyncio
async def test_place_market_order_retries(monkeypatch):
    """Ensure network errors trigger retries before succeeding."""

    attempts = 0

    async def side_effect(symbol, side, amount):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise NetworkError("temporary glitch")
        return {"id": "retry", "status": "ok"}

    class DummyExchange:
        async def create_market_order(self, symbol, side, amount):
            return await side_effect(symbol, side, amount)

    async def no_sleep(_):
        pass

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    result = await routes.place_market_order(DummyExchange(), "BTC/USDT", "buy", 1)
    assert result == {"id": "retry", "status": "ok"}
    assert attempts == 3


@pytest.mark.asyncio
async def test_webhook_exchange_error(monkeypatch):
    """Exchange errors should return HTTP 400."""

    class DummyExchange:
        async def load_markets(self):
            return {}

        async def create_market_order(self, symbol, side, amount):
            raise ExchangeError("oops")

        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "ex1",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 400
        assert "Exchange error" in response.text
    revoke_token(token)


@pytest.mark.asyncio
async def test_webhook_network_error(monkeypatch):
    """Network errors should return HTTP 502."""

    class DummyExchange:
        async def load_markets(self):
            return {}

        async def create_market_order(self, symbol, side, amount):
            raise NetworkError("timeout")

        async def close(self):
            pass

    async def mock_get_exchange(*args, **kwargs):
        return DummyExchange()

    monkeypatch.setattr(exchange_factory, "get_exchange", mock_get_exchange)
    monkeypatch.setattr(routes, "get_exchange", mock_get_exchange)

    token = issue_token(ttl=30)
    payload = {
        "token": token,
        "nonce": "net1",
        "exchange": "binance",
        "apiKey": "x",
        "secret": "y",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 30000,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 502
        assert "Network error" in response.text
    revoke_token(token)

