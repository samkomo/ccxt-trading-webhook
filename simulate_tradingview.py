import requests
import time
import json

url = "https://ccxt-fastapi-webhook-1f2d93f5c1ad.herokuapp.com/webhook"

payload = {
    "token": "cba4d11bd31f78dfad55214f827ae89674e6700ccf427d6b67844045d55c47ec",
    "exchange": "Bybit",
    "apiKey": "qqVTN5OcwqS894rjB0",
    "secret": "UYWEEclkTsrhkRBQTnw7pJtL6iuBckQQAPJE",
    "symbol": "SOL/USDT",
    "side": "buy",
    "amount": 20,
    "price": 178
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
