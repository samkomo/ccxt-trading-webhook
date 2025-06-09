import ccxt.async_support as ccxt
try:
    import ccxt.pro as ccxtpro
except Exception:  # pragma: no cover - optional dependency
    ccxtpro = None

from config.settings import settings

# Map (exchange_id, api_key, secret, use_ws) -> exchange instance
session_pool = {}

async def get_session(exchange_id: str, api_key: str, secret: str):
    """Return a cached exchange session, creating it if necessary."""
    key = (exchange_id, api_key, secret, settings.USE_WEBSOCKETS)
    if key in session_pool:
        return session_pool[key]

    if settings.USE_WEBSOCKETS and ccxtpro and exchange_id in getattr(ccxtpro, 'exchanges', []):
        exchange_class = getattr(ccxtpro, exchange_id)
    else:
        exchange_class = getattr(ccxt, exchange_id)

    session = exchange_class({
        'apiKey': api_key,
        'secret': secret,
        'options': {
            'defaultType': 'future'
        }
    })
    session_pool[key] = session
    return session

async def close_session(session):
    """Close and remove a session from the pool."""
    if not session:
        return
    try:
        await session.close()
    finally:
        for k, v in list(session_pool.items()):
            if v is session:
                session_pool.pop(k, None)
                break

async def close_all():
    """Close all active sessions."""
    for session in list(session_pool.values()):
        try:
            await session.close()
        except Exception:
            pass
    session_pool.clear()
