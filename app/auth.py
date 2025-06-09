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
from fastapi import Request
from config.settings import settings
import logging
from typing import Optional, Dict

logger = logging.getLogger("webhook_logger")

# Acceptable clock drift range in seconds
MAX_TIMESTAMP_AGE = 300  # 5 minutes

# Cache of recently seen request signatures for replay protection
signature_cache: Dict[str, int] = {}

def cleanup_signature_cache() -> None:
    """Remove expired entries from the signature cache."""
    now = int(time.time())
    expired = [sig for sig, expiry in signature_cache.items() if expiry <= now]
    for sig in expired:
        del signature_cache[sig]

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

        cleanup_signature_cache()
        if signature_header in signature_cache:
            logger.warning("Signature reuse detected")
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

        # Cache the signature to prevent replay attacks
        signature_cache[signature_header] = current_time + settings.SIGNATURE_CACHE_TTL

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
    if not hmac.compare_digest(token, settings.WEBHOOK_SECRET):
        logger.warning("Invalid token in fallback mode")
        return False
    return True
