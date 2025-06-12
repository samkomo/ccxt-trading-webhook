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
        SIGNATURE_CACHE_TTL (int): Seconds to remember request signatures for
            replay protection.
        SIGNATURE_CACHE_SIZE (int): Maximum number of entries in the signature
            replay cache.
        TOKEN_TTL (int): Seconds before issued tokens expire.
        TOKEN_RATE_CACHE_SIZE (int): Maximum number of tracked tokens for rate
            limiting.
        REQUIRE_HTTPS (bool): Reject non-HTTPS requests when True.
        QUEUE_ORDERS (bool): Enqueue orders to Celery when True.
        STATIC_API_KEY (str): API key required in header when enabled.
        REQUIRE_API_KEY (bool): Enforce API key verification when True.
    """
    WEBHOOK_SECRET: str
    DEFAULT_EXCHANGE: str
    DEFAULT_API_KEY: str
    DEFAULT_API_SECRET: str
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT: str = "10/minute"
    SIGNATURE_CACHE_TTL: int = 300
    SIGNATURE_CACHE_SIZE: int = 1000
    NONCE_TTL: int = 300
    TOKEN_TTL: int = 86400
    TOKEN_RATE_CACHE_SIZE: int = 1000
    REQUIRE_HTTPS: bool = False
    QUEUE_ORDERS: bool = False
    STATIC_API_KEY: str = ""
    REQUIRE_API_KEY: bool = False
    TOKEN_DB_PATH: str = "tokens.db"
    DATABASE_URL: str = "sqlite:///identity.db"
    DOCUMENT_ENCRYPTION_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# Global settings instance
settings = Settings()
