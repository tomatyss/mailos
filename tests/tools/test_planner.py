"""Tests for the planner tool."""

from unittest.mock import MagicMock

import pytest

from mailos.tools.planner import planner_tool, set_llm_instance
from mailos.vendors.models import Content, ContentType, LLMResponse


@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    llm = MagicMock()
    # Mock generate_sync instead of generate
    llm.generate_sync.return_value = LLMResponse(
        content=[
            Content(
                type=ContentType.TEXT,
                data="1. First step\n2. Second step\n3. Third step",
            )
        ],
        model="test-model",
        finish_reason="stop",
    )
    return llm


def test_planner_successful_generation(mock_llm):
    """Test successful plan generation."""
    # Set up the LLM instance
    set_llm_instance(mock_llm)

    # Generate plan
    result = planner_tool.function(task="Test task", context="Test context")

    # Verify result
    assert result["status"] == "success"
    assert "plan" in result
    assert result["plan"] == "1. First step\n2. Second step\n3. Third step"
    assert result["metadata"]["model"] == "test-model"
    assert result["metadata"]["finish_reason"] == "stop"

    # Verify LLM was called with correct messages
    call_args = mock_llm.generate_sync.call_args
    messages = call_args[0][0]  # First positional argument
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "Test task" in messages[1].content[0].data
    assert "Test context" in messages[1].content[0].data


def test_planner_error_handling(mock_llm):
    """Test error handling during plan generation."""
    # Set up the LLM instance
    set_llm_instance(mock_llm)

    # Setup mock to raise exception
    mock_llm.generate_sync.side_effect = Exception("Test error")

    # Generate plan
    result = planner_tool.function(task="Test task")

    # Verify error handling
    assert result["status"] == "error"
    assert "Failed to generate plan" in result["message"]


def test_planner_without_context(mock_llm):
    """Test plan generation without optional context."""
    # Set up the LLM instance
    set_llm_instance(mock_llm)

    # Generate plan without context
    result = planner_tool.function(task="Test task")

    # Verify result
    assert result["status"] == "success"
    assert "plan" in result

    # Verify context was not included in prompt
    call_args = mock_llm.generate_sync.call_args
    messages = call_args[0][0]  # First positional argument
    assert "Context:" not in messages[1].content[0].data


def test_planner_without_llm():
    """Test planner behavior when LLM is not set."""
    # Clear any existing LLM instance
    set_llm_instance(None)

    # Try to generate plan without LLM
    result = planner_tool.function(task="Test task")

    # Verify error handling
    assert result["status"] == "error"
    assert "LLM instance not set" in result["message"]
