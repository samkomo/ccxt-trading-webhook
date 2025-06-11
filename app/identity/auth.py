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
from fastapi import Request, HTTPException, status, Depends
from config.settings import settings
from .token_store import is_token_valid, register_nonce
from datetime import datetime
from app.db import SessionLocal
from .models import ApiToken, UserRole, TokenUsageLog, hash_token
from sqlalchemy.exc import OperationalError
import logging
from typing import Optional, Dict

logger = logging.getLogger("webhook_logger")

# Acceptable clock drift range in seconds
MAX_TIMESTAMP_AGE = 300  # 5 minutes

# Simple in-memory cache to track recently seen request signatures
signature_cache: Dict[str, float] = {}

# In-memory token rate tracking {token_hash: [timestamps]}
token_rate_cache: Dict[str, list[float]] = {}


def _parse_rate(rate: str) -> tuple[int, float]:
    count, per = rate.split("/")
    count = int(count)
    seconds = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
    }.get(per, 60)
    return count, seconds


TOKEN_RATE_LIMIT = _parse_rate(settings.RATE_LIMIT)


def _enforce_token_limit(token_hash: str) -> bool:
    limit, period = TOKEN_RATE_LIMIT
    now = time.time()
    usage = token_rate_cache.get(token_hash, [])
    usage = [t for t in usage if now - t < period]
    if len(usage) >= limit:
        return False
    usage.append(now)
    token_rate_cache[token_hash] = usage
    return True


async def require_api_key(request: Request) -> None:
    """Optional header-based API key authentication."""
    if not settings.REQUIRE_API_KEY:
        return
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.STATIC_API_KEY:
        logger.warning("Invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )


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
            key=settings.WEBHOOK_SECRET.encode(), msg=body, digestmod=hashlib.sha256
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


def verify_token(
    token: Optional[str], nonce: Optional[str], request: Optional[Request] = None
) -> bool:
    """
    Verifies a simple token against the shared secret (used by fallback systems).

    Args:
        token (Optional[str]): Token provided in JSON body.
        nonce (Optional[str]): One-time nonce.

    Returns:
        bool: True if valid, else False.
    """
    if token is None or nonce is None:
        logger.warning("Missing token or nonce in fallback mode")
        return False

    if is_token_valid(token):
        if not register_nonce(nonce):
            logger.warning("Replay attack detected: nonce reuse")
            return False
        return True

    token_hash = hash_token(token)
    try:
        with SessionLocal() as db:
            api_token: ApiToken | None = (
                db.query(ApiToken)
                .filter(ApiToken.token_hash == token_hash, ApiToken.is_revoked == False)
                .first()
            )
            if not api_token:
                logger.warning("Invalid or expired token in fallback mode")
                return False
            if api_token.expires_at and api_token.expires_at < datetime.utcnow():
                logger.warning("Expired API token")
                return False
            if not _enforce_token_limit(token_hash):
                logger.warning("Token rate limit exceeded")
                return False
            if not register_nonce(nonce):
                logger.warning("Replay attack detected: nonce reuse")
                return False
            if api_token.role_restrictions:
                roles = api_token.role_restrictions.get("roles", [])
                if roles:
                    count = (
                        db.query(UserRole)
                        .filter(
                            UserRole.user_id == api_token.user_id,
                            UserRole.role_id.in_(roles),
                            UserRole.is_active == True,
                        )
                        .count()
                    )
                    if count == 0:
                        logger.warning("Token role restriction failed")
                        return False
            api_token.last_used_at = datetime.utcnow()
            log = TokenUsageLog(
                token_id=api_token.id,
                user_id=api_token.user_id,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("User-Agent") if request else None,
            )
            db.add(log)
            db.commit()
            return True
    except OperationalError:
        logger.error("Token database not initialized")
        return False


# JWT utilities for login sessions and email verification
import jwt
from datetime import datetime, timedelta
from app.db import SessionLocal
from .models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_ALGORITHM = "HS256"
http_bearer = HTTPBearer(auto_error=False)


def create_jwt(subject: str, expires_in: int = 3600) -> str:
    payload = {"sub": subject, "exp": datetime.utcnow() + timedelta(seconds=expires_in)}
    return jwt.encode(payload, settings.WEBHOOK_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.WEBHOOK_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )
    user_id = decode_jwt(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        return user
