"""Shared prompt utilities for LLM interactions."""

import json
from typing import Any, Dict, List, Optional

from mailos.vendors.models import Tool


def create_system_prompt(checker_config: Dict[str, Any]) -> str:
    """Create a system prompt for LLM interactions.

    Args:
        checker_config: Configuration dictionary for the checker

    Returns:
        Formatted system prompt string
    """
    base_prompt = (
        f"Your email is {checker_config['monitor_email']}. "
        f"When using tools, always use checker_id='{checker_config['id']}' "
        f"to ensure operations are performed using the correct configuration."
    )

    # Append any custom system prompt from the checker config
    if checker_config.get("system_prompt"):
        base_prompt += f"\n\n{checker_config['system_prompt']}"

    return base_prompt


def create_task_prompt(
    task: Dict[str, Any], variables: Dict[str, Any], enabled_tools: List[Tool]
) -> str:
    """Create a prompt for task execution.

    Args:
        task: Task configuration dictionary
        variables: Variables to use in templates
        enabled_tools: List of enabled tools for this checker

    Returns:
        Formatted task prompt string
    """
    tools_description = ""
    if enabled_tools:
        tools_description = "You have access to the following tools:\n" + "\n".join(
            f"- {tool.name}: {tool.description}" for tool in enabled_tools
        )

    return f"""
Context: You are processing a scheduled task. Here are the details:

Title: {task['title']}
Description: {task['description']}

Available variables:
{json.dumps(variables, indent=2)}

{tools_description}

Your task is to determine the appropriate action to take based on the task description.
Use the available tools to accomplish the task.
"""


def create_email_prompt(
    email_data: Dict[str, Any],
    available_tools: Optional[List[Tool]] = None,
    has_images: bool = False,
) -> str:
    """Create a prompt for email response.

    Args:
        email_data: Dictionary containing email information
        available_tools: List of available tools
        has_images: Whether the email contains images

    Returns:
        Formatted email prompt string
    """
    tools_description = ""
    if available_tools:
        tools_description = (
            "You have access to the following tools:\n"
            + "\n".join(
                f"- {tool.name}: {tool.description}" for tool in available_tools
            )
            + f"\n\nIMPORTANT: When using tools that create files (like create_pdf), "
            f"you MUST use the sender's email address ({email_data['sender']}) as the "
            f"sender_email parameter. This ensures files are saved in the correct "
            f"directory and will be properly attached to your response email."
        )

    image_context = (
        "\nThis email contains images which I've included for your analysis. "
        "Please examine them and incorporate relevant details in your response."
        if has_images
        else ""
    )

    return f"""
Context: You are responding to an email. Here are the details:{image_context}

From: {email_data['sender']}
Subject: {email_data['subject']}
Message: {email_data['body']}

{tools_description}

Please compose a professional and helpful response. Keep your response concise and
relevant. Your response will be followed by the original message, so you don't need
to quote it.
"""
