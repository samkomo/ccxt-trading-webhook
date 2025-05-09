
# 🚀 CCXT Trading Webhook

A secure, scalable Flask-based webhook server for placing crypto orders on multiple exchanges using the CCXT library.

---

## 🔧 Features

- 🔐 HMAC SHA256 request authentication
- ⏱ Timestamp validation to prevent replay attacks
- 🔁 Dynamic exchange support via CCXT (e.g., Binance, Kraken)
- 🧱 Modular Flask app structure
- 🛠 Production-ready via Gunicorn and Heroku
- 🧪 Built-in unit tests
- 📋 Configurable via `.env`

---

## 📦 Installation & Setup

```bash
# Clone the repo
git clone https://github.com/your-username/ccxt-trading-webhook.git
cd ccxt-trading-webhook

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file in the project root:

```env
WEBHOOK_SECRET=your_shared_secret
DEFAULT_EXCHANGE=binance
DEFAULT_API_KEY=your_api_key
DEFAULT_API_SECRET=your_api_secret
LOG_LEVEL=INFO
```

---

## 🧪 Run Tests

```bash
python -m unittest tests/test_webhook.py
```

---

## 🧪 Run Locally

```bash
python run.py
```

Access the health check: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## 📡 Example Webhook Request

Send a signed POST request to `/webhook` with the following:

**Headers:**

- `Content-Type: application/json`
- `X-Signature`: HMAC SHA256 of the raw JSON body, using `WEBHOOK_SECRET`
- `X-Timestamp`: ISO 8601 UTC timestamp (e.g., `2025-05-09T12:00:00Z`)

**JSON Body Example:**

```json
{
  "exchange": "binance",
  "apiKey": "your_key",
  "secret": "your_secret",
  "symbol": "BTC/USDT",
  "side": "buy",
  "amount": 0.01,
  "price": 30000
}
```

**Curl Example:**

```bash
curl -X POST http://127.0.0.1:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: your_hmac_signature" \
  -H "X-Timestamp: 2025-05-09T12:00:00Z" \
  -d '{"exchange":"binance","apiKey":"...","secret":"...","symbol":"BTC/USDT","side":"buy","amount":0.01,"price":30000}'
```

---

## 🚀 Deploy to Heroku (GitHub Integration)

```bash
# Initialize Git
git init
git remote add origin https://github.com/your-username/ccxt-trading-webhook.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

Then:

1. Go to [Heroku](https://dashboard.heroku.com/)
2. Create a new app
3. Connect GitHub repo under "Deploy"
4. Set config variables from `.env`
5. Click "Deploy Branch"

---

## 🔥 Run with Gunicorn

```bash
gunicorn run:app
```

---

## 📁 Project Structure

```
ccxt-trading-webhook/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── auth.py
│   ├── utils.py
│   └── exchange_factory.py
├── config/
│   └── settings.py
├── tests/
│   └── test_webhook.py
├── .env
├── .gitignore
├── Procfile
├── README.md
├── requirements.txt
├── run.py
```

---

## 📄 License

MIT
