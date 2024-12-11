"""Python code interpreter tool."""

import sys
import traceback
from io import StringIO
from typing import Dict

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def execute_python(code: str) -> Dict:
    """Execute Python code and return the output.

    Args:
        code: Python code to execute

    Returns:
        Dict with execution status, output/error, and any printed output
    """
    # Capture stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout = StringIO()
    stderr = StringIO()
    sys.stdout = stdout
    sys.stderr = stderr

    result = None
    try:
        # Execute the code
        exec_globals = {}
        exec(code, exec_globals)

        # Get any printed output
        output = stdout.getvalue()

        return {
            "status": "success",
            "output": output,
            "result": str(result) if result is not None else None,
        }
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Error executing Python code: {error_msg}")
        return {
            "status": "error",
            "error": str(e),
            "traceback": error_msg,
            "output": stdout.getvalue(),  # Include any output before the error
        }
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# Define the Python interpreter tool
python_interpreter_tool = Tool(
    name="execute_python",
    description="Execute Python code and return the output",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"}
        },
    },
    required_params=["code"],
    function=execute_python,
)
