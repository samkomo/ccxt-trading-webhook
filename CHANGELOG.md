# 📦 Changelog

All notable changes to this project will be documented in this file.

---

## [v1.0.0] - Initial Production Release

### Added
- Async FastAPI webhook with secure HMAC and token authentication
- `exchange_factory.py` for dynamic CCXT exchange instantiation
- `routes.py` to handle webhook and health check endpoints
- Full `.env`-based configuration with Pydantic v2
- TradingView-compatible payload support with token fallback
- Mocking layer for safe local testing (`mocks.py`)
- Full async test suite using `pytest-asyncio` and `httpx`
- `simulate_tradingview.py` for end-to-end simulation
- Heroku deployment config: `Procfile`, `runtime.txt`
- Complete `README.md` with setup, usage, and deployment docs