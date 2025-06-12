import asyncio
import time
import os
import sys
import json
import hmac
import hashlib
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Ensure default configuration for tests
os.environ.setdefault("WEBHOOK_SECRET", "testsecret")
os.environ.setdefault("DEFAULT_EXCHANGE", "binance")
os.environ.setdefault("DEFAULT_API_KEY", "key")
os.environ.setdefault("DEFAULT_API_SECRET", "secret")
os.environ.setdefault("TOKEN_DB_PATH", "test_tokens.db")

from app.identity.auth import verify_signature
from app.execution.session_pool import ExchangeSessionPool
from app.execution.tasks import _execute_order, place_order_task
import app.execution.exchange_factory as exchange_factory
from ccxt.base.errors import NetworkError

class DummyRequest:
    def __init__(self, headers, body=b''):
        self.headers = headers
        self._body = body
    async def body(self):
        return self._body

@pytest.mark.asyncio
async def test_verify_signature_bad_timestamp():
    req = DummyRequest({'X-Timestamp': 'notint', 'X-Signature': 'sig'})
    assert await verify_signature(req) is False

@pytest.mark.asyncio
async def test_verify_signature_missing_header():
    ts = str(int(time.time()))
    req = DummyRequest({'X-Timestamp': ts})
    assert await verify_signature(req) is False

@pytest.mark.asyncio
async def test_session_pool_reuse_and_full(monkeypatch):
    pool = ExchangeSessionPool(maxsize=1)

    class DummyExchange:
        def __init__(self, name):
            self.name = name
            self.closed = False
            self._pool_key = ('binance','k','s')
        async def close(self):
            self.closed = True

    ex1 = DummyExchange('one')
    ex2 = DummyExchange('two')
    created = 0
    async def fake_create(*args, **kwargs):
        nonlocal created
        created += 1
        return ex1 if created == 1 else ex2
    monkeypatch.setattr(pool, '_create_exchange', fake_create)

    a1 = await pool.acquire('binance','k','s')  # returns ex1
    a2 = await pool.acquire('binance','k','s')  # returns ex2
    await pool.release(a1)  # pool now holds ex1
    await pool.release(a2)  # pool full -> ex2 closed
    assert ex2.closed is True

    a3 = await pool.acquire('binance','k','s')
    assert a3 is ex1

@pytest.mark.asyncio
async def test_session_pool_release_without_key():
    pool = ExchangeSessionPool()
    class DummyExchange:
        def __init__(self):
            self.closed = False
        async def close(self):
            self.closed = True
    ex = DummyExchange()
    await pool.release(ex)
    assert ex.closed is True

@pytest.mark.asyncio
async def test_execute_order_success(monkeypatch):
    class DummyExchange:
        async def load_markets(self):
            pass
        async def create_market_order(self, symbol, side, amount):
            return {'id': 'ok'}
        async def close(self):
            pass
    async def fake_get(*args, **kwargs):
        return DummyExchange()
    calls = {'n': 0}
    async def release_mock(exchange):
        calls['n'] += 1
    monkeypatch.setattr('app.execution.tasks.get_exchange', fake_get)
    monkeypatch.setattr('app.execution.tasks.release_exchange', release_mock)

    result = await _execute_order({'exchange':'binance','apiKey':'k','secret':'s','symbol':'BTC/USDT','side':'buy','amount':1})
    assert result == {'id': 'ok'}
    assert calls['n'] == 1

@pytest.mark.asyncio
async def test_execute_order_network_error(monkeypatch):
    class DummyExchange:
        async def load_markets(self):
            pass
        async def create_market_order(self, symbol, side, amount):
            raise NetworkError('oops')
        async def close(self):
            pass
    async def fake_get(*args, **kwargs):
        return DummyExchange()
    async def rel(ex):
        pass
    monkeypatch.setattr('app.execution.tasks.get_exchange', fake_get)
    monkeypatch.setattr('app.execution.tasks.release_exchange', rel)

    with pytest.raises(NetworkError):
        await _execute_order({'exchange':'binance','apiKey':'k','secret':'s','symbol':'BTC/USDT','side':'buy','amount':1})


def test_place_order_task(monkeypatch):
    run_mock = MagicMock(return_value='res')
    monkeypatch.setattr(asyncio, 'run', run_mock)
    out = place_order_task({'a':1})
    assert out == 'res'
    run_mock.assert_called_once()

@pytest.mark.asyncio
async def test_api_key_invalid(monkeypatch):
    from main import app
    from httpx import AsyncClient, ASGITransport
    import app.api.routes as routes
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    settings = __import__('config.settings', fromlist=['settings']).settings
    settings.REQUIRE_API_KEY = True
    settings.STATIC_API_KEY = 'secretkey'

    dummy_order = {'id': '1'}
    class DummyExchange:
        async def load_markets(self):
            return {}
        async def create_market_order(self, symbol, side, amount):
            return dummy_order
        async def close(self):
            pass
    async def mock_get(*a, **kw):
        return DummyExchange()
    monkeypatch.setattr(routes, 'get_exchange', mock_get)
    monkeypatch.setattr(exchange_factory, 'get_exchange', mock_get)

    token = __import__('app.identity.token_store', fromlist=['issue_token']).issue_token(ttl=5)
    payload = {
        'token': token,
        'nonce': 'badkey',
        'exchange': 'binance',
        'apiKey': 'k',
        'secret': 's',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'amount': 1,
        'price': 1,
    }
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post('/webhook', json=payload, headers={'X-API-Key': 'wrong'})
        assert response.status_code == 401
    settings.REQUIRE_API_KEY = False
    settings.STATIC_API_KEY = ''


@pytest.mark.asyncio
async def test_queue_failure(monkeypatch):
    from main import app
    from httpx import AsyncClient, ASGITransport
    import app.api.routes as routes
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    settings = __import__('config.settings', fromlist=['settings']).settings
    settings.QUEUE_ORDERS = True
    failing = MagicMock(side_effect=RuntimeError('boom'))
    monkeypatch.setattr(routes, 'place_order_task', MagicMock(delay=failing))
    payload = {
        'exchange': 'binance',
        'apiKey': 'k',
        'secret': 's',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'amount': 1,
        'price': 1,
    }
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        'X-Signature': signature,
        'X-Timestamp': timestamp,
        'Content-Type': 'application/json',
    }
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post('/webhook', content=body, headers=headers)
        assert response.status_code == 500
    settings.QUEUE_ORDERS = False

@pytest.mark.asyncio
async def test_get_exchange_success(monkeypatch):
    called = {}
    async def fake_acquire(exchange_id, api_key, secret):
        called['args'] = (exchange_id, api_key, secret)
        return 'ok'
    monkeypatch.setattr(exchange_factory, 'exchange_pool', MagicMock(acquire=fake_acquire))
    monkeypatch.setattr(exchange_factory.ccxt, 'exchanges', ['dummy'])
    monkeypatch.setattr(exchange_factory.ccxt, 'dummy', type('X', (), {}), raising=False)
    res = await exchange_factory.get_exchange('dummy', 'a', 'b')
    assert res == 'ok'
    assert called['args'] == ('dummy', 'a', 'b')

@pytest.mark.asyncio
async def test_get_exchange_missing_creds(monkeypatch):
    settings = __import__('config.settings', fromlist=['settings']).settings
    default_key = settings.DEFAULT_API_KEY
    settings.DEFAULT_API_KEY = ''
    settings.DEFAULT_API_SECRET = ''
    monkeypatch.setattr(exchange_factory.ccxt, 'exchanges', ['binance'])
    monkeypatch.setattr(exchange_factory.ccxt, 'binance', type('B', (), {}), raising=False)
    with pytest.raises(HTTPException) as exc:
        await exchange_factory.get_exchange('binance')
    assert exc.value.status_code == 401
    settings.DEFAULT_API_KEY = default_key
    settings.DEFAULT_API_SECRET = 'secret'
