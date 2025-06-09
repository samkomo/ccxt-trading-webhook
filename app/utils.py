import logging
from pythonjsonlogger import jsonlogger
from config.settings import settings

def setup_logger(name: str = "webhook_logger") -> logging.Logger:
    """
    Sets up and returns a consistent logger.
    Falls back to INFO if log level is invalid or undefined.
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
