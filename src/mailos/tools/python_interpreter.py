"""Python code interpreter tool."""

import signal
import sys
import traceback
from io import StringIO
from typing import Dict

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Code execution timed out")


def execute_python(code: str, timeout: int = 5) -> Dict:
    """Execute Python code and return the output.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 5)

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

    # Set up the timeout handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    result = None
    try:
        # Split code into blocks that can be executed independently
        lines = code.strip().split("\n")
        current_block = []
        exec_globals = {}

        for line in lines:
            current_block.append(line)
            try:
                # Try to compile the current block
                block_code = "\n".join(current_block)
                compiled_code = compile(block_code, "<string>", "exec")
                # If compilation succeeds, execute the block
                exec(compiled_code, exec_globals)
                current_block = []  # Reset for next block
            except SyntaxError:
                # If we get a syntax error, keep accumulating lines
                # This handles multi-line statements
                continue
            except Exception as e:
                # For runtime errors, return immediately
                error_type = type(e).__name__
                error_msg = f"{error_type}: {str(e)}"
                error_traceback = traceback.format_exc()
                return {
                    "status": "error",
                    "error": error_msg,
                    "traceback": error_traceback,
                    "output": stdout.getvalue() + stderr.getvalue(),
                }

        # Try to compile and execute any remaining lines
        if current_block:
            try:
                block_code = "\n".join(current_block)
                compiled_code = compile(block_code, "<string>", "exec")
                exec(compiled_code, exec_globals)
            except Exception as e:
                error_type = type(e).__name__
                error_msg = f"{error_type}: {str(e)}"
                error_traceback = traceback.format_exc()
                return {
                    "status": "error",
                    "error": error_msg,
                    "traceback": error_traceback,
                    "output": stdout.getvalue() + stderr.getvalue(),
                }

        # Get any printed output
        output = stdout.getvalue() + stderr.getvalue()  # Include stderr in output

        return {
            "status": "success",
            "output": output,
            "result": str(result) if result is not None else None,
        }
    except TimeoutError as e:
        error_msg = f"TimeoutError: {str(e)}"
        logger.error(f"Code execution timed out: {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "traceback": error_msg,
            "output": stdout.getvalue() + stderr.getvalue(),
        }
    except Exception as e:
        error_type = type(e).__name__
        error_msg = f"{error_type}: {str(e)}"
        error_traceback = traceback.format_exc()
        logger.error(f"Error executing Python code: {error_traceback}")
        return {
            "status": "error",
            "error": error_msg,
            "traceback": error_traceback,
            "output": stdout.getvalue() + stderr.getvalue(),
        }
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        # Restore the old signal handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


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
