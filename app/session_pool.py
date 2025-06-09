import logging
from typing import Dict, Any

from app.exchange_factory import get_exchange

logger = logging.getLogger("webhook_logger")

# Cached exchange instances by exchange id
_sessions: Dict[str, Any] = {}
# Cached markets per exchange id
_markets: Dict[str, Dict[str, Any]] = {}

async def get_persistent_exchange(exchange_id: str, api_key: str, secret: str):
    """Return a persistent exchange instance and cache its markets."""
    exchange = _sessions.get(exchange_id)
    if not exchange:
        exchange = await get_exchange(exchange_id, api_key, secret)
        _sessions[exchange_id] = exchange
    if exchange_id not in _markets:
        _markets[exchange_id] = await exchange.load_markets()
    return exchange


def get_market(exchange_id: str, symbol: str):
    """Retrieve market metadata for a symbol from the cache."""
    return _markets.get(exchange_id, {}).get(symbol)
