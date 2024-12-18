"""UI functions for managing automated tasks."""

from pywebio.output import (
    close_popup,
    popup,
    put_buttons,
    put_markdown,
    toast,
    use_scope,
)
from pywebio.pin import pin, put_input, put_textarea

from mailos.utils.config_utils import load_config
from mailos.utils.logger_utils import logger
from mailos.utils.task_utils import TaskManager


def create_task_form(
    checker_id: str, checker_name: str, task_id: str = None, on_save=None
):
    """Create a form for new task or editing existing one.

    Args:
        checker_id: ID of the checker to add/edit task for
        checker_name: Name of the checker for display
        task_id: ID of task to edit, or None for new task
        on_save: Callback function to save the task
    """
    task = None
    if task_id:
        task = TaskManager.get_task(checker_id, task_id)
        if not task:
            logger.warning(f"No task found with ID: {task_id}")
            return
    else:
        task = {}

    def submit_form():
        # Validate required fields
        if not pin.task_title or not pin.task_description or not pin.schedule:
            toast("Title, description, and schedule are required", color="error")
            return

        task_config = {
            "title": pin.task_title,
            "description": pin.task_description,
            "schedule": pin.schedule,
            "enabled": True,  # Default to enabled
            "variables": {},  # Can be updated later
        }

        success = False
        if task_id:
            success = TaskManager.update_task(checker_id, task_id, task_config)
        else:
            success = TaskManager.add_task(checker_id, task_config)

        if success:
            toast(f"Task {'updated' if task_id else 'added'} successfully")
            if on_save:
                on_save()
        else:
            toast("Failed to save task", color="error")

        close_popup()

    with popup(f"{'Edit' if task_id else 'New'} Task for {checker_name}", size="large"):
        put_markdown(f"### {'Edit' if task_id else 'New'} Task")
        put_markdown(f"**Checker**: {checker_name}")

        put_input(
            "task_title",
            type="text",
            label="Title",
            value=task.get("title", ""),
            help_text="A short, descriptive title for this task",
        )

        put_textarea(
            "task_description",
            label="Description",
            value=task.get("description", ""),
            rows=5,
            help_text=(
                "Detailed description of what this task should do. The system will "
                "analyze this description to determine which tool to use and how to "
                "execute the task."
            ),
        )

        put_input(
            "schedule",
            type="text",
            label="Schedule (Cron Expression)",
            value=task.get("schedule", "*/5 * * * *"),  # Default to every 5 minutes
            help_text=(
                "Cron expression format: minute hour day month weekday\n"
                "Common examples:\n"
                "*/5 * * * * (every 5 minutes)\n"
                "0 9 * * * (daily at 9 AM)\n"
                "0 */2 * * * (every 2 hours)\n"
                "0 9 * * 1-5 (weekdays at 9 AM)"
            ),
        )

        put_buttons(
            [
                {"label": "Save", "value": "save", "color": "success"},
                {"label": "Cancel", "value": "cancel", "color": "secondary"},
            ],
            onclick=lambda val: submit_form() if val == "save" else close_popup(),
        )


def refresh_task_list(checker_id: str):
    """Refresh the task list display.

    Args:
        checker_id: ID of the checker
    """
    config = load_config()
    for checker in config["checkers"]:
        if checker.get("id") == checker_id:
            with use_scope("task_section", clear=True):
                display_task_list(checker_id, checker["name"])
            break


def handle_task_action(action: str, checker_id: str, task_id: str = None):
    """Handle task management actions.

    Args:
        action: The action to perform ('add', 'edit', or 'delete')
        checker_id: ID of the checker
        task_id: ID of the task (required for edit/delete actions)
    """
    logger.debug(
        f"Handling task action: {action} for checker {checker_id} task {task_id}"
    )

    if action == "edit":
        task = TaskManager.get_task(checker_id, task_id)
        if task:
            create_task_form(
                checker_id,
                task["title"],
                task_id,
                on_save=lambda: refresh_task_list(checker_id),
            )
        else:
            toast("Task not found", color="error")

    elif action == "delete":
        if TaskManager.delete_task(checker_id, task_id):
            toast("Task deleted successfully")
            refresh_task_list(checker_id)
        else:
            toast("Failed to delete task", color="error")

    elif action == "add":
        config = load_config()
        checker_name = None
        for c in config["checkers"]:
            if c.get("id") == checker_id:
                checker_name = c["name"]
                break

        if checker_name:
            create_task_form(
                checker_id,
                checker_name,
                on_save=lambda: refresh_task_list(checker_id),
            )
        else:
            toast("Checker not found", color="error")


def display_task_list(checker_id: str, checker_name: str):
    """Display list of tasks for a checker with management options."""
    tasks = TaskManager.get_tasks(checker_id)

    with use_scope("tasks", clear=True):
        put_markdown(f"### Scheduled Tasks for {checker_name}")
        put_markdown("---")

        if not tasks:
            put_markdown("No tasks configured")
        else:
            for task in tasks:
                with use_scope(f"task_{task['id']}"):
                    put_markdown(f"#### {task['title']}")
                    put_markdown(f"Description: {task['description']}")
                    put_markdown(f"Schedule: {task['schedule']}")
                    put_markdown(f"Last Run: {task.get('last_run', 'Never')}")

                    def button_click(val, tid=task["id"]):
                        if val == "edit":
                            handle_task_action("edit", checker_id, tid)
                        elif val == "delete":
                            handle_task_action("delete", checker_id, tid)

                    put_buttons(
                        [
                            {"label": "Edit", "value": "edit", "color": "primary"},
                            {"label": "Delete", "value": "delete", "color": "danger"},
                        ],
                        onclick=button_click,
                    )
                    put_markdown("---")

        put_buttons(
            [{"label": "Add Task", "value": "add", "color": "success"}],
            onclick=lambda val: (
                handle_task_action("add", checker_id) if val == "add" else None
            ),
        )
