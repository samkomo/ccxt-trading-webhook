"""Signature replay protection cache."""

import time
from typing import Dict

from config.settings import settings

# Optional Redis support
if settings.model_fields.get('SIGNATURE_CACHE_BACKEND') and settings.SIGNATURE_CACHE_BACKEND == "redis":
    import redis.asyncio as redis  # type: ignore
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
else:
    redis_client = None  # type: ignore

# In-memory cache structure {signature: expiry}
_cache: Dict[str, float] = {}

async def is_duplicate(signature: str) -> bool:
    """Check if signature was seen recently and store it."""
    ttl = getattr(settings, "SIGNATURE_CACHE_TTL", 0)
    if ttl <= 0:
        return False

    now = time.time()

    if redis_client is not None:
        if await redis_client.exists(signature):
            return True
        await redis_client.setex(signature, ttl, "1")
        return False

    # purge expired
    expired = [sig for sig, exp in _cache.items() if exp < now]
    for sig in expired:
        del _cache[sig]

    if signature in _cache:
        return True

    _cache[signature] = now + ttl
    return False

async def clear_cache() -> None:
    """Clear cache contents (for tests)."""
    if redis_client is not None:
        await redis_client.flushdb()
    else:
        _cache.clear()
