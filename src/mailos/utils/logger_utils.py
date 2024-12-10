"""Logging utilities."""

import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")


def setup_logger(name, log_level=logging.INFO):
    """Set up logger for a given name.

    Args:
        name (str): Logger name
        log_level: Logging level (default: logging.INFO)
    """
    # First, remove all handlers from the root logger to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set the root logger level
    root_logger.setLevel(log_level)

    # Create handlers
    file_handler = RotatingFileHandler(
        "logs/mailos.log", maxBytes=1024 * 1024, backupCount=5  # 1MB
    )
    console_handler = logging.StreamHandler()

    # Set log levels for handlers
    file_handler.setLevel(log_level)
    console_handler.setLevel(log_level)

    # Create formatters and add it to handlers
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    console_handler.setFormatter(file_format)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Get or create logger for the specific name
    logger = logging.getLogger(name)
    # Make sure this logger propagates to root
    logger.propagate = True
    # Don't add handlers to individual loggers to avoid duplicate logs
    logger.handlers = []

    return logger
