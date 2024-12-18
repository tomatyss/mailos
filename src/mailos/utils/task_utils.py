"""Task management utilities for scheduled email sending."""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from croniter import croniter

from mailos.utils.config_utils import load_config, save_config
from mailos.utils.email_utils import send_email
from mailos.utils.logger_utils import logger
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory
from mailos.vendors.models import Content, ContentType, Message, RoleType


def _initialize_llm(checker_config: Dict[str, Any]):
    """Initialize LLM with appropriate configuration.

    Args:
        checker_config: Configuration dictionary for the checker

    Returns:
        Initialized LLM instance or None if initialization fails
    """
    llm_args = {
        "provider": checker_config["llm_provider"],
        "model": checker_config["model"],
    }

    vendor_config = VENDOR_CONFIGS.get(checker_config["llm_provider"])
    if not vendor_config:
        logger.error(f"Unknown LLM provider: {checker_config['llm_provider']}")
        return None

    for field in vendor_config.fields:
        field_name = "aws_region" if field.name == "region" else field.name

        if field_name in checker_config:
            llm_args[field_name] = checker_config[field_name]
        elif field.required:
            logger.error(
                f"Missing required field '{field_name}' for {vendor_config.name}"
            )
            return None
        elif field.default is not None:
            llm_args[field_name] = field.default

    return LLMFactory.create(**llm_args)


def _parse_llm_response(response_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse LLM response to extract subject and body.

    Handles various response formats:
    1. JSON format: {"subject": "...", "body": "..."}
    2. Markdown-like format:
       Subject: ...
       Body: ...
    3. Direct format (subject and body separated by newlines)
    """
    # Try JSON format first
    try:
        data = json.loads(response_text)
        if isinstance(data, dict) and "subject" in data and "body" in data:
            return data["subject"], data["body"]
    except json.JSONDecodeError:
        pass

    # Try Markdown-like format
    subject_match = re.search(r"(?:Subject|SUBJECT):\s*(.+?)(?:\n|$)", response_text)
    body_match = re.search(
        r"(?:Body|BODY):\s*(.+?)(?=(?:\n*Subject:|\n*$))", response_text, re.DOTALL
    )

    if subject_match and body_match:
        return subject_match.group(1).strip(), body_match.group(1).strip()

    # Try direct format (first line is subject, rest is body)
    lines = response_text.strip().split("\n", 1)
    if len(lines) >= 2:
        return lines[0].strip(), lines[1].strip()
    elif len(lines) == 1:
        return lines[0].strip(), ""

    logger.error("Could not parse LLM response into subject and body")
    return None, None


def create_task_prompt(task: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """Create a prompt for the LLM based on the task data.

    Args:
        task: Task configuration dictionary
        variables: Variables to use in templates

    Returns:
        Formatted prompt string for the LLM
    """
    return f"""
Context: You are processing email templates for a scheduled task. Here are the details:

Task: {task['name']}
Recipients: {', '.join(task['recipients'])}

Please process these templates by replacing variables (enclosed in {{}}) with their
values:

Available variables:
{json.dumps(variables, indent=2)}

Subject template:
{task['subject_template']}

Body template:
{task['body_template']}

Please compose a professional and helpful email.
Keep your response concise and relevant.

Return the processed subject and body in this format:
Subject: [processed subject]
Body: [processed body]

NOTE: YOUR RESPONSE WILL BE SENT TO THE RECIPIENTS DIRECTLY.
DO NOT ADD ANY INFORMATION NOT RELEVANT TO THE TASK.
"""


class TaskManager:
    """Manages scheduled email tasks for checkers."""

    @staticmethod
    def add_task(checker_id: str, task_config: Dict) -> bool:
        """Add a new task to a checker's configuration."""
        try:
            config = load_config()
            for checker in config["checkers"]:
                if checker.get("id") == checker_id:
                    # Initialize tasks list if it doesn't exist
                    if "tasks" not in checker:
                        checker["tasks"] = []

                    # Add task ID and creation timestamp
                    task_config["id"] = f"task_{len(checker['tasks']) + 1}"
                    task_config["created_at"] = datetime.now().isoformat()
                    task_config["last_run"] = None

                    # Validate cron expression
                    if not croniter.is_valid(task_config["schedule"]):
                        logger.error(
                            f"Invalid cron expression: {task_config['schedule']}"
                        )
                        return False

                    checker["tasks"].append(task_config)
                    save_config(config)
                    logger.info(
                        f"Added task {task_config['id']} to checker {checker_id}"
                    )
                    return True

            logger.warning(f"No checker found with ID: {checker_id}")
            return False

        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return False

    @staticmethod
    def update_task(checker_id: str, task_id: str, updates: Dict) -> bool:
        """Update an existing task's configuration."""
        try:
            config = load_config()
            for checker in config["checkers"]:
                if checker.get("id") == checker_id:
                    for task in checker.get("tasks", []):
                        if task["id"] == task_id:
                            # Validate cron expression if schedule is being updated
                            if "schedule" in updates:
                                if not croniter.is_valid(updates["schedule"]):
                                    logger.error(
                                        f"Invalid cron expression: "
                                        f"{updates['schedule']}"
                                    )
                                    return False

                            task.update(updates)
                            save_config(config)
                            logger.info(
                                f"Updated task {task_id} in checker {checker_id}"
                            )
                            return True

            logger.warning(f"Task {task_id} not found in checker {checker_id}")
            return False

        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return False

    @staticmethod
    def delete_task(checker_id: str, task_id: str) -> bool:
        """Delete a task from a checker's configuration."""
        try:
            config = load_config()
            for checker in config["checkers"]:
                if checker.get("id") == checker_id:
                    tasks = checker.get("tasks", [])
                    for i, task in enumerate(tasks):
                        if task["id"] == task_id:
                            tasks.pop(i)
                            save_config(config)
                            logger.info(
                                f"Deleted task {task_id} from checker {checker_id}"
                            )
                            return True

            logger.warning(f"Task {task_id} not found in checker {checker_id}")
            return False

        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False

    @staticmethod
    def get_tasks(checker_id: str) -> List[Dict]:
        """Get all tasks for a checker."""
        config = load_config()
        for checker in config["checkers"]:
            if checker.get("id") == checker_id:
                return checker.get("tasks", [])
        return []

    @staticmethod
    def get_task(checker_id: str, task_id: str) -> Optional[Dict]:
        """Get a specific task's configuration."""
        tasks = TaskManager.get_tasks(checker_id)
        for task in tasks:
            if task["id"] == task_id:
                return task
        return None

    @staticmethod
    def should_run_task(task: Dict) -> bool:
        """Check if a task should be run based on its schedule."""
        if not task.get("enabled", False):
            return False

        last_run = task.get("last_run")
        if not last_run:
            return True

        try:
            last_run_dt = datetime.fromisoformat(last_run)
            cron = croniter(task["schedule"], last_run_dt)
            next_run = cron.get_next(datetime)
            return datetime.now() >= next_run
        except Exception as e:
            logger.error(f"Error checking task schedule: {e}")
            return False

    @staticmethod
    def execute_task(checker_config: Dict, task: Dict) -> bool:
        """Execute a scheduled task."""
        try:
            # Initialize LLM with proper configuration
            llm = _initialize_llm(checker_config)
            if not llm or not hasattr(llm, "generate_sync"):
                logger.error(
                    "Failed to initialize LLM or sync generation not supported"
                )
                return False

            # Process templates with LLM
            system_message = Message(
                role=RoleType.SYSTEM,
                content=[
                    Content(
                        type=ContentType.TEXT,
                        data=checker_config.get(
                            "system_prompt", "You are a helpful email assistant."
                        ),
                    )
                ],
            )

            # Create prompt for processing templates
            variables = task.get("variables", {})
            variables["timestamp"] = datetime.now().isoformat()

            user_message = Message(
                role=RoleType.USER,
                content=[
                    Content(
                        type=ContentType.TEXT,
                        data=create_task_prompt(task, variables),
                    )
                ],
            )

            # Generate processed templates
            response = llm.generate_sync(
                messages=[system_message, user_message],
                stream=False,
            )

            if not response or not response.content:
                logger.error("Empty response from LLM")
                return False

            # Parse LLM response to get subject and body
            subject, body = _parse_llm_response(response.content[0].data)
            if not subject or not body:
                logger.error("Failed to parse LLM response")
                return False

            # Send email to all recipients
            smtp_server = checker_config["imap_server"].replace("imap", "smtp")
            success = True

            for recipient in task["recipients"]:
                if not send_email(
                    smtp_server=smtp_server,
                    smtp_port=465,  # Standard SSL port
                    sender_email=checker_config["monitor_email"],
                    password=checker_config["password"],
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    email_data={},  # No original email for scheduled tasks
                ):
                    success = False
                    logger.error(f"Failed to send task email to {recipient}")

            # Update last run timestamp
            if success:
                task["last_run"] = datetime.now().isoformat()
                TaskManager.update_task(checker_config["id"], task["id"], task)
                logger.info(f"Successfully executed task {task['id']}")

            return success

        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return False
