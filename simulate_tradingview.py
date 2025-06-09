import requests
import time
import json
from app.utils import setup_logger

logger = setup_logger("simulate_tradingview")

url = "http://127.0.0.1:8000/webhook"
payload = {
    "token": "dummy",
    "nonce": str(time.time()),
    "exchange": "binance",
    "apiKey": "dummy",
    "secret": "dummy",
    "symbol": "SOL/USDT",
    "side": "sell",
    "amount": 1,
    "price": 174.10
}


headers = {
    "Content-Type": "application/json"
}

start = time.monotonic()
response = requests.post(url, data=json.dumps(payload), headers=headers)
end = time.monotonic()

logger.info(f"Status Code: {response.status_code}")
logger.info(f"Response Time: {end - start:.4f} seconds")
logger.info("Response Body: %s", response.json())
