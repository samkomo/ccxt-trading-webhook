import ccxt.async_support as ccxt
from fastapi import HTTPException, status
from typing import Dict, Tuple, Optional
from config.settings import settings

# Cached exchange instances keyed by (exchange_id, api_key)
_sessions: Dict[Tuple[str, str], ccxt.Exchange] = {}

async def get_persistent_exchange(exchange_id: str, api_key: Optional[str] = None, secret: Optional[str] = None) -> ccxt.Exchange:
    """Return a cached ccxt client or create one if missing."""
    exchange_id = exchange_id.lower()
    if exchange_id not in ccxt.exchanges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exchange '{exchange_id}' is not supported by CCXT."
        )

    exchange_class = getattr(ccxt, exchange_id)
    api_key = api_key or settings.DEFAULT_API_KEY
    secret = secret or settings.DEFAULT_API_SECRET

    if not api_key or not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API credentials for exchange '{exchange_id}'."
        )

    key = (exchange_id, api_key)
    if key in _sessions:
        return _sessions[key]

    try:
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            'options': {'defaultType': 'future'}
        })
        _sessions[key] = exchange
        return exchange
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize exchange '{exchange_id}': {str(e)}"
        )

async def close_all_sessions() -> None:
    """Close all cached exchange sessions."""
    for exchange in list(_sessions.values()):
        try:
            await exchange.close()
        except Exception:
            pass
    _sessions.clear()
