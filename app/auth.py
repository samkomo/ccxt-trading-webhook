"""
Authentication utilities for validating webhook requests.

Supports:
- HMAC SHA256 signature verification (secure clients)
- Timestamp freshness check (replay protection)
- Fallback token verification (for systems like TradingView)
"""

import hmac
import hashlib
import time
from fastapi import Request, HTTPException, status
from config.settings import settings
from app.token_store import is_token_valid
import logging
from typing import Optional, Dict

logger = logging.getLogger("webhook_logger")

# Acceptable clock drift range in seconds
MAX_TIMESTAMP_AGE = 300  # 5 minutes

# Simple in-memory cache to track recently seen request signatures
signature_cache: Dict[str, float] = {}

async def require_api_key(request: Request) -> None:
    """Optional header-based API key authentication."""
    if not settings.REQUIRE_API_KEY:
        return
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.STATIC_API_KEY:
        logger.warning("Invalid or missing API key")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

async def verify_signature(request: Request) -> bool:
    """
    Verifies the HMAC SHA256 signature of a request body using the shared secret.

    Returns:
        bool: True if valid, False if invalid or expired.
    """
    try:
        timestamp_header = request.headers.get("X-Timestamp")
        signature_header = request.headers.get("X-Signature")

        if not timestamp_header or not signature_header:
            logger.warning("Missing signature or timestamp header")
            return False

        # Convert timestamp to int and check freshness
        timestamp = int(timestamp_header)
        current_time = int(time.time())
        if abs(current_time - timestamp) > MAX_TIMESTAMP_AGE:
            logger.warning(f"Expired timestamp: {timestamp_header}")
            return False

        # Generate expected signature from raw request body
        body = await request.body()
        expected_signature = hmac.new(
            key=settings.WEBHOOK_SECRET.encode(),
            msg=body,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature_header):
            logger.warning("Signature mismatch")
            return False
        # Clean out expired cache entries
        now = int(time.time())
        expired = [sig for sig, exp in signature_cache.items() if exp <= now]
        for sig in expired:
            signature_cache.pop(sig, None)

        # Reject if we've already seen this signature recently
        if signature_header in signature_cache:
            logger.warning("Replay attack detected: signature reuse")
            return False

        # Store signature with future expiry for replay protection
        signature_cache[signature_header] = now + settings.SIGNATURE_CACHE_TTL

        return True
    except ValueError:
        logger.warning("Invalid timestamp format")
        return False
    except Exception as e:
        logger.exception("Unexpected error during signature verification")
        return False

def verify_token(token: Optional[str]) -> bool:
    """
    Verifies a simple token against the shared secret (used by fallback systems).

    Args:
        token (Optional[str]): Token provided in JSON body.

    Returns:
        bool: True if valid, else False.
    """
    if token is None:
        logger.warning("Missing token in fallback mode")
        return False

    if not is_token_valid(token):
        logger.warning("Invalid or expired token in fallback mode")
        return False
    return True
