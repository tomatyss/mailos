"""
MailOS Web Application Module.

This module provides a web interface for managing email monitoring configurations
using PyWebIO.
"""

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from pywebio import start_server
from pywebio.output import clear, put_button, put_markdown, toast, use_scope
from pywebio.pin import pin

from mailos.check_emails import init_scheduler
from mailos.check_emails import main as check_emails_main
from mailos.ui.checker_form import create_checker_form
from mailos.ui.display import display_checkers, refresh_display
from mailos.utils.auth_utils import require_auth
from mailos.utils.config_utils import load_config, save_config
from mailos.utils.logger_utils import logger, parse_log_level, set_log_level
from mailos.vendors.config import VENDOR_CONFIGS

scheduler = None


@dataclass
class CheckerConfig:
    """Email checker configuration."""

    id: str
    name: str
    monitor_email: str
    password: str
    imap_server: str
    imap_port: int
    llm_provider: str
    model: str
    system_prompt: str
    enabled_tools: List[str]
    enabled: bool
    auto_reply: bool
    last_run: str = "Never"

    @classmethod
    def from_form(cls, checker_id: Optional[str] = None) -> "CheckerConfig":
        """Create CheckerConfig from form data."""
        return cls(
            id=checker_id or str(uuid.uuid4()),
            name=pin.checker_name,
            monitor_email=pin.monitor_email,
            password=pin.password,
            imap_server=pin.imap_server,
            imap_port=pin.imap_port,
            llm_provider=pin.llm_provider,
            model=pin.model,
            system_prompt=pin.system_prompt,
            enabled_tools=getattr(pin, "enabled_tools", []) or [],
            enabled="Enable monitoring" in pin.features,
            auto_reply="Auto-reply to emails" in pin.features,
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "monitor_email": self.monitor_email,
            "password": self.password,
            "imap_server": self.imap_server,
            "imap_port": self.imap_port,
            "llm_provider": self.llm_provider,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "enabled_tools": self.enabled_tools,
            "enabled": self.enabled,
            "auto_reply": self.auto_reply,
            "last_run": self.last_run,
        }


def update_vendor_credentials(checker_dict: Dict, vendor_config) -> None:
    """Update vendor-specific credentials in checker dictionary."""
    if not vendor_config:
        return

    for field in vendor_config.fields:
        if hasattr(pin, field.name):
            field_value = getattr(pin, field.name)
            if field_value or field.required:
                checker_dict[field.name] = field_value


def save_checker(identifier: Optional[str] = None) -> None:
    """Save or update an email checker configuration."""
    try:
        config = load_config()
        logger.info(f"Updating checker with identifier: {identifier}")

        # Create checker config from form data
        checker_config = CheckerConfig.from_form(identifier)
        logger.debug(f"Enabled tools from form: {checker_config.enabled_tools}")

        if identifier:
            # Update existing checker
            for checker in config["checkers"]:
                if checker.get("id") == identifier:
                    # Convert to dictionary and update
                    checker_dict = checker_config.to_dict()
                    # Add vendor-specific credentials
                    update_vendor_credentials(
                        checker_dict, VENDOR_CONFIGS.get(checker_config.llm_provider)
                    )
                    # Preserve last_run if exists
                    if "last_run" in checker:
                        checker_dict["last_run"] = checker["last_run"]
                    # Update checker
                    checker.update(checker_dict)
                    logger.info(f"Updated checker with ID: {identifier}")
                    break
            else:
                logger.warning(f"No checker found with ID: {identifier}")
                return
        else:
            # Create new checker dictionary
            new_checker = checker_config.to_dict()
            # Add vendor-specific credentials
            update_vendor_credentials(
                new_checker, VENDOR_CONFIGS.get(checker_config.llm_provider)
            )
            # Add to config
            config["checkers"].append(new_checker)
            logger.info(f"Added new checker with ID: {new_checker['id']}")

        # Save configuration
        save_config(config)

        # Update UI
        clear("edit_checker_form" if identifier else "new_checker_form")
        refresh_display()
        toast(f"Checker {'updated' if identifier else 'added'} successfully")

        # Run initial check for new checkers
        if not identifier:
            check_emails_main()
            toast("Initial check completed")

    except Exception as e:
        logger.error(f"Failed to save configuration: {str(e)}")
        toast(f"Failed to save configuration: {str(e)}", color="error")


def ensure_checker_ids(config: Dict) -> bool:
    """Ensure all checkers have IDs."""
    modified = False
    for checker in config.get("checkers", []):
        if not checker.get("id"):
            checker["id"] = str(uuid.uuid4())
            modified = True
    return modified


@require_auth
def check_email_app():
    """Run the main web application."""
    global scheduler
    if not scheduler:
        logger.info("Initializing scheduler...")
        scheduler = init_scheduler()

    put_markdown("# MailOS")
    put_markdown("Configure multiple email accounts to monitor")

    config = load_config()

    # Ensure all checkers have IDs
    if ensure_checker_ids(config):
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
            ["debug", "info", "warning", "error", "critical"], case_sensitive=False
        ),
        default="info",
        help="Set the logging level",
    )
    def run(log_level: str):
        """Run the web application with specified log level."""
        # Use our logger_utils functions to set the log level
        level = parse_log_level(log_level)
        set_log_level(level)

        logger.debug("Starting application with log level: %s", log_level)
        init_scheduler()
        start_server(check_email_app, port=8080, debug=True)

    run()


if __name__ == "__main__":
    cli()
