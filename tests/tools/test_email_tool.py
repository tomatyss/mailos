"""Tests for the email sending tool."""

from unittest.mock import patch

import pytest

from mailos.tools.email_tool import email_tool


@pytest.fixture
def mock_config():
    """Mock configuration with test checker."""
    return {
        "checkers": [
            {
                "id": "test-checker",
                "monitor_email": "test@example.com",
                "imap_server": "imap.example.com",
                "password": "test-password",
            }
        ]
    }


@pytest.fixture
def mock_load_config(mock_config):
    """Mock the load_config function."""
    with patch("mailos.tools.email_tool.load_config") as mock:
        mock.return_value = mock_config
        yield mock


@pytest.fixture
def mock_send_email():
    """Mock the send_email utility function."""
    with patch("mailos.tools.email_tool.send_email_util") as mock:
        mock.return_value = True
        yield mock


def test_send_email_success(mock_load_config, mock_send_email):
    """Test successful email sending."""
    result = email_tool.function(
        to="recipient@example.com",
        subject="Test Subject",
        body="Test Body",
        checker_id="test-checker",
    )

    assert result["status"] == "success"
    assert "sent successfully" in result["message"]

    # Verify send_email was called with correct parameters
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[1]
    assert call_args["smtp_server"] == "smtp.example.com"
    assert call_args["smtp_port"] == 465
    assert call_args["sender_email"] == "test@example.com"
    assert call_args["password"] == "test-password"
    assert call_args["recipient"] == "recipient@example.com"
    assert call_args["subject"] == "Test Subject"
    assert call_args["body"] == "Test Body"
    assert call_args["email_data"]["body"] == "Test Body"
    assert call_args["email_data"]["from"] == "test@example.com"
    assert call_args["email_data"]["subject"] == "Test Subject"


def test_send_email_with_attachments(mock_load_config, mock_send_email):
    """Test email sending with attachments."""
    attachments = ["/path/to/file1.pdf", "/path/to/file2.jpg"]
    result = email_tool.function(
        to="recipient@example.com",
        subject="Test Subject",
        body="Test Body",
        checker_id="test-checker",
        attachments=attachments,
    )

    assert result["status"] == "success"
    assert "sent successfully" in result["message"]

    # Verify attachments were properly formatted
    call_args = mock_send_email.call_args[1]
    assert "attachments" in call_args["email_data"]
    sent_attachments = call_args["email_data"]["attachments"]
    assert len(sent_attachments) == 2
    assert sent_attachments[0]["path"] == attachments[0]
    assert sent_attachments[0]["original_name"] == "file1.pdf"
    assert sent_attachments[1]["path"] == attachments[1]
    assert sent_attachments[1]["original_name"] == "file2.jpg"


def test_send_email_invalid_checker_id(mock_load_config, mock_send_email):
    """Test email sending with invalid checker ID."""
    result = email_tool.function(
        to="recipient@example.com",
        subject="Test Subject",
        body="Test Body",
        checker_id="invalid-checker",
    )

    assert result["status"] == "error"
    assert "not found" in result["message"]
    mock_send_email.assert_not_called()


def test_send_email_no_config(mock_load_config, mock_send_email):
    """Test email sending with no configuration."""
    mock_load_config.return_value = None
    result = email_tool.function(
        to="recipient@example.com",
        subject="Test Subject",
        body="Test Body",
        checker_id="test-checker",
    )

    assert result["status"] == "error"
    assert "No configuration found" in result["message"]
    mock_send_email.assert_not_called()


def test_send_email_send_failure(mock_load_config, mock_send_email):
    """Test handling of email sending failure."""
    mock_send_email.return_value = False
    result = email_tool.function(
        to="recipient@example.com",
        subject="Test Subject",
        body="Test Body",
        checker_id="test-checker",
    )

    assert result["status"] == "error"
    assert "Failed to send email" in result["message"]


def test_send_email_exception(mock_load_config):
    """Test handling of exceptions during email sending."""
    with patch(
        "mailos.tools.email_tool.send_email_util", side_effect=Exception("Test error")
    ):
        result = email_tool.function(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            checker_id="test-checker",
        )

        assert result["status"] == "error"
        assert "Test error" in result["message"]


def test_tool_definition():
    """Test tool definition and metadata."""
    # Test basic tool attributes
    assert email_tool.name == "send_email"
    assert isinstance(email_tool.description, str)
    assert len(email_tool.description) > 0

    # Test parameters schema
    assert email_tool.parameters["type"] == "object"
    properties = email_tool.parameters["properties"]

    # Test required parameters
    required_params = ["to", "subject", "body", "checker_id"]
    assert set(email_tool.required_params) == set(required_params)

    # Verify each required parameter is properly defined
    for param in required_params:
        assert param in properties
        assert "type" in properties[param]
        assert "description" in properties[param]
        assert isinstance(properties[param]["description"], str)
        assert len(properties[param]["description"]) > 0

    # Test optional parameters
    assert "attachments" in properties
    assert properties["attachments"]["type"] == "array"
    assert "description" in properties["attachments"]
    assert isinstance(properties["attachments"]["description"], str)
    assert len(properties["attachments"]["description"]) > 0
