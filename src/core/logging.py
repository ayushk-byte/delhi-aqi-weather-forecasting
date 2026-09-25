"""Structured logging setup with support for standard formatting and rich console output."""

import logging
import sys


def get_logger(name: str = "delhi_aqi", level: str | None = None) -> logging.Logger:
    """Return a configured logger instance with structured output format.

    Args:
        name: Name of the logger, usually the module's __name__.
        level: Optional log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    elif not logger.level:
        logger.setLevel(logging.INFO)

    return logger
