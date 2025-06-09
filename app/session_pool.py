"""Exchange session pool for reusing clients and market data."""

import asyncio
from typing import Dict, Tuple, Any

from app.exchange_factory import get_exchange


class _Session:
    def __init__(self, exchange: Any, markets: Any) -> None:
        self.exchange = exchange
        self.markets = markets


_sessions: Dict[Tuple[str, str, str], _Session] = {}
_lock = asyncio.Lock()


async def get_session(exchange_id: str, api_key: str, secret: str):
    """Retrieve or create a cached exchange session."""
    key = (exchange_id.lower(), api_key, secret)
    async with _lock:
        session = _sessions.get(key)
        if session:
            return session.exchange, session.markets
        exchange = await get_exchange(exchange_id, api_key, secret)
        markets = await exchange.load_markets()
        _sessions[key] = _Session(exchange, markets)
        return exchange, markets


async def close_all_sessions() -> None:
    """Close all cached exchange sessions."""
    async with _lock:
        for session in list(_sessions.values()):
            try:
                await session.exchange.close()
            except Exception:
                pass
        _sessions.clear()
