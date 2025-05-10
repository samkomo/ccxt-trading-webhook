"""
Factory for creating CCXT async exchange instances with error handling.
"""

import ccxt.async_support as ccxt
from config.settings import settings
from fastapi import HTTPException, status
from typing import Optional

async def get_exchange(
    exchange_id: str,
    api_key: Optional[str] = None,
    secret: Optional[str] = None
):
    """
    Instantiate an async CCXT exchange with dynamic credentials.

    Args:
        exchange_id (str): e.g. 'binance'
        api_key (Optional[str]): API key to use (or default)
        secret (Optional[str]): Secret to use (or default)

    Raises:
        HTTPException: If exchange doesn't exist or credentials are missing.

    Returns:
        ccxt.Exchange: Configured async CCXT exchange client
    """
    exchange_id = exchange_id.lower()  # 🛠 Normalize input

    try:
        exchange_class = getattr(ccxt, exchange_id)
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exchange '{exchange_id}' is not supported by CCXT."
        )

    api_key = api_key or settings.DEFAULT_API_KEY
    secret = secret or settings.DEFAULT_API_SECRET

    if not api_key or not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API credentials for exchange '{exchange_id}'."
        )

    try:
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
        })
        return exchange
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize exchange '{exchange_id}': {str(e)}"
        )
