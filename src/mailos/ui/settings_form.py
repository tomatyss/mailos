"""UI functions for general settings form."""

from pywebio.output import close_popup, popup, put_buttons, put_markdown
from pywebio.pin import pin, put_select, put_textarea

from mailos.utils.config_utils import load_config, save_config
from mailos.utils.logger_utils import logger, parse_log_level


def create_settings_form():
    """Create form for general settings."""
    config = load_config()
    settings = config.get("settings", {})
    no_reply_indicators = config.get("no_reply_indicators", [])

    def submit_form():
        try:
            # Parse no-reply indicators from textarea
            new_indicators = [
                indicator.strip()
                for indicator in pin.no_reply_indicators.split("\n")
                if indicator.strip()
            ]

            # Update config with new settings
            config["settings"] = {
                "log_level": pin.log_level,
                "check_interval": int(pin.check_interval),
            }
            config["no_reply_indicators"] = new_indicators

            save_config(config)

            # Update log level
            level = parse_log_level(pin.log_level)
            logger.setLevel(level)

            close_popup()
        except Exception as e:
            logger.error(f"Failed to save settings: {str(e)}")

    with popup("General Settings", size="large"):
        put_markdown("### General Settings")

        # Log level selection
        put_select(
            "log_level",
            options=[
                {"label": "Debug", "value": "debug"},
                {"label": "Info", "value": "info"},
                {"label": "Warning", "value": "warning"},
                {"label": "Error", "value": "error"},
                {"label": "Critical", "value": "critical"},
            ],
            label="Log Level",
            value=settings.get("log_level", "info"),
            help_text="Set the application logging level",
        )

        # Check interval selection
        put_select(
            "check_interval",
            options=[
                {"label": "Every minute", "value": "60"},
                {"label": "Every 5 minutes", "value": "300"},
                {"label": "Every 15 minutes", "value": "900"},
                {"label": "Every 30 minutes", "value": "1800"},
                {"label": "Every hour", "value": "3600"},
            ],
            label="Check Interval",
            value=str(settings.get("check_interval", 300)),
            help_text="How often to check for new emails",
        )

        # No-reply indicators textarea
        put_markdown("### No-Reply Indicators")
        put_markdown(
            "Enter email addresses or patterns (one per line) that indicate "
            "automated/no-reply emails:"
        )
        put_textarea(
            "no_reply_indicators",
            value="\n".join(no_reply_indicators),
            rows=10,
            help_text=(
                "These patterns will be used to identify automated/no-reply emails"
            ),
        )

        put_buttons(
            [
                {"label": "Save", "value": "save", "color": "success"},
                {"label": "Cancel", "value": "cancel", "color": "secondary"},
            ],
            onclick=lambda val: submit_form() if val == "save" else close_popup(),
        )
