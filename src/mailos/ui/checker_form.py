"""UI functions for creating and editing checker forms."""

from pywebio.output import close_popup, popup, put_buttons, put_markdown, use_scope
from pywebio.pin import (
    pin,
    pin_on_change,
    put_checkbox,
    put_input,
    put_select,
    put_textarea,
)

from mailos.tools import AVAILABLE_TOOLS
from mailos.utils.config_utils import load_config
from mailos.utils.logger_utils import logger
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory


def create_checker_form(checker_id=None, on_save=None):
    """Create a form for new checker or editing existing one.

    Args:
        checker_id: The ID of the checker to edit, or None for new checker
        on_save: Callback function to save the checker
    """
    config = load_config()
    checker = None

    if checker_id:
        # Find checker by ID
        for c in config["checkers"]:
            if c.get("id") == checker_id:
                checker = c
                break
        if not checker:
            logger.warning(f"No checker found with ID: {checker_id}")
            return
    else:
        checker = {}

    llm_providers = list(LLMFactory._providers.keys())

    # Log the current state
    logger.debug(f"Creating form for checker ID: {checker_id}")
    logger.debug(f"Current checker config: {checker}")

    # Pre-select current features
    current_features = []
    if checker.get("enabled", False):
        current_features.append("Enable monitoring")
    if checker.get("auto_reply", False):
        current_features.append("Auto-reply to emails")

    # Get currently enabled tools
    current_tools = checker.get("enabled_tools", [])

    def submit_form():
        # Log form data before submission
        logger.debug("Form submission - Collecting pin data:")
        logger.debug(f"checker_name: {pin.checker_name}")
        logger.debug(f"monitor_email: {pin.monitor_email}")
        logger.debug(f"imap_server: {pin.imap_server}")
        logger.debug(f"imap_port: {pin.imap_port}")
        logger.debug(f"features: {pin.features}")
        logger.debug(f"enabled_tools: {pin.enabled_tools}")

        if on_save:
            on_save(checker_id)
        close_popup()

    with popup(f"{'Edit' if checker_id else 'New'} Email Checker", size="large"):
        put_markdown(f"### {'Edit' if checker_id else 'New'} Email Checker")

        # Email configuration fields
        put_input(
            "checker_name",
            type="text",
            label="Checker Name",
            value=checker.get("name", ""),
        )

        put_input(
            "monitor_email",
            type="text",
            label="Email to monitor",
            value=checker.get("monitor_email", ""),
        )

        put_input(
            "password",
            type="password",
            label="Email password",
            value=checker.get("password", ""),
        )

        # Log current IMAP server value before creating input
        logger.debug(
            "Setting IMAP server input with value: %s",
            checker.get("imap_server", "imap.gmail.com"),
        )
        put_input(
            "imap_server",
            type="text",
            label="IMAP Server",
            value=checker.get("imap_server", "imap.gmail.com"),
        )

        put_input(
            "imap_port",
            type="number",
            label="IMAP Port",
            value=checker.get("imap_port", 993),
        )

        put_checkbox(
            "features",
            options=["Enable monitoring", "Auto-reply to emails"],
            value=current_features,
            inline=True,
        )

        # Tools selection
        put_markdown("### Available Tools")
        put_checkbox(
            "enabled_tools",
            options=[
                {"label": display_name, "value": tool_name}
                for tool_name, display_name in AVAILABLE_TOOLS
            ],
            value=current_tools,
            inline=True,
            help_text="Select tools to enable for this checker",
        )

        # LLM configuration
        put_markdown("### LLM Configuration")
        put_select(
            "llm_provider",
            options=llm_providers,
            label="LLM Provider",
            value=checker.get("llm_provider", llm_providers[0]),
        )

        def on_provider_change(provider):
            vendor_config = VENDOR_CONFIGS.get(provider)
            if not vendor_config:
                return

            with use_scope("provider_credentials", clear=True):
                # Add model selection with supported models
                put_select(
                    "model",
                    options=vendor_config.supported_models,
                    label="Model Name",
                    value=checker.get("model", vendor_config.default_model),
                )

                # Add vendor-specific configuration fields
                for field in vendor_config.fields:
                    put_input(
                        field.name,
                        type=field.type,
                        label=field.label,
                        value=checker.get(field.name, field.default or ""),
                        help_text=field.help_text,
                    )

        # Initial credentials fields
        with use_scope("provider_credentials"):
            on_provider_change(checker.get("llm_provider", llm_providers[0]))

        put_textarea(
            "system_prompt",
            label="System Prompt",
            value=checker.get("system_prompt", ""),
            rows=5,
        )

        put_buttons(
            [
                {"label": "Save", "value": "save", "color": "success"},
                {"label": "Cancel", "value": "cancel", "color": "secondary"},
            ],
            onclick=lambda val: submit_form() if val == "save" else close_popup(),
        )

        # Register provider change handler
        pin_on_change("llm_provider", onchange=on_provider_change)
