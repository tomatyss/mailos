"""Logging utilities."""

import inspect
import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Global flag to track if root logger has been configured
_root_configured = False
# Cache for module loggers
_loggers = {}


def _configure_root_logger(log_level=logging.INFO):
    """Configure root logger if not already configured."""
    global _root_configured
    if _root_configured:
        return

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

    _root_configured = True


# Configure root logger at import time
_configure_root_logger()


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
                _loggers[module_name].handlers = []

            self._logger = _loggers[module_name]
        return self._logger

    def __getattr__(self, name):
        return getattr(self.__get_logger(), name)


# Create a single instance to be imported
logger = LazyLogger()


# For backward compatibility
def setup_logger(name, log_level=logging.INFO):
    """Set up logger for a given name (deprecated)."""
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
        _loggers[name].propagate = True
        _loggers[name].handlers = []
    return _loggers[name]


# Export only what's needed
__all__ = ["logger"]
