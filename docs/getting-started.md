# Getting Started

## Project Overview

This project is a production-grade, asynchronous webhook server built with **FastAPI** for **executing cryptocurrency trades** via [TradingView](https://tradingview.com) alerts. It securely handles webhook requests and places live orders on supported crypto exchanges using the [`ccxt`](https://github.com/ccxt/ccxt) library (with async support).

### Use Cases
- Automated trading via TradingView strategies
- Backtest-to-execution pipeline
- Scalable webhook backend for crypto signal platforms

### Built With
- **FastAPI** – high-performance Python web framework
- **CCXT (async_support)** – unified crypto exchange trading library
- **pytest + httpx** – async-capable testing stack
- **Heroku-ready** – cloud deployment via Procfile

## Installation & Setup
```bash
git clone https://github.com/your-username/ccxt-trading-webhook.git
cd ccxt-trading-webhook

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Extras required for local documentation builds
pip install mkdocs-material mkdocs-openapi-markdown-plugin openapi-markdown
```

These additional packages are needed if you plan to run `mkdocs build` or
`mkdocs serve` locally.

## Running the Webhook Locally
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

## Testing
Run all tests:
```bash
pytest tests/
```

Run a full local simulation:
```bash
python simulate_tradingview.py
```

## Postman Collection
A ready-made Postman collection lives at [`docs/postman_collection.json`](postman_collection.json). Import it for quick testing:
1. Open **Postman** and click **Import**.
2. Select the **File** tab and choose `postman_collection.json` from this repo.
3. Run the **Send Webhook** request against your local server.

