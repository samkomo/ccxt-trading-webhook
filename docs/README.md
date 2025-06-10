# 🚀 CCXT FastAPI Async Webhook

A production-grade, asynchronous webhook for executing crypto trades using TradingView alerts and `ccxt.async_support`. Secure, tested, and deployable.

---

## 1. 🏁 Project Overview

This project is a production-grade, asynchronous webhook server built with **FastAPI** for **executing cryptocurrency trades** via [TradingView](https://tradingview.com) alerts. It securely handles webhook requests and places live orders on supported crypto exchanges using the [`ccxt`](https://github.com/ccxt/ccxt) library (with async support).

### 🎯 Use Cases
- Automated trading via TradingView strategies
- Backtest-to-execution pipeline
- Scalable webhook backend for crypto signal platforms

### 🛠 Built With
- **FastAPI** – high-performance Python web framework
- **CCXT (async_support)** – unified crypto exchange trading library
- **pytest + httpx** – async-capable testing stack
- **Heroku-ready** – cloud deployment via Procfile

---

## 2. 🚀 Features

- ⚡ **Asynchronous** with FastAPI + `ccxt.async_support`
- 🔐 **Secure dual-mode authentication** (HMAC + timestamp or token fallback)
- 📡 **TradingView-compatible**
- 🧪 **Full async test suite** with `pytest-asyncio` and mocking
- ☁️ **Heroku deployment ready**
- 🚦 **Per-IP rate limiting** via `slowapi`
- 📑 **JSON structured logging** for easy ingestion
- 📊 **Prometheus metrics** available at `/metrics`

---

## 3. 📦 Installation & Setup

```bash
git clone https://github.com/your-username/ccxt-trading-webhook.git
cd ccxt-trading-webhook

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

---

## 4. 🔐 Environment Variables

```env
WEBHOOK_SECRET=your_shared_secret
DEFAULT_EXCHANGE=binance
DEFAULT_API_KEY=your_exchange_api_key
DEFAULT_API_SECRET=your_exchange_api_secret
LOG_LEVEL=INFO
RATE_LIMIT=10/minute
SIGNATURE_CACHE_TTL=300
NONCE_TTL=300
TOKEN_TTL=86400
REQUIRE_HTTPS=false
QUEUE_ORDERS=false
STATIC_API_KEY=
REQUIRE_API_KEY=false
```

| Variable           | Description |
|--------------------|-------------|
| `WEBHOOK_SECRET`   | Shared secret for HMAC or token |
| `DEFAULT_EXCHANGE` | Fallback exchange |
| `DEFAULT_API_KEY`  | Optional fallback key |
| `DEFAULT_API_SECRET` | Optional fallback secret |
| `LOG_LEVEL`        | Logging verbosity |
| `RATE_LIMIT`       | Requests allowed per timeframe |
| `SIGNATURE_CACHE_TTL` | Cache TTL for replay-protection signatures |
| `NONCE_TTL` | Expiration time for stored nonces (seconds) |
| `TOKEN_TTL` | Expiration time for issued tokens (seconds) |
| `REQUIRE_HTTPS` | Reject plain HTTP requests when set to `true` |
| `QUEUE_ORDERS` | Enqueue orders to Celery when enabled |
| `STATIC_API_KEY` | API key expected in the `X-API-Key` header |
| `REQUIRE_API_KEY` | Enable static API key verification |

Logs are emitted in JSON format for easier ingestion into log platforms.

---

## 5. ▶️ Running the Webhook Locally

```bash
uvicorn main:app --reload
```

Test the health endpoint:

```bash
curl http://127.0.0.1:8000/
```

Interactive API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Expose metrics:

```bash
curl http://127.0.0.1:8000/metrics
```

Simulate an alert:

```bash
python simulate_tradingview.py
```

---

## 6. 📡 Webhook Payload Format

### 🔐 A. Secure Mode

Use headers:

| Header | Description |
|--------|-------------|
| `X-Timestamp` | Unix time in seconds |
| `X-Signature` | HMAC SHA256 using `WEBHOOK_SECRET` |

Generate signature:

```python
hmac.new(secret.encode(), json_body.encode(), hashlib.sha256).hexdigest()
```

---

### 🔁 B. Token Fallback Mode

Use this when custom headers can't be set (e.g., TradingView):

```json
{
  "token": "issued_token_here",
  "nonce": "unique_id",
  ...
}
```
Include a new random `nonce` value with each request to prevent replay attacks.

**Issuing a Token**
Generate and store a token with an optional TTL (defaults to `TOKEN_TTL`):

```bash
python manage_tokens.py issue --ttl 3600
```
The command prints the token value which should be used in TradingView alerts.

**Revoking a Token**

```bash
python manage_tokens.py revoke <token>
```
Expired tokens are automatically cleaned up during verification.

---

## 7. 🔁 TradingView Integration

- Set Webhook URL in the TradingView alert:
  `https://your-app.herokuapp.com/webhook`

- Paste the message as **one-line JSON**:

```json
{
  "token": "issued_token_here",
  "nonce": "unique_id",
  "exchange": "{{exchange}}",
  "apiKey": "your_api_key",
  "secret": "your_api_secret",
  "symbol": "{{ticker}}",
  "side": "{{strategy.order.action}}",
  "amount": "{{strategy.order.contracts}}",
  "price": "{{close}}"
}
```
Make sure each alert uses a unique `nonce` value.

**Common Variables**:

| Variable                      | Description                                      |
|------------------------------|--------------------------------------------------|
| `{{strategy.order.action}}`  | `"buy"` or `"sell"` depending on strategy signal |
| `{{strategy.order.id}}`      | Custom order ID from Pine script                 |
| `{{strategy.position_size}}` | Size of the current position                     |
| `{{strategy.order.contracts}}`| Number of contracts/units in the order           |
| `{{close}}`                  | Close price of the current candle                |
| `{{ticker}}`                 | Trading pair (e.g., `BTCUSDT`)                   |
| `{{exchange}}`               | Exchange name (e.g., `BINANCE`)                  |
| `{{time}}`                   | UNIX timestamp of the candle                     |

---

## 8. 🧪 Testing

Run all tests:

```bash
pytest tests/
```

Tests cover:
- Token/HMAC auth
- Timestamp checks
- Order routing
- Async safety

Run a full local simulation:

```bash
python simulate_tradingview.py
```

---

## 9. ☁️ Deployment (Heroku)

Detailed deployment guides, including Docker Compose and VPS instructions,
are available in [deployment.md](deployment.md).


### CLI-Based Deployment:

```bash
heroku create ccxt-fastapi-webhook
heroku config:set WEBHOOK_SECRET=...
heroku addons:create heroku-redis:hobby-dev
heroku config:set CELERY_BROKER_URL=$(heroku config:get REDIS_URL)
heroku config:set CELERY_RESULT_BACKEND=$(heroku config:get REDIS_URL)
heroku config:set QUEUE_ORDERS=true
git push heroku main
heroku ps:scale worker=1
```

### GitHub-Based Auto Deploy:

1. Go to **Heroku Dashboard → Deploy tab**
2. Choose GitHub → Connect your repo
3. Enable Auto Deploy on `main`
4. Set secrets under **Config Vars**:

```bash
heroku config:set WEBHOOK_SECRET=your_shared_secret
heroku config:set DEFAULT_EXCHANGE=binance
heroku config:set DEFAULT_API_KEY=your_api_key
heroku config:set DEFAULT_API_SECRET=your_api_secret
heroku config:set LOG_LEVEL=INFO
heroku addons:create heroku-redis:hobby-dev
heroku config:set CELERY_BROKER_URL=$(heroku config:get REDIS_URL)
heroku config:set CELERY_RESULT_BACKEND=$(heroku config:get REDIS_URL)
heroku config:set QUEUE_ORDERS=true
heroku ps:scale web=1 worker=1
```

---

## 10. 🔒 HTTPS & Reverse Proxy

For production you should serve the webhook over HTTPS. You can either run
Uvicorn behind a reverse proxy like **Nginx** or enable TLS directly.

### Nginx Example

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /path/fullchain.pem;
    ssl_certificate_key /path/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Run Uvicorn bound to localhost:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Direct TLS with Uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 443 \
  --ssl-keyfile /path/privkey.pem --ssl-certfile /path/fullchain.pem
```

Set `REQUIRE_HTTPS=true` in `.env` to reject plain HTTP requests.

---

## 11. 📂 Project Structure

```text
ccxt-trading-webhook/
├── app/
│   ├── auth.py
│   ├── routes.py
│   ├── exchange_factory.py
│   ├── utils.py
├── config/settings.py
├── tests/test_webhook.py
├── simulate_tradingview.py
├── main.py
├── Procfile
├── requirements.txt
├── runtime.txt
├── README.md
```

---

## 12. 📬 Postman Collection

A ready-made Postman collection lives at [`docs/postman_collection.json`](docs/postman_collection.json). Import it for quick testing:

1. Open **Postman** and click **Import**.
2. Select the **File** tab and choose `docs/postman_collection.json` from this repo.
3. Run the **Send Webhook** request against your local server.

---

## 📄 License

MIT
