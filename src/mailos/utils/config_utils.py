"""Configuration utilities for loading and saving email configuration."""

import json
import logging
import os
from typing import Any, Dict

CONFIG_FILE = "email_config.json"
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


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file.

    Returns:
        Dictionary containing configuration settings
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Ensure attachment settings exist
            if "attachment_settings" not in config:
                config["attachment_settings"] = DEFAULT_CONFIG["attachment_settings"]
            return config
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to JSON file.

    Args:
        config: Configuration dictionary to save
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


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
        config = load_config()
        for checker in config["checkers"]:
            if checker.get("id") == checker_id:
                checker[field] = value
                save_config(config)
                logger.debug(f"Updated {field} for checker {checker_id}")
                return True
        logger.warning(f"No checker found with ID: {checker_id}")
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
        config = load_config()
        current_settings = config.get("attachment_settings", {})
        current_settings.update(settings)
        config["attachment_settings"] = current_settings
        save_config(config)
        logger.debug("Updated attachment settings")
        return True
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
