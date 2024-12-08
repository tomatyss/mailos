"""Logging utilities."""

import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")


def setup_logger(name):
    """Set up logger for a given name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create handlers
    file_handler = RotatingFileHandler(
        f"logs/{name}.log", maxBytes=1024 * 1024, backupCount=5  # 1MB
    )
    console_handler = logging.StreamHandler()

    # Create formatters and add it to handlers
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    console_handler.setFormatter(file_format)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
