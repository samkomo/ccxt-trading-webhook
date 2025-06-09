"""Shared utility helpers for logging configuration."""

import logging
from pythonjsonlogger import jsonlogger
from config.settings import settings

def setup_logger(name: str = "webhook_logger") -> logging.Logger:
    """Configure and return a structured logger instance.

    Parameters
    ----------
    name: str, optional
        Logger name to create or retrieve. Defaults to ``"webhook_logger"``.

    Returns
    -------
    logging.Logger
        The configured logger with JSON formatting applied.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    try:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    except Exception:
        level = logging.INFO

    logger.setLevel(level)

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
