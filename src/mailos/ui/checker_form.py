"""UI functions for creating and editing checker forms."""

from pywebio.output import (
    close_popup,
    popup,
    put_buttons,
    put_markdown,
    toast,
    use_scope,
)
from pywebio.pin import (
    pin,
    pin_on_change,
    put_checkbox,
    put_input,
    put_select,
    put_textarea,
)

from mailos.tools import AVAILABLE_TOOLS
from mailos.ui.task_form import create_task_form, display_task_list
from mailos.utils.config_utils import load_config, save_config
from mailos.utils.logger_utils import logger
from mailos.utils.task_utils import TaskManager
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory


def handle_task_action(action: str, checker_id: str, task_id: str = None):
    """Handle task-related actions."""
    config = load_config()
    checker = None
    for c in config["checkers"]:
        if c.get("id") == checker_id:
            checker = c
            break

    if not checker:
        toast("Checker not found", color="error")
        return

    if action == "add":

        def on_task_save():
            # Refresh task list
            config = load_config()
            for c in config["checkers"]:
                if c.get("id") == checker_id:
                    display_task_list(checker_id, c["name"])
                    break

        create_task_form(checker_id, checker["name"], on_save=on_task_save)
    elif action == "edit":

        def on_task_save():
            # Refresh task list
            config = load_config()
            for c in config["checkers"]:
                if c.get("id") == checker_id:
                    display_task_list(checker_id, c["name"])
                    break

        create_task_form(checker_id, checker["name"], task_id, on_save=on_task_save)
    elif action == "delete":
        if TaskManager.delete_task(checker_id, task_id):
            toast("Task deleted successfully")
            # Refresh task list
            config = load_config()
            for c in config["checkers"]:
                if c.get("id") == checker_id:
                    display_task_list(checker_id, c["name"])
                    break
        else:
            toast("Failed to delete task", color="error")


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
    if checker.get("enable_tasks", False):
        current_features.append("Enable scheduled tasks")

    # Get currently enabled tools
    current_tools = checker.get("enabled_tools", [])

    def submit_form():
        # Create checker config from form data
        checker_config = {
            "name": pin.checker_name,
            "monitor_email": pin.monitor_email,
            "password": pin.password,
            "imap_server": pin.imap_server,
            "imap_port": pin.imap_port,
            "llm_provider": pin.llm_provider,
            "model": pin.model,
            "system_prompt": pin.system_prompt,
            "enabled_tools": getattr(pin, "enabled_tools", []) or [],
            "enabled": "Enable monitoring" in pin.features,
            "auto_reply": "Auto-reply to emails" in pin.features,
            "enable_tasks": "Enable scheduled tasks" in pin.features,
        }

        if checker_id:
            # Update existing checker
            for c in config["checkers"]:
                if c.get("id") == checker_id:
                    # Preserve existing tasks and last_run
                    checker_config["tasks"] = c.get("tasks", [])
                    if "last_run" in c:
                        checker_config["last_run"] = c["last_run"]
                    checker_config["id"] = checker_id
                    c.update(checker_config)
                    break
        else:
            # Add new checker
            from uuid import uuid4

            checker_config["id"] = str(uuid4())
            checker_config["tasks"] = []
            config["checkers"].append(checker_config)

        save_config(config)
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
            options=[
                "Enable monitoring",
                "Auto-reply to emails",
                "Enable scheduled tasks",
            ],
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

        # Task management section
        if checker_id:
            with use_scope("task_section"):
                display_task_list(checker_id, checker["name"])

        put_buttons(
            [
                {"label": "Save", "value": "save", "color": "success"},
                {"label": "Cancel", "value": "cancel", "color": "secondary"},
            ],
            onclick=lambda val: submit_form() if val == "save" else close_popup(),
        )

        # Register provider change handler
        pin_on_change("llm_provider", onchange=on_provider_change)

        # Register features change handler to show/hide task management
        def on_features_change(features):
            if not checker_id:
                return
            checker["enable_tasks"] = "Enable scheduled tasks" in features
            with use_scope("task_section", clear=True):
                if "Enable scheduled tasks" in features:
                    display_task_list(checker_id, checker["name"])
                else:
                    put_markdown("Enable scheduled tasks to manage automated tasks")

        pin_on_change("features", onchange=on_features_change)
