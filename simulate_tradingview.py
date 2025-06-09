"""Utility script that sends a test webhook request.

This module can be run directly to simulate how TradingView would call the
``/webhook`` endpoint. The payload is intentionally simple and uses dummy API
credentials.
"""

import json
import time
from typing import Dict

import requests

from app.utils import setup_logger

logger = setup_logger("simulate_tradingview")

# Target endpoint of the locally running FastAPI app
URL = "http://127.0.0.1:8000/webhook"

# Minimal example payload accepted by the webhook route
PAYLOAD: Dict[str, object] = {
    "token": "dummy",
    "exchange": "binance",
    "apiKey": "dummy",
    "secret": "dummy",
    "symbol": "SOL/USDT",
    "side": "sell",
    "amount": 1,
    "price": 174.10,
}

# Static headers for JSON payloads
HEADERS = {"Content-Type": "application/json"}


def send_test_webhook(url: str = URL) -> requests.Response:
    """Send ``PAYLOAD`` to ``url`` and return the response.

    Args:
        url (str): Address of the webhook endpoint.

    Returns:
        requests.Response: HTTP response from the server.
    """

    start = time.monotonic()
    response = requests.post(url, data=json.dumps(PAYLOAD), headers=HEADERS)
    end = time.monotonic()

    logger.info("Status Code: %s", response.status_code)
    logger.info("Response Time: %.4f seconds", end - start)
    logger.info("Response Body: %s", response.json())

    return response


if __name__ == "__main__":
    send_test_webhook()
