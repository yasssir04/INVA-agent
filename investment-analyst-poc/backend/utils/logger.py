"""Central logging configuration for the backend."""
from __future__ import annotations
import logging
import logging.handlers
import os
from typing import Optional

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "logs", "app.log")
LOG_PATH = os.path.abspath(LOG_PATH)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

_formatter = logging.Formatter(
    fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

_handler = logging.handlers.RotatingFileHandler(
    LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
)
_handler.setFormatter(_formatter)

_console = logging.StreamHandler()
_console.setFormatter(_formatter)


def get_logger(name: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """Get a configured logger.

    Args:
        name: Logger name.
        level: Log level name.
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name or __name__)
    if not logger.handlers:
        logger.addHandler(_handler)
        logger.addHandler(_console)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger
