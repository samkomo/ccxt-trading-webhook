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

## Development
Install dependencies and run the tests:
```bash
pip install -r requirements.txt
pytest
```

## License
MIT
