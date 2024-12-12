"""Bash command execution tool."""

import shlex
import subprocess
from typing import Dict, Optional

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def execute_bash(
    command: str, working_dir: Optional[str] = None, timeout: Optional[int] = 30
) -> Dict:
    """Execute a bash command and return the output.

    Args:
        command: Command to execute
        working_dir: Optional working directory for command execution
        timeout: Optional timeout in seconds (default: 30)

    Returns:
        Dict with execution status, output, and error if any
    """
    try:
        # Split command into arguments safely
        args = shlex.split(command)

        # Execute command with timeout
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout)

            return {
                "status": "success" if process.returncode == 0 else "error",
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            error_msg = "Command timed out"
            logger.error(f"Error executing bash command: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "stdout": stdout,
                "stderr": stderr,
            }

    except Exception as e:
        logger.error(f"Error executing bash command: {str(e)}")
        return {"status": "error", "error": str(e)}


# Define the bash command tool
bash_command_tool = Tool(
    name="execute_bash",
    description="Execute a bash command and return the output",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to execute"},
            "working_dir": {
                "type": "string",
                "description": "Optional working directory for command execution",
            },
            "timeout": {
                "type": "integer",
                "description": "Optional timeout in seconds (default: 30)",
            },
        },
    },
    required_params=["command"],
    function=execute_bash,
)
