"""Celery tasks for asynchronous order placement."""

import asyncio
import logging
import os
from celery import Celery
from ccxt.base.errors import ExchangeError, NetworkError

from app.execution.exchange_factory import get_exchange, release_exchange

celery_app = Celery(__name__)
celery_app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

logger = logging.getLogger("webhook_logger")


async def _execute_order(payload: dict) -> dict:
    """Execute a market order asynchronously via CCXT.

    Args:
        payload: Dictionary containing order parameters. Expected keys are
            ``exchange``, ``apiKey``, ``secret``, ``symbol``, ``side`` and
            ``amount``.

    Returns:
        dict: Raw order data returned by CCXT.
    """
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
            await release_exchange(exchange)


@celery_app.task(name="place_order")
def place_order_task(payload: dict) -> dict:
    """Synchronously execute ``_execute_order`` inside a Celery worker.

    Args:
        payload: Same structure as expected by ``_execute_order``.

    Returns:
        dict: Order information returned from the exchange.
    """
    return asyncio.run(_execute_order(payload))
