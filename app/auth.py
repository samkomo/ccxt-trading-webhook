import hmac
import hashlib
from datetime import datetime, timedelta
from flask import request
from config import settings

def verify_signature(request):
    """
    Verifies HMAC SHA256 signature using a shared secret.
    The signature should be in the 'X-Signature' header.
    """
    secret = settings.WEBHOOK_SECRET
    if not secret:
        raise ValueError("WEBHOOK_SECRET is not configured")

    signature = request.headers.get('X-Signature')
    if not signature:
        return False

    payload = request.get_data()
    computed_signature = hmac.new(
        key=secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, signature)


def is_recent_request(request, tolerance_minutes=5):
    """
    Prevents replay attacks by validating the 'X-Timestamp' header.
    Expects an ISO 8601 UTC timestamp (e.g. 2024-06-01T12:00:00Z).
    """
    timestamp = request.headers.get('X-Timestamp')
    if not timestamp:
        return False

    try:
        request_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        return False

    return datetime.utcnow() - request_time <= timedelta(minutes=tolerance_minutes)
