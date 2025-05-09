import ccxt
from config import settings

def get_exchange(exchange_id=None, api_key=None, secret=None):
    """
    Dynamically creates and returns a CCXT exchange instance.

    Args:
        exchange_id (str): Name of the exchange (e.g., 'binance')
        api_key (str): API key for the exchange
        secret (str): API secret for the exchange

    Returns:
        exchange (ccxt.Exchange): Authenticated exchange instance
    """
    # Use defaults if no arguments provided
    exchange_id = exchange_id or settings.DEFAULT_EXCHANGE
    api_key = api_key or settings.DEFAULT_API_KEY
    secret = secret or settings.DEFAULT_API_SECRET

    if not hasattr(ccxt, exchange_id):
        raise ValueError(f"Exchange '{exchange_id}' is not supported by CCXT.")

    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({
        'apiKey': api_key,
        'secret': secret,
    })
