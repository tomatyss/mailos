"""Tests for email reply handling."""

from unittest.mock import MagicMock, patch

import pytest

from mailos.reply import handle_email_reply
from mailos.vendors.config import VENDOR_CONFIGS


@pytest.fixture
def valid_email_data():
    """Provide valid email data fixture."""
    return {
        "from": "sender@example.com",
        "subject": "Test Subject",
        "body": "Test body content",
        "message_id": "<test123@example.com>",
        "msg_date": "2024-03-20",
    }


@pytest.fixture
def base_checker_config():
    """Provide base checker configuration fixture."""
    return {
        "id": "test-checker-1",  # Added id field
        "monitor_email": "support@example.com",
        "password": "test_password",
        "imap_server": "imap.example.com",
        "imap_port": 993,
        "auto_reply": True,
        "api_key": "test_api_key",
    }


@pytest.fixture
def mock_llm():
    """Mock LLM instance."""
    mock = MagicMock()
    mock.generate_sync.return_value = MagicMock(
        content=[MagicMock(data="Test response")]
    )
    return mock


@pytest.fixture
def mock_smtp():
    """Mock SMTP connection."""
    with patch("mailos.utils.email_utils.smtplib.SMTP_SSL") as mock:
        yield mock


@pytest.mark.parametrize(
    "provider,config",
    [
        ("anthropic", {"id": "test-anthropic", "api_key": "test_key"}),
        ("openai", {"id": "test-openai", "api_key": "test_key"}),
        (
            "bedrock-anthropic",
            {
                "id": "test-bedrock",
                "aws_access_key": "test_key",
                "aws_secret_key": "test_secret",
                "aws_region": "us-east-1",
            },
        ),
    ],
)
def test_handle_email_reply_different_providers(
    provider, config, valid_email_data, mock_llm, mock_smtp
):
    """Test handle_email_reply with different providers."""
    # Configure mock SMTP to return success
    mock_smtp.return_value.__enter__.return_value.send_message.return_value = {}

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        checker_config = {
            "monitor_email": "support@example.com",
            "password": "test_password",
            "imap_server": "smtp.example.com",  # Changed from imap to smtp
            "auto_reply": True,
            "llm_provider": provider,
            "model": VENDOR_CONFIGS[provider].default_model,
            **config,
        }

        result = handle_email_reply(checker_config, valid_email_data)
        assert result is True


def test_handle_email_reply_disabled(base_checker_config, valid_email_data):
    """Test handle_email_reply when auto-reply is disabled."""
    base_checker_config["auto_reply"] = False
    result = handle_email_reply(base_checker_config, valid_email_data)
    assert result is False


def test_handle_email_reply_missing_required_fields(
    base_checker_config, valid_email_data
):
    """Test handle_email_reply with missing required fields."""
    # Remove required field
    del valid_email_data["from"]
    result = handle_email_reply(base_checker_config, valid_email_data)
    assert result is False


@pytest.mark.parametrize("optional_field", ["body", "msg_date", "message_id"])
def test_handle_email_reply_missing_optional_fields(
    optional_field, base_checker_config, valid_email_data, mock_llm, mock_smtp
):
    """Test handle_email_reply with missing optional fields."""
    # Configure mock SMTP to return success
    mock_smtp.return_value.__enter__.return_value.send_message.return_value = {}

    email_data = valid_email_data.copy()
    del email_data[optional_field]

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        # Update the SMTP server in config
        base_checker_config["imap_server"] = "smtp.example.com"
        # Add required LLM configuration
        base_checker_config.update(
            {
                "llm_provider": "anthropic",
                "model": "claude-3-sonnet",
                "api_key": "test_api_key",
            }
        )
        result = handle_email_reply(base_checker_config, email_data)
        assert result is True


def test_handle_email_reply_with_attachments(
    base_checker_config, valid_email_data, mock_llm, mock_smtp
):
    """Test handle_email_reply with attachments."""
    # Configure mock SMTP to return success
    mock_smtp.return_value.__enter__.return_value.send_message.return_value = {}

    # Add attachments to email data
    valid_email_data["attachments"] = [
        {
            "path": "/path/to/test.pdf",
            "type": "application/pdf",
            "original_name": "test.pdf",
        }
    ]

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        base_checker_config.update(
            {
                "llm_provider": "anthropic",
                "model": "claude-3-sonnet",
                "api_key": "test_api_key",
            }
        )
        result = handle_email_reply(base_checker_config, valid_email_data)
        assert result is True


def test_handle_email_reply_llm_error(base_checker_config, valid_email_data, mock_smtp):
    """Test handle_email_reply with LLM initialization error."""
    with patch("mailos.reply.LLMFactory.create", return_value=None):
        result = handle_email_reply(base_checker_config, valid_email_data)
        assert result is False


def test_handle_email_reply_empty_response(
    base_checker_config, valid_email_data, mock_llm, mock_smtp
):
    """Test handle_email_reply with empty LLM response."""
    mock_llm.generate_sync.return_value = MagicMock(content=[])

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        result = handle_email_reply(base_checker_config, valid_email_data)
        assert result is False
