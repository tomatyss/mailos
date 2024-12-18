"""Task management utilities for automated task execution."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from croniter import croniter

from mailos.tools import TOOL_MAP
from mailos.utils.config_utils import load_config, save_config
from mailos.utils.logger_utils import logger
from mailos.utils.prompt_utils import create_system_prompt, create_task_prompt
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory
from mailos.vendors.models import Content, ContentType, Message, RoleType, Tool


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


class TaskManager:
    """Manages scheduled tasks."""

    @staticmethod
    def add_task(checker_id: str, task_config: Dict) -> bool:
        """Add a new task to a checker's configuration."""
        try:
            # Validate required fields
            required_fields = ["title", "description", "schedule"]
            for field in required_fields:
                if field not in task_config:
                    logger.error(f"Missing required field: {field}")
                    return False

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
            logger.debug(
                f"Attempting to delete task {task_id} from checker {checker_id}"
            )

            config = load_config()
            checker = None
            checker_index = None

            # Find checker
            for i, c in enumerate(config["checkers"]):
                if c.get("id") == checker_id:
                    checker = c
                    checker_index = i
                    break

            if not checker:
                logger.warning(f"Checker {checker_id} not found")
                return False

            logger.debug(f"Found checker {checker_id}")

            # Get current tasks
            tasks = checker.get("tasks", [])
            if not tasks:
                logger.warning(f"No tasks found for checker {checker_id}")
                return False

            logger.debug(f"Current tasks: {[t['id'] for t in tasks]}")

            # Find task index
            task_index = None
            for i, task in enumerate(tasks):
                if task["id"] == task_id:
                    task_index = i
                    break

            if task_index is None:
                logger.warning(f"Task {task_id} not found in checker {checker_id}")
                return False

            # Remove task
            removed_task = tasks.pop(task_index)
            logger.debug(f"Removed task {removed_task['id']}")

            # Update checker's tasks
            checker["tasks"] = tasks
            config["checkers"][checker_index] = checker

            logger.debug(f"Remaining tasks: {[t['id'] for t in checker['tasks']]}")

            # Save updated config
            if save_config(config):
                logger.info(
                    f"Successfully deleted task {task_id} from checker {checker_id}"
                )
                return True
            else:
                logger.error("Failed to save config after deleting task")
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

            # Setup enabled tools
            enabled_tools = [
                Tool(
                    name=tool_name,
                    description=TOOL_MAP[tool_name].description,
                    parameters=TOOL_MAP[tool_name].parameters,
                    function=TOOL_MAP[tool_name].function,
                    required_params=TOOL_MAP[tool_name].required_params,
                )
                for tool_name in checker_config.get("enabled_tools", [])
                if tool_name in TOOL_MAP
            ]

            # Process task with LLM
            system_message = Message(
                role=RoleType.SYSTEM,
                content=[
                    Content(
                        type=ContentType.TEXT,
                        data=create_system_prompt(checker_config),
                    )
                ],
            )

            # Create prompt for processing task
            variables = task.get("variables", {})
            variables["timestamp"] = datetime.now().isoformat()

            user_message = Message(
                role=RoleType.USER,
                content=[
                    Content(
                        type=ContentType.TEXT,
                        data=create_task_prompt(task, variables, enabled_tools),
                    )
                ],
            )

            # Let the LLM vendor handle tool execution
            response = llm.generate_sync(
                messages=[system_message, user_message],
                stream=False,
                tools=enabled_tools,
            )

            if not response or not response.content:
                logger.error("Empty response from LLM")
                return False

            # Update last run timestamp
            task["last_run"] = datetime.now().isoformat()
            TaskManager.update_task(checker_config["id"], task["id"], task)
            logger.info(f"Successfully executed task {task['id']}")

            return True

        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return False
