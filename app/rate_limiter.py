"""Centralized rate limiter configuration for the API."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Use the client's IP address to identify unique callers
limiter = Limiter(key_func=get_remote_address)

__all__ = ["limiter"]
