"""UI actions for handling global and checker actions."""

from pywebio.output import toast

from mailos import check_emails
from mailos.utils.config_utils import load_config, save_config


def handle_global_control(action, refresh_callback):
    """Handle global control actions (start/pause/check all)."""
    if action == "check":
        check_emails.main()
        toast("Manual check completed")
        refresh_callback()
    elif action in ["pause", "start"]:
        config = load_config()
        for checker in config["checkers"]:
            checker["enabled"] = action == "start"
        save_config(config)
        toast(f"All checkers {'started' if action == 'start' else 'paused'}")
        refresh_callback()


def handle_checker_action(
    checker_id, action, edit_callback=None, refresh_callback=None
):
    """Handle individual checker actions (delete/edit/toggle/copy).

    Args:
        checker_id: The ID of the checker to act on
        action: The action to perform (delete/edit/toggle/copy)
        edit_callback: Callback for edit action
        refresh_callback: Callback to refresh display
    """
    config = load_config()

    if action.startswith("delete_"):
        # Find and remove checker by ID
        config["checkers"] = [
            c for c in config["checkers"] if c.get("id") != checker_id
        ]
        toast("Checker deleted")
        save_config(config)
        refresh_callback()
        return True
    elif action.startswith("toggle_"):
        # Find and toggle checker by ID
        for checker in config["checkers"]:
            if checker.get("id") == checker_id:
                checker["enabled"] = not checker["enabled"]
                status = "enabled" if checker["enabled"] else "disabled"
                toast(f"Checker {status}")
                save_config(config)
                refresh_callback()
                break
        return True
    elif action.startswith("edit_"):
        if edit_callback:
            edit_callback(checker_id)  # Pass ID instead of index
        return False
    elif action.startswith("copy_"):
        # Find checker by ID and create a copy
        for checker in config["checkers"]:
            if checker.get("id") == checker_id:
                import uuid

                new_checker = checker.copy()
                new_checker["id"] = str(uuid.uuid4())  # Generate new ID for copy
                new_checker["name"] = f"{new_checker.get('name', '')} (Copy)"
                new_checker["enabled"] = False  # Start disabled by default
                new_checker["last_run"] = "Never"
                config["checkers"].append(new_checker)
                save_config(config)
                toast("Checker copied")
                refresh_callback()
                break
        return True
    return True
