from flask import Blueprint, request, jsonify
from app.auth import verify_signature, is_recent_request
from app.exchange_factory import get_exchange
import logging

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger('webhook_logger')

@webhook_bp.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'running', 'message': 'CCXT webhook server is live'}), 200

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    if not verify_signature(request):
        logger.warning("Invalid signature")
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 403

    if not is_recent_request(request):
        logger.warning("Stale or missing timestamp")
        return jsonify({'status': 'error', 'message': 'Invalid or expired timestamp'}), 403

    data = request.json
    try:
        # Required fields
        exchange_id = data.get('exchange')
        api_key = data.get('apiKey')
        secret = data.get('secret')
        symbol = data['symbol']
        side = data['side']
        amount = float(data['amount'])
        price = float(data['price'])

        # Instantiate exchange
        exchange = get_exchange(exchange_id, api_key, secret)
        order = exchange.create_limit_order(symbol, side, amount, price)

        logger.info(f"Order placed: {order}")
        return jsonify({'status': 'success', 'order': order})
    except Exception as e:
        logger.exception("Failed to process webhook")
        return jsonify({'status': 'error', 'message': str(e)}), 400
