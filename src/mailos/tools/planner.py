"""Planner tool for generating step-by-step plans using the current LLM instance."""

from typing import Dict, Optional

from mailos.utils.logger_utils import logger
from mailos.vendors.base import BaseLLM
from mailos.vendors.models import Content, ContentType, Message, RoleType, Tool

# Global variable to store the LLM instance
_llm_instance: Optional[BaseLLM] = None


def set_llm_instance(llm: BaseLLM) -> None:
    """Set the LLM instance to use for planning.

    Args:
        llm: LLM instance to use for generating plans
    """
    global _llm_instance
    _llm_instance = llm


def generate_plan(task: str, context: Optional[str] = None) -> Dict:
    """Generate a step-by-step plan for the given task.

    Args:
        task: Task description to generate a plan for
        context: Optional additional context for the task

    Returns:
        Dict containing the generated plan or error message
    """
    if not _llm_instance:
        return {
            "status": "error",
            "message": "LLM instance not set. Call set_llm_instance first.",
        }

    try:
        # Construct the planning prompt
        system_prompt = (
            "You are a planning assistant. Given a task, generate a clear and "
            "detailed step-by-step plan. Each step should be specific and "
            "actionable. Format your response as a numbered list with clear "
            "steps. Focus on breaking down complex tasks into manageable pieces."
        )

        # Add context if provided
        user_prompt = f"Task: {task}\n"
        if context:
            user_prompt += f"Context: {context}\n"
        user_prompt += "\nGenerate a detailed step-by-step plan:"

        # Create messages for the LLM
        messages = [
            Message(
                role=RoleType.SYSTEM,
                content=[Content(type=ContentType.TEXT, data=system_prompt)],
            ),
            Message(
                role=RoleType.USER,
                content=[Content(type=ContentType.TEXT, data=user_prompt)],
            ),
        ]

        # Use generate_sync instead of generate for synchronous execution
        response = _llm_instance.generate_sync(messages)

        logger.info(f"Generated plan for task: {task}")

        # Extract the plan from the response
        plan_text = (
            response.content[0].data if response.content else "No plan generated"
        )

        return {
            "status": "success",
            "plan": plan_text,
            "metadata": {
                "model": response.model,
                "finish_reason": response.finish_reason,
            },
        }

    except Exception as e:
        logger.error(f"Error generating plan: {str(e)}")
        return {"status": "error", "message": f"Failed to generate plan: {str(e)}"}


# Create the planner tool instance
planner_tool = Tool(
    name="generate_plan",
    description="Generate a detailed step-by-step plan for a given task",
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Description of the task to generate a plan for",
            },
            "context": {
                "type": "string",
                "description": "Optional additional context for the task",
            },
        },
        "required": ["task"],
    },
    required_params=["task"],
    function=generate_plan,
)
