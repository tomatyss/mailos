"""Logging utilities."""

import inspect
import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Cache for module loggers
_loggers = {}
# Cache for handlers
_handlers = []


def set_log_level(level):
    """Set the log level for all loggers and handlers.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    # Update root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Update all cached loggers
    for logger in _loggers.values():
        logger.setLevel(level)

    # Update all handlers
    for handler in _handlers:
        handler.setLevel(level)


def _configure_root_logger(log_level=logging.INFO):
    """Configure root logger with handlers."""
    root_logger = logging.getLogger()

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Clear cached handlers
    _handlers.clear()

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

    # Cache handlers for later level updates
    _handlers.extend([file_handler, console_handler])


# Configure root logger at import time with INFO level
_configure_root_logger(logging.INFO)


def parse_log_level(level_str: str) -> int:
    """Parse string log level to logging constant.

    Args:
        level_str: String representation of log level

    Returns:
        Logging level constant

    Raises:
        ValueError: If level string is invalid
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    level_str = level_str.lower()
    if level_str not in level_map:
        raise ValueError(
            f"Invalid log level: {level_str}. "
            f"Valid levels are: {', '.join(level_map.keys())}"
        )

    return level_map[level_str]


class LazyLogger:
    """A proxy that creates the logger only when needed."""

    def __init__(self):
        self._logger = None

    def __get_logger(self):
        if self._logger is None:
            # Get the caller's module name
            frame = inspect.currentframe()
            while frame:
                if frame.f_globals["__name__"] != __name__:
                    module_name = frame.f_globals["__name__"]
                    break
                frame = frame.f_back

            # Create and cache logger
            if module_name not in _loggers:
                _loggers[module_name] = logging.getLogger(module_name)
                _loggers[module_name].propagate = True
                # Don't add handlers to module loggers,
                # they'll use root logger's handlers
                _loggers[module_name].handlers = []

            self._logger = _loggers[module_name]
        return self._logger

    def __getattr__(self, name):
        return getattr(self.__get_logger(), name)


# Create a single instance to be imported
logger = LazyLogger()


def setup_logger(name, log_level=None):
    """Set up logger for a given name.

    Args:
        name: Logger name
        log_level: Optional log level (if not provided, uses root logger's level)

    Returns:
        Logger instance
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
        _loggers[name].propagate = True
        # Don't add handlers to module loggers, they'll use root logger's handlers
        _loggers[name].handlers = []

        if log_level is not None:
            _loggers[name].setLevel(log_level)

    return _loggers[name]


# Export public interface
__all__ = ["logger", "setup_logger", "set_log_level", "parse_log_level"]
