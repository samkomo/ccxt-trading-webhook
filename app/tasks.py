"""Celery tasks for asynchronous order placement."""

import asyncio
import logging
import os
from celery import Celery
from ccxt.base.errors import ExchangeError, NetworkError

from app.exchange_factory import get_exchange

celery_app = Celery(__name__)
celery_app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

logger = logging.getLogger("webhook_logger")


async def _execute_order(payload: dict) -> dict:
    """Execute an order using CCXT with the given payload."""
    exchange = None
    try:
        exchange = await get_exchange(
            payload["exchange"], payload.get("apiKey"), payload.get("secret")
        )
        await exchange.load_markets()
        order = await exchange.create_market_order(
            symbol=payload["symbol"],
            side=payload["side"],
            amount=payload["amount"],
        )
        logger.info(f"Async order placed: {order}")
        return order
    except (ExchangeError, NetworkError) as e:
        logger.warning(f"Order failed: {e}")
        raise
    finally:
        if exchange:
            await exchange.close()


@celery_app.task(name="place_order")
def place_order_task(payload: dict) -> dict:
    """Celery task wrapper to run the async order coroutine."""
    return asyncio.run(_execute_order(payload))
