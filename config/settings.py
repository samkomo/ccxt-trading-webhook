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
        TOKEN_TTL (int): Seconds before issued tokens expire.
        REQUIRE_HTTPS (bool): Reject non-HTTPS requests when True.
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
    TOKEN_TTL: int = 86400
    REQUIRE_HTTPS: bool = False
    STATIC_API_KEY: str = ""
    REQUIRE_API_KEY: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# Global settings instance
settings = Settings()
