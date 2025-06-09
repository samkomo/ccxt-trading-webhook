"""
App configuration loaded from .env using Pydantic v2 settings model.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Settings loaded from environment variables or .env file.

    Fields:
        WEBHOOK_SECRET (str): Shared secret for HMAC or token validation.
        DEFAULT_EXCHANGE (str): Default exchange name (e.g., binance).
        DEFAULT_API_KEY (str): Fallback API key if not provided in payload.
        DEFAULT_API_SECRET (str): Fallback API secret.
        LOG_LEVEL (str): Logging verbosity (DEBUG, INFO, etc.).
        RATE_LIMIT (str): Requests allowed per time window (e.g., "10/minute").
        SIGNATURE_CACHE_TTL (int): Replay cache TTL in seconds.
        SIGNATURE_CACHE_BACKEND (str): "memory" or "redis" backend.
        REDIS_URL (str): Redis connection URL when using redis backend.
    """
    WEBHOOK_SECRET: str
    DEFAULT_EXCHANGE: str
    DEFAULT_API_KEY: str
    DEFAULT_API_SECRET: str
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT: str = "10/minute"
    SIGNATURE_CACHE_TTL: int = 300
    SIGNATURE_CACHE_BACKEND: str = "memory"  # "memory" or "redis"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# Global settings instance
settings = Settings()
