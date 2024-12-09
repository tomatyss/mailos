"""UI functions for creating and editing checker forms."""

from pywebio.output import close_popup, popup, put_buttons, put_markdown, use_scope
from pywebio.pin import pin_on_change, put_checkbox, put_input, put_select, put_textarea

from mailos.utils.config_utils import load_config
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory


def create_checker_form(index=None, on_save=None):
    """Create a form for new checker or editing existing one."""
    config = load_config() if index is not None else {"checkers": []}
    checker = config["checkers"][index] if index is not None else {}
    llm_providers = list(LLMFactory._providers.keys())

    # Pre-select current features
    current_features = []
    if checker.get("enabled", False):
        current_features.append("Enable monitoring")
    if checker.get("auto_reply", False):
        current_features.append("Auto-reply to emails")

    def submit_form():
        if on_save:
            on_save(index)
        close_popup()

    with popup(f"{'Edit' if index is not None else 'New'} Email Checker", size="large"):
        put_markdown(f"### {'Edit' if index is not None else 'New'} Email Checker")

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
        )

        # LLM configuration
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
