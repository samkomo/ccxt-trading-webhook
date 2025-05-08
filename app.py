
from flask import Flask, request, jsonify
import ccxt
import os

app = Flask(__name__)

# Load API keys from environment variables
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    try:
        symbol = data['symbol']
        side = data['side']
        amount = float(data['amount'])
        price = float(data['price'])

        order = exchange.create_limit_order(symbol, side, amount, price)
        return jsonify({'status': 'success', 'order': order})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run()
