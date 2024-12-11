"""UI display functions."""

from pywebio.output import clear, put_markdown, use_scope

from mailos.ui.actions import handle_checker_action, handle_global_control
from mailos.ui.checker_form import create_checker_form
from mailos.ui.checker_list import display_checker, display_checker_controls
from mailos.utils.config_utils import load_config


def display_checkers(config, save_checker=None):
    """Display configured email checkers."""
    if not config["checkers"]:
        put_markdown("### No email checkers configured yet")
        return

    put_markdown("### Configured Email Checkers")

    def on_filter_change(value):
        clear("checker_list")
        with use_scope("checker_list"):
            for checker in config["checkers"]:
                display_checker(
                    checker,
                    lambda checker_id, action: handle_checker_action(
                        checker_id,
                        action,
                        edit_callback=lambda x: create_checker_form(x, save_checker),
                        refresh_callback=lambda: refresh_display(save_checker),
                    ),
                    status_filter=value,
                )

    # Add handler for global controls and filter
    display_checker_controls(
        lambda action: handle_global_control(
            action, lambda: refresh_display(save_checker)
        ),
        on_filter=on_filter_change,
    )

    # Initial display
    with use_scope("checker_list"):
        for checker in config["checkers"]:
            display_checker(
                checker,
                lambda checker_id, action: handle_checker_action(
                    checker_id,
                    action,
                    edit_callback=lambda x: create_checker_form(x, save_checker),
                    refresh_callback=lambda: refresh_display(save_checker),
                ),
            )
    put_markdown("---")


def refresh_display(save_checker=None):
    """Refresh the display of configured email checkers."""
    config = load_config()
    clear("checkers")
    with use_scope("checkers"):
        display_checkers(config, save_checker)
