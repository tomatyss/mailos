"""Tests for the bash command tool."""

import subprocess

import pytest

from mailos.tools.bash_command import execute_bash


def test_execute_bash_success(mock_subprocess):
    """Test successful command execution."""
    result = execute_bash("ls -l")

    assert result["status"] == "success"
    assert result["return_code"] == 0
    assert result["stdout"] == "stdout"
    assert result["stderr"] == "stderr"

    # Verify command was executed with correct parameters
    mock_subprocess.Popen.assert_called_once()
    args, kwargs = mock_subprocess.Popen.call_args
    assert args[0] == ["ls", "-l"]
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["text"] is True


def test_execute_bash_with_working_dir(mock_subprocess, tmp_path):
    """Test command execution with working directory."""
    result = execute_bash("pwd", working_dir=str(tmp_path))

    assert result["status"] == "success"
    # Verify working directory was passed correctly
    args, kwargs = mock_subprocess.Popen.call_args
    assert kwargs["cwd"] == str(tmp_path)


def test_execute_bash_timeout(mock_subprocess):
    """Test command timeout handling."""
    # Configure mock to simulate timeout
    cmd = "sleep 10"
    timeout = 1
    mock_subprocess.Popen.return_value.communicate.side_effect = (
        subprocess.TimeoutExpired(cmd, timeout)
    )

    result = execute_bash(cmd, timeout=timeout)

    assert result["status"] == "error"
    assert result["error"] == f"Command '{cmd}' timed out after {timeout} seconds"


def test_execute_bash_command_error(mock_subprocess):
    """Test handling of command execution errors."""
    # Configure mock to simulate command failure
    mock_subprocess.Popen.return_value.returncode = 1

    result = execute_bash("invalid_command")

    assert result["status"] == "error"
    assert result["return_code"] == 1


def test_execute_bash_exception_handling(mock_subprocess):
    """Test handling of unexpected exceptions."""
    # Configure mock to raise an exception
    mock_subprocess.Popen.side_effect = Exception("Unexpected error")

    result = execute_bash("ls")

    assert result["status"] == "error"
    assert "Unexpected error" in result["error"]


@pytest.mark.parametrize(
    "command,expected_args",
    [
        ("ls -l", ["ls", "-l"]),
        ('echo "hello world"', ["echo", "hello world"]),
        ("git status", ["git", "status"]),
    ],
)
def test_execute_bash_command_parsing(mock_subprocess, command, expected_args):
    """Test correct parsing of different command formats."""
    execute_bash(command)

    args, _ = mock_subprocess.Popen.call_args
    assert args[0] == expected_args


def test_execute_bash_with_custom_timeout(mock_subprocess):
    """Test command execution with custom timeout."""
    execute_bash("long_running_command", timeout=60)

    # Verify timeout was passed correctly
    _, kwargs = mock_subprocess.Popen.call_args
    assert mock_subprocess.Popen.return_value.communicate.call_args[1]["timeout"] == 60


def test_execute_bash_output_capture(mock_subprocess):
    """Test capturing of command output."""
    mock_subprocess.Popen.return_value.communicate.return_value = (
        "custom stdout",
        "custom stderr",
    )

    result = execute_bash("echo test")

    assert result["stdout"] == "custom stdout"
    assert result["stderr"] == "custom stderr"
