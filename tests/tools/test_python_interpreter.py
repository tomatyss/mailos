"""Tests for the Python interpreter tool."""

import pytest

from mailos.tools.python_interpreter import execute_python


def test_execute_python_success(capture_output):
    """Test successful Python code execution."""
    code = """
print('Hello, World!')
x = 5 + 3
print(f'Result: {x}')
"""
    result = execute_python(code)

    assert result["status"] == "success"
    assert "Hello, World!" in result["output"]
    assert "Result: 8" in result["output"]
    assert result["result"] is None  # No return value


def test_execute_python_syntax_error(capture_output):
    """Test handling of Python syntax errors."""
    code = """
print('Start')
if True
    print('Invalid syntax')
"""
    result = execute_python(code)

    assert result["status"] == "error"
    assert "SyntaxError" in result["error"]
    assert "Start" in result["output"]  # Should capture output before error


def test_execute_python_runtime_error(capture_output):
    """Test handling of runtime errors."""
    code = """
print('Before error')
x = 1 / 0  # ZeroDivisionError
print('After error')
"""
    result = execute_python(code)

    assert result["status"] == "error"
    assert "ZeroDivisionError" in result["error"]
    assert "Before error" in result["output"]
    assert "After error" not in result["output"]


def test_execute_python_with_imports(capture_output):
    """Test Python code execution with imports."""
    code = """
import math
print(f'Pi is approximately {math.pi:.2f}')
"""
    result = execute_python(code)

    assert result["status"] == "success"
    assert "Pi is approximately 3.14" in result["output"]


def test_execute_python_multiple_statements(capture_output):
    """Test execution of multiple Python statements."""
    code = """
x = 10
y = 20
print(f'Sum: {x + y}')
print(f'Product: {x * y}')
"""
    result = execute_python(code)

    assert result["status"] == "success"
    assert "Sum: 30" in result["output"]
    assert "Product: 200" in result["output"]


def test_execute_python_with_functions(capture_output):
    """Test Python code with function definitions and calls."""
    code = """
def greet(name):
    return f'Hello, {name}!'

message = greet('Python')
print(message)
"""
    result = execute_python(code)

    assert result["status"] == "success"
    assert "Hello, Python!" in result["output"]


def test_execute_python_scope_isolation(capture_output):
    """Test that each execution has isolated scope."""
    code1 = "x = 42"
    code2 = "print(x)"

    execute_python(code1)
    result = execute_python(code2)

    assert result["status"] == "error"
    assert "NameError" in result["error"]


def test_execute_python_large_output(capture_output):
    """Test handling of large output."""
    code = """
for i in range(1000):
    print(f'Line {i}')
"""
    result = execute_python(code)

    assert result["status"] == "success"
    assert "Line 0" in result["output"]
    assert "Line 999" in result["output"]


def test_execute_python_stderr_capture(capture_output):
    """Test capturing stderr output."""
    code = """
import sys
print('stdout message')
print('stderr message', file=sys.stderr)
"""
    result = execute_python(code)

    assert result["status"] == "success"
    assert "stdout message" in result["output"]
    # stderr should be captured and included in output
    assert "stderr message" in result["output"]


@pytest.mark.parametrize(
    "code,expected_error",
    [
        ("while True: pass", "TimeoutError"),  # Infinite loop
        ("import nonexistent_module", "ModuleNotFoundError"),  # Import error
        ("x = [1][2]", "IndexError"),  # Index error
        ("x = int('not_a_number')", "ValueError"),  # Value error
    ],
)
def test_execute_python_various_errors(capture_output, code, expected_error):
    """Test handling of various Python errors."""
    result = execute_python(code)

    assert result["status"] == "error"
    assert expected_error in result["error"] or expected_error in result["traceback"]
