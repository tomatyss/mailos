"""Configuration utilities for loading and saving email configuration."""

import json
import logging
import os

CONFIG_FILE = "email_config.json"
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"checkers": []}


def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


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
