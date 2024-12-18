"""Configuration utilities for loading and saving email configuration."""

import fcntl
import json
import logging
import os
from typing import Any, Dict

DEFAULT_CONFIG_FILE = "email_config.json"
DEFAULT_CONFIG = {
    "checkers": [],
    "attachment_settings": {
        "base_storage_path": "attachments",
        "max_storage_gb": 10.0,
        "allowed_extensions": ["*"],  # * means all extensions allowed
        "max_file_size_mb": 25,  # Maximum size per file in MB
    },
}
# TODO: add support for s3 and google drive

logger = logging.getLogger(__name__)

# Global variable to store the current config file path
_config_file = DEFAULT_CONFIG_FILE


def set_config_file(path: str) -> None:
    """Set the path for the configuration file.

    Args:
        path: Path to the configuration file
    """
    global _config_file
    _config_file = path
    logger.info(f"Set configuration file path to: {path}")


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file.

    Returns:
        Dictionary containing configuration settings
    """
    try:
        logger.debug(f"Loading configuration from: {_config_file}")
        if os.path.exists(_config_file):
            with open(_config_file, "r") as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    config = json.load(f)
                    # Ensure attachment settings exist
                    if "attachment_settings" not in config:
                        config["attachment_settings"] = DEFAULT_CONFIG[
                            "attachment_settings"
                        ]
                    logger.debug("Configuration loaded successfully")
                    return config
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        logger.info(f"No configuration file found at {_config_file}, using defaults")
        return DEFAULT_CONFIG.copy()
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {_config_file}: {e}")
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to JSON file.

    Args:
        config: Configuration dictionary to save

    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        logger.debug(f"Saving configuration to: {_config_file}")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(_config_file)), exist_ok=True)

        # Verify config structure
        if not isinstance(config, dict):
            logger.error("Invalid configuration format: must be a dictionary")
            return False

        if "checkers" not in config:
            logger.error("Invalid configuration: missing 'checkers' key")
            return False

        # Save with atomic write pattern and file locking
        temp_file = f"{_config_file}.tmp"
        with open(temp_file, "w") as f:
            # Acquire exclusive lock for writing
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(config, f, indent=4)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

                # Atomic rename
                os.replace(temp_file, _config_file)

                logger.debug("Configuration saved successfully")
                return True
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                # Clean up temp file if it still exists
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

    except (TypeError, ValueError) as e:
        logger.error(f"Error encoding configuration to JSON: {e}")
        return False
    except OSError as e:
        logger.error(f"Error writing configuration file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving configuration: {e}")
        return False

    # Clean up temp file in case of any errors
    try:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    except Exception as e:
        logger.warning(f"Failed to clean up temp file after error: {e}")

    return False


def update_checker_field(checker_id: str, field: str, value: any) -> bool:
    """Update a single field of a checker by its ID.

    Args:
        checker_id: The ID of the checker to update
        field: The field name to update
        value: The new value for the field

    Returns:
        bool: True if the update was successful, False otherwise
    """
    try:
        logger.debug(f"Updating field '{field}' for checker {checker_id}")
        config = load_config()

        # Find and update checker
        checker_found = False
        for checker in config["checkers"]:
            if checker.get("id") == checker_id:
                checker_found = True
                checker[field] = value
                break

        if not checker_found:
            logger.warning(f"No checker found with ID: {checker_id}")
            return False

        # Save updated config
        if save_config(config):
            logger.debug(f"Successfully updated {field} for checker {checker_id}")
            return True
        else:
            logger.error(f"Failed to save config after updating {field}")
            return False

    except Exception as e:
        logger.error(f"Error updating checker field: {e}")
        return False


def update_attachment_settings(settings: Dict[str, Any]) -> bool:
    """Update attachment-related settings.

    Args:
        settings: Dictionary containing attachment settings to update

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        logger.debug("Updating attachment settings")
        config = load_config()
        current_settings = config.get("attachment_settings", {})
        current_settings.update(settings)
        config["attachment_settings"] = current_settings

        # Save updated config
        if save_config(config):
            logger.debug("Successfully updated attachment settings")
            return True
        else:
            logger.error("Failed to save config after updating attachment settings")
            return False

    except Exception as e:
        logger.error(f"Error updating attachment settings: {e}")
        return False


def get_attachment_settings() -> Dict[str, Any]:
    """Get current attachment settings.

    Returns:
        Dictionary containing attachment settings
    """
    config = load_config()
    return config.get("attachment_settings", DEFAULT_CONFIG["attachment_settings"])
