import asyncio
from typing import Dict, Tuple, Optional
import ccxt.async_support as ccxt


class ExchangeSessionPool:
    """Asynchronous pool for reusing CCXT client sessions."""

    def __init__(self, maxsize: int = 5):
        self.maxsize = maxsize
        self._pools: Dict[Tuple[str, str, str], asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def _create_exchange(self, exchange_id: str, api_key: str, secret: str):
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            "apiKey": api_key,
            "secret": secret,
            "options": {"defaultType": "future"},
        })
        exchange._pool_key = (exchange_id, api_key, secret)
        return exchange

    async def acquire(self, exchange_id: str, api_key: str, secret: str):
        key = (exchange_id, api_key, secret)
        async with self._lock:
            pool = self._pools.get(key)
            if pool is None:
                pool = asyncio.Queue(maxsize=self.maxsize)
                self._pools[key] = pool
            if not pool.empty():
                exchange = await pool.get()
                return exchange
        return await self._create_exchange(exchange_id, api_key, secret)

    async def release(self, exchange) -> None:
        key: Optional[Tuple[str, str, str]] = getattr(exchange, "_pool_key", None)
        if key is None:
            await exchange.close()
            return
        async with self._lock:
            pool = self._pools.setdefault(key, asyncio.Queue(maxsize=self.maxsize))
        if pool.qsize() < self.maxsize:
            await pool.put(exchange)
        else:
            await exchange.close()


# Global pool instance
exchange_pool = ExchangeSessionPool()
