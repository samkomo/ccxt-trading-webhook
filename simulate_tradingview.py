import requests
import time
import json

url = "http://127.0.0.1:8000/webhook"
payload = {
    "token": "dummy",
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

print(f"Status Code: {response.status_code}")
print(f"Response Time: {end - start:.4f} seconds")
print("Response Body:", response.json())
