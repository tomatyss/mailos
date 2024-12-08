"""
MailOS Web Application Module.

This module provides a web interface for managing email monitoring configurations
using PyWebIO. It allows users to create, update, and manage email checkers that
use various LLM providers (OpenAI, Anthropic, Bedrock) to process emails.

The application supports:
- Creating and editing email checker configurations
- Managing monitoring settings for email accounts
- Configuring LLM providers and their credentials
- Real-time display of active checkers
- Scheduling and managing email checking jobs

Example:
    To run the web application:
    ```python
    from mailos.app import start_app
    start_app(port=8080)
    ```
"""

from typing import Optional

from pywebio import start_server
from pywebio.output import clear, put_button, put_markdown, toast, use_scope
from pywebio.pin import pin

from mailos.check_emails import init_scheduler
from mailos.ui.checker_form import create_checker_form
from mailos.ui.display import display_checkers, refresh_display
from mailos.utils.config_utils import load_config, save_config
from mailos.utils.logger_utils import setup_logger

scheduler = None
logger = setup_logger("web_app")


def save_checker(identifier: Optional[str] = None) -> None:
    """Save or update an email checker configuration.

    Args:
        identifier (str, optional): Unique identifier (email or name) of existing
            checker to update. If None, creates new checker.
    """
    try:
        config = load_config()

        # Collect form data
        checker_config = {
            "name": pin.checker_name,
            "monitor_email": pin.monitor_email,
            "password": pin.password,
            "imap_server": pin.imap_server,
            "imap_port": pin.imap_port,
            "llm_provider": pin.llm_provider,
            "model": pin.model,
            "system_prompt": pin.system_prompt,
        }

        # Add provider-specific credentials
        if pin.llm_provider == "bedrock-anthropic":
            checker_config.update(
                {
                    "aws_access_key": pin.aws_access_key,
                    "aws_secret_key": pin.aws_secret_key,
                    "aws_region": pin.aws_region,
                }
            )
            if hasattr(pin, "aws_session_token") and pin.aws_session_token:
                checker_config["aws_session_token"] = pin.aws_session_token
        else:
            checker_config["api_key"] = pin.api_key

        # Transform configuration
        checker_config["enabled"] = "Enable monitoring" in pin.features
        checker_config["auto_reply"] = "Auto-reply to emails" in pin.features

        if identifier:
            # Find and update existing checker
            for checker in config["checkers"]:
                if (
                    checker.get("monitor_email") == identifier
                    or checker.get("name") == identifier
                ):
                    checker_config["last_run"] = checker.get("last_run", "Never")
                    config["checkers"].remove(checker)
                    config["checkers"].append(checker_config)
                    break
        else:
            checker_config["last_run"] = "Never"
            config["checkers"].append(checker_config)

        save_config(config)
        clear("edit_checker_form" if identifier else "new_checker_form")
        refresh_display()
        toast(f"Checker {'updated' if identifier else 'added'} successfully")

        if not identifier:  # Run new checker immediately
            from mailos.check_emails import main

            main()
            toast("Initial check completed")

    except Exception as e:
        toast(f"Failed to save configuration: {str(e)}", color="error")


def check_email_app():
    """Run the main web application."""
    global scheduler
    if not scheduler:
        logger.info("Initializing scheduler...")
        scheduler = init_scheduler()

    put_markdown("# MailOS")
    put_markdown("Configure multiple email accounts to monitor")

    config = load_config()

    with use_scope("checkers"):
        display_checkers(config, save_checker)

    put_button(
        "Add New Checker", onclick=lambda: create_checker_form(on_save=save_checker)
    )


def cli():
    """CLI entry point for the application."""
    init_scheduler()
    start_server(check_email_app, port=8080, debug=True)


if __name__ == "__main__":
    cli()
