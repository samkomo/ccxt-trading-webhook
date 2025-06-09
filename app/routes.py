"""HTTP route handlers exposing the trading webhook endpoint."""

from fastapi import APIRouter, HTTPException, Request, status, Depends
from app.auth import verify_signature, verify_token, require_api_key
from app.exchange_factory import get_exchange, release_exchange
from app.tasks import place_order_task
from typing import Optional, Literal
from pydantic import BaseModel, constr, confloat
import logging
from ccxt.base.errors import ExchangeError, NetworkError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.rate_limiter import limiter
from config.settings import settings

router = APIRouter()
logger = logging.getLogger("webhook_logger")


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type((NetworkError, ExchangeError)),
)
async def place_market_order(exchange, symbol: str, side: str, amount: float):
    """Create a market order on the given exchange.

    Parameters
    ----------
    exchange: ccxt.Exchange
        The exchange client on which to execute the trade.
    symbol: str
        Trading pair symbol, e.g. ``"BTC/USDT"``.
    side: str
        ``"buy"`` or ``"sell"``.
    amount: float
        Asset quantity to trade.

    Returns
    -------
    dict
        The order information returned by CCXT.
    """

    return await exchange.create_market_order(
        symbol=symbol,
        side=side,
        amount=amount,
    )


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
        nonce (Optional[str]): One-time nonce for replay protection when using tokens.
    """
    exchange: str
    apiKey: str
    secret: str
    symbol: constr(pattern="^[A-Z0-9]+/[A-Z0-9]+$")
    side: Literal["buy", "sell"]
    amount: confloat(gt=0)
    price: confloat(gt=0)
    token: Optional[str] = None
    nonce: Optional[str] = None


@router.post("/webhook")
@limiter.limit(settings.RATE_LIMIT)
async def webhook(request: Request, payload: WebhookPayload, _: None = Depends(require_api_key)):
    """Process an authenticated webhook request.

    Parameters
    ----------
    request: Request
        Incoming FastAPI request used for header inspection.
    payload: WebhookPayload
        Parsed payload containing order details and credentials.
    _ : None
        API key dependency placeholder.

    Returns
    -------
    dict
        JSON response describing the execution status.
    """
    if settings.REQUIRE_HTTPS and request.url.scheme != "https":
        logger.warning("Plain HTTP request rejected")
        raise HTTPException(status_code=400, detail="HTTPS required")
    if "X-Signature" in request.headers:
        if not await verify_signature(request):
            logger.warning("Invalid HMAC signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        if not verify_token(payload.token, payload.nonce):
            logger.warning("Missing or invalid token in fallback mode")
            raise HTTPException(status_code=403, detail="Unauthorized")

    if settings.QUEUE_ORDERS:
        place_order_task.delay(payload.model_dump())
        logger.info("Order enqueued for async execution")
        return {"status": "queued"}

    exchange = None
    try:
        exchange = await get_exchange(payload.exchange, payload.apiKey, payload.secret)
        markets = await exchange.load_markets()
        logger.debug(markets.get(payload.symbol))

        order = await exchange.create_market_order(
            symbol=payload.symbol,
            side=payload.side,
            amount=payload.amount,
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

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.exception("Unhandled server error")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if exchange:
            await release_exchange(exchange)
