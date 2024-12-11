"""
MailOS Web Application Module.

This module provides a web interface for managing email monitoring configurations
using PyWebIO.
"""

import logging
import uuid
from typing import Optional

from pywebio import start_server
from pywebio.output import clear, put_button, put_markdown, toast, use_scope
from pywebio.pin import pin

from mailos.check_emails import init_scheduler
from mailos.ui.checker_form import create_checker_form
from mailos.ui.display import display_checkers, refresh_display
from mailos.utils.config_utils import load_config, save_config
from mailos.utils.logger_utils import setup_logger
from mailos.vendors.config import VENDOR_CONFIGS

logger = setup_logger(__name__)

scheduler = None


def save_checker(identifier: Optional[str] = None) -> None:
    """Save or update an email checker configuration."""
    try:
        config = load_config()
        logger.info(f"Updating checker with identifier: {identifier}")

        # Get enabled tools (will be empty list if none checked)
        enabled_tools = getattr(pin, "enabled_tools", []) or []
        logger.debug(f"Enabled tools from form: {enabled_tools}")

        if identifier:
            # Find and update existing checker
            for checker in config["checkers"]:
                if checker.get("id") == identifier:
                    # Update basic fields
                    checker.update(
                        {
                            "name": pin.checker_name,
                            "monitor_email": pin.monitor_email,
                            "password": pin.password,
                            "imap_server": pin.imap_server,
                            "imap_port": pin.imap_port,
                            "llm_provider": pin.llm_provider,
                            "model": pin.model,
                            "system_prompt": pin.system_prompt,
                            "enabled_tools": enabled_tools,
                            "enabled": "Enable monitoring" in pin.features,
                            "auto_reply": "Auto-reply to emails" in pin.features,
                        }
                    )

                    # Update provider-specific credentials
                    vendor_config = VENDOR_CONFIGS.get(pin.llm_provider)
                    if vendor_config:
                        for field in vendor_config.fields:
                            if hasattr(pin, field.name):
                                field_value = getattr(pin, field.name)
                                if field_value or field.required:
                                    checker[field.name] = field_value

                    logger.info(f"Updated checker with ID: {identifier}")
                    logger.debug(f"Updated tools: {enabled_tools}")
                    break
            else:
                logger.warning(f"No checker found with ID: {identifier}")
                return

            # Save all changes at once
            save_config(config)
        else:
            # Create new checker
            new_checker = {
                "id": str(uuid.uuid4()),
                "name": pin.checker_name,
                "monitor_email": pin.monitor_email,
                "password": pin.password,
                "imap_server": pin.imap_server,
                "imap_port": pin.imap_port,
                "llm_provider": pin.llm_provider,
                "model": pin.model,
                "system_prompt": pin.system_prompt,
                "enabled": "Enable monitoring" in pin.features,
                "auto_reply": "Auto-reply to emails" in pin.features,
                "enabled_tools": enabled_tools,
                "last_run": "Never",
            }

            # Add provider-specific credentials
            vendor_config = VENDOR_CONFIGS.get(pin.llm_provider)
            if vendor_config:
                for field in vendor_config.fields:
                    if hasattr(pin, field.name):
                        field_value = getattr(pin, field.name)
                        if field_value or field.required:
                            new_checker[field.name] = field_value

            config["checkers"].append(new_checker)
            save_config(config)
            logger.info(f"Added new checker with ID: {new_checker['id']}")
            logger.debug(f"Initial tools: {enabled_tools}")

        clear("edit_checker_form" if identifier else "new_checker_form")
        refresh_display()
        toast(f"Checker {'updated' if identifier else 'added'} successfully")

        if not identifier:  # Run new checker immediately
            from mailos.check_emails import main

            main()
            toast("Initial check completed")

    except Exception as e:
        logger.error(f"Failed to save configuration: {str(e)}")
        toast(f"Failed to save configuration: {str(e)}", color="error")


def check_email_app():
    """Run the main web application."""
    global scheduler
    if not scheduler:
        logger = logging.getLogger("web_app")
        logger.info("Initializing scheduler...")
        scheduler = init_scheduler()

    put_markdown("# MailOS")
    put_markdown("Configure multiple email accounts to monitor")

    config = load_config()

    # Ensure all existing checkers have IDs
    modified = False
    for checker in config.get("checkers", []):
        if not checker.get("id"):
            checker["id"] = str(uuid.uuid4())
            modified = True
    if modified:
        save_config(config)
        logger.info("Added IDs to existing checkers")

    with use_scope("checkers"):
        display_checkers(config, save_checker)

    put_button(
        "Add New Checker", onclick=lambda: create_checker_form(on_save=save_checker)
    )


def cli():
    """CLI entry point for the application."""
    import click

    @click.command()
    @click.option(
        "--log-level",
        type=click.Choice(
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
        ),
        default="INFO",
        help="Set the logging level",
    )
    def run(log_level):
        log_level = getattr(logging, log_level.upper())
        logger = setup_logger("web_app", log_level)
        logger.debug("Starting application with log level: %s", log_level)
        init_scheduler()
        start_server(check_email_app, port=8080, debug=True)

    run()


if __name__ == "__main__":
    cli()
