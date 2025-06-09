from fastapi import APIRouter, HTTPException, Request, status
from app.auth import verify_signature, verify_token
from app.exchange_factory import get_exchange
from typing import Optional, Literal
from pydantic import BaseModel, constr, confloat
import logging
from ccxt.base.errors import ExchangeError, NetworkError
from app.rate_limiter import limiter
from config.settings import settings

router = APIRouter()
logger = logging.getLogger("webhook_logger")


class WebhookPayload(BaseModel):
    """
    Defines the expected structure of incoming webhook payloads.

    Fields:
        exchange (str): The exchange ID (e.g., 'binance').
        apiKey (str): API key for the exchange.
        secret (str): API secret for the exchange.
        symbol (str): Trading pair symbol matching ``^[A-Z0-9]+/[A-Z0-9]+$``.
        side (Literal["buy", "sell"]): Order side.
        amount (float): Amount of asset to buy/sell (> 0).
        price (float): Limit price for the order (> 0).
        token (Optional[str]): Fallback auth token (for unsigned clients like TradingView).
    """
    exchange: str
    apiKey: str
    secret: str
    symbol: constr(pattern="^[A-Z0-9]+/[A-Z0-9]+$")
    side: Literal["buy", "sell"]
    amount: confloat(gt=0)
    price: confloat(gt=0)
    token: Optional[str] = None


@router.post("/webhook")
@limiter.limit(settings.RATE_LIMIT)
async def webhook(request: Request, payload: WebhookPayload):
    if "X-Signature" in request.headers:
        if not await verify_signature(request):
            logger.warning("Invalid HMAC signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        if not verify_token(payload.token):
            logger.warning("Missing or invalid token in fallback mode")
            raise HTTPException(status_code=403, detail="Unauthorized")

    exchange = None
    try:
        exchange = await get_exchange(payload.exchange, payload.apiKey, payload.secret)
        markets = await exchange.load_markets()
        logger.debug(markets.get(payload.symbol))

        # order = await exchange.create_limit_order(
        #     symbol=payload.symbol,
        #     side=payload.side,
        #     amount=payload.amount,
        #     price=payload.price
        # )
        order = await exchange.create_market_order(
            symbol=payload.symbol,
            side=payload.side,
            amount=payload.amount
        )

        logger.info(f"Order placed: {order}")
        return {"status": "success", "order": order}

    except ExchangeError as ccxt_err:
        logger.warning(f"CCXT exchange error: {ccxt_err}")
        raise HTTPException(status_code=400, detail=f"Exchange error: {str(ccxt_err)}")

    except NetworkError as net_err:
        logger.warning(f"CCXT network error: {net_err}")
        raise HTTPException(status_code=502, detail=f"Network error: {str(net_err)}")

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))

    except Exception as e:
        logger.exception("Unhandled server error")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if exchange:
            await exchange.close()