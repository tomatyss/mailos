"""UI functions for managing email tasks."""

from pywebio.output import (
    close_popup,
    popup,
    put_buttons,
    put_markdown,
    toast,
    use_scope,
)
from pywebio.pin import pin, put_input, put_textarea

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
        if (
            not pin.task_name
            or not pin.recipients
            or not pin.subject_template
            or not pin.body_template
            or not pin.schedule
        ):
            toast("All fields are required", color="error")
            return

        task_config = {
            "name": pin.task_name,
            "recipients": [r.strip() for r in pin.recipients.split(",")],
            "subject_template": pin.subject_template,
            "body_template": pin.body_template,
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

        # Task configuration fields
        put_input(
            "task_name",
            type="text",
            label="Task Name",
            value=task.get("name", ""),
            help_text="A descriptive name for this task",
        )

        put_input(
            "recipients",
            type="text",
            label="Recipients (comma-separated)",
            value=",".join(task.get("recipients", [])),
            help_text="List of email addresses to send to",
        )

        put_input(
            "subject_template",
            type="text",
            label="Subject Template",
            value=task.get("subject_template", ""),
            help_text="Template for email subject. Use {variable} for placeholders.",
        )

        put_textarea(
            "body_template",
            label="Body Template",
            value=task.get("body_template", ""),
            rows=5,
            help_text="Template for email body. Use {variable} for placeholders.",
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


def display_task_list(checker_id: str, checker_name: str):
    """Display list of tasks for a checker with management options.

    Args:
        checker_id: ID of the checker
        checker_name: Name of the checker for display
    """
    tasks = TaskManager.get_tasks(checker_id)

    with use_scope("tasks", clear=True):
        put_markdown(f"### Scheduled Tasks for {checker_name}")
        put_markdown("---")

        if not tasks:
            put_markdown("No tasks configured")
        else:
            for task in tasks:
                with use_scope(f"task_{task['id']}"):
                    put_markdown(f"#### {task['name']}")
                    put_markdown(
                        f"- Recipients: {', '.join(task['recipients'])}\n"
                        f"- Schedule: {task['schedule']}\n"
                        f"- Last Run: {task.get('last_run', 'Never')}"
                    )
                    put_buttons(
                        [
                            {
                                "label": "Edit",
                                "value": "edit",
                                "color": "primary",
                            },
                            {
                                "label": "Delete",
                                "value": "delete",
                                "color": "danger",
                            },
                        ],
                        onclick=lambda val, task_id=task["id"]: handle_task_action(
                            val, checker_id, checker_name, task_id
                        ),
                    )
                    put_markdown("---")  # Separator between tasks

        put_buttons(
            [{"label": "Add Task", "value": "add", "color": "success"}],
            onclick=lambda _: create_task_form(
                checker_id,
                checker_name,
                on_save=lambda: display_task_list(checker_id, checker_name),
            ),
        )


def handle_task_action(action: str, checker_id: str, checker_name: str, task_id: str):
    """Handle task management actions."""
    if action == "edit":
        create_task_form(
            checker_id,
            checker_name,
            task_id,
            on_save=lambda: display_task_list(checker_id, checker_name),
        )
    elif action == "delete":
        if TaskManager.delete_task(checker_id, task_id):
            toast("Task deleted successfully")
            display_task_list(checker_id, checker_name)
        else:
            toast("Failed to delete task", color="error")
