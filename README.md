# 🚀 CCXT Trading Webhook

A secure, scalable Flask-based webhook server to place crypto orders on multiple exchanges using the CCXT library.

## 🔧 Features

- ✅ Supports dynamic exchanges (e.g., Binance, Kraken)
- ✅ Authenticated using HMAC-SHA256 signatures
- ✅ Timestamp verification to prevent replay attacks
- ✅ Logs all activity with configurable log level
- ✅ Designed for deployment on Heroku with Gunicorn

---

## 📦 Installation

```bash
git clone https://github.com/your-username/ccxt-trading-webhook.git
cd ccxt-trading-webhook
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
