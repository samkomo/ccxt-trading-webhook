# 🚀 CCXT FastAPI Async Webhook

A production-grade, asynchronous webhook for executing crypto trades using TradingView alerts and `ccxt.async_support`.

## Documentation
Full setup and usage instructions live in the [docs](https://your-username.github.io/ccxt-trading-webhook/). The documentation covers authentication, TradingView integration, API details and deployment options.

## Features
- ⚡ **Asynchronous** with FastAPI + `ccxt.async_support`
- 🔐 **Secure dual-mode authentication** (HMAC + timestamp or token fallback)
- 📡 **TradingView-compatible**
- 🧪 **Full async test suite** with `pytest-asyncio` and mocking
- ☁️ **Heroku deployment ready**
- 🚦 **Per-IP rate limiting** via `slowapi`
- 📑 **JSON structured logging** for easy ingestion
- 📊 **Prometheus metrics** available at `/metrics`

## Project Structure
The main application code lives inside the `app/` package and is organized into
domain-driven subpackages:

- `api` – FastAPI route declarations
- `identity` – authentication helpers and token utilities
- `wallet` – deposit address management
- `marketplace` – strategy catalog CRUD
- `subscription` – follower subscriptions
- `execution` – CCXT session management and order placement
- `ledger` – trade history and export helpers
- `risk` – per-user risk limits
- `dashboard` – Prometheus metrics endpoint
- `compliance` – audit logging tools

## Development
Install dependencies and run the tests:
```bash
pip install -r requirements.txt
# Extras needed for local documentation builds
pip install mkdocs-material mkdocs-openapi-markdown-plugin openapi-markdown
pytest
```

These extra packages are required if you plan to run `mkdocs build` or
`mkdocs serve` locally.

## License
MIT
