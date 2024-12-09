"""Tests for email reply functionality."""

from unittest.mock import MagicMock, patch

import pytest

from mailos.reply import create_email_prompt, handle_email_reply, should_reply
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.models import Content, LLMResponse, RoleType


@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    llm = MagicMock()
    llm.generate_sync.return_value = LLMResponse(
        content=[Content(type="text", data="Test response")], role=RoleType.ASSISTANT
    )
    return llm


@pytest.fixture
def valid_email_data():
    """Create valid email data for testing."""
    return {
        "from": "sender@example.com",
        "subject": "Test Subject",
        "body": "Test body content",
        "msg_date": "2024-03-20",
        "message_id": "<test123@example.com>",
    }


@pytest.fixture
def valid_checker_config():
    """Create valid checker configuration for testing."""
    return {
        "monitor_email": "support@example.com",
        "password": "test_password",
        "imap_server": "imap.example.com",
        "auto_reply": True,
        "llm_provider": "anthropic",
        "model": "claude-3-sonnet",
        "api_key": "test_api_key",
    }


def test_create_email_prompt():
    """Test email prompt creation."""
    email_data = {
        "from": "test@example.com",
        "subject": "Test Subject",
        "body": "Test Message",
    }
    prompt = create_email_prompt(email_data)

    assert "test@example.com" in prompt
    assert "Test Subject" in prompt
    assert "Test Message" in prompt


def test_should_reply_valid_email():
    """Test should_reply with valid email."""
    email_data = {"from": "user@example.com", "subject": "Regular inquiry"}
    assert should_reply(email_data) is True


def test_should_reply_noreply_email():
    """Test should_reply with no-reply email."""
    email_data = {"from": "no-reply@example.com", "subject": "Notification"}
    assert should_reply(email_data) is False


@pytest.mark.parametrize(
    "provider,config",
    [
        ("anthropic", {"api_key": "test_key"}),
        ("openai", {"api_key": "test_key"}),
        (
            "bedrock-anthropic",
            {
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
        mock_llm.generate_sync.assert_called_once()


def test_handle_email_reply_missing_required_fields(valid_checker_config):
    """Test handle_email_reply with missing required fields."""
    email_data = {
        "subject": "Test Subject",  # missing 'from' field
        "body": "Test body",
    }
    result = handle_email_reply(valid_checker_config, email_data)
    assert result is False


def test_handle_email_reply_auto_reply_disabled(valid_checker_config, valid_email_data):
    """Test handle_email_reply with auto-reply disabled."""
    valid_checker_config["auto_reply"] = False
    result = handle_email_reply(valid_checker_config, valid_email_data)
    assert result is False


@patch("smtplib.SMTP_SSL")
def test_handle_email_reply_smtp_error(
    mock_smtp, valid_checker_config, valid_email_data, mock_llm
):
    """Test handle_email_reply with SMTP error."""
    mock_smtp.return_value.__enter__.return_value.send_message.side_effect = Exception(
        "SMTP Error"
    )

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        # Update the SMTP server in config
        valid_checker_config["imap_server"] = "smtp.example.com"
        result = handle_email_reply(valid_checker_config, valid_email_data)
        assert result is False


def test_handle_email_reply_unknown_provider(valid_checker_config, valid_email_data):
    """Test handle_email_reply with unknown provider."""
    valid_checker_config["llm_provider"] = "unknown_provider"
    result = handle_email_reply(valid_checker_config, valid_email_data)
    assert result is False


def test_handle_email_reply_missing_credentials(valid_checker_config, valid_email_data):
    """Test handle_email_reply with missing credentials."""
    del valid_checker_config["api_key"]
    result = handle_email_reply(valid_checker_config, valid_email_data)
    assert result is False


@pytest.mark.parametrize("optional_field", ["body", "msg_date", "message_id"])
def test_handle_email_reply_missing_optional_fields(
    optional_field, valid_checker_config, valid_email_data, mock_llm, mock_smtp
):
    """Test handle_email_reply with missing optional fields."""
    # Configure mock SMTP to return success
    mock_smtp.return_value.__enter__.return_value.send_message.return_value = {}

    email_data = valid_email_data.copy()
    del email_data[optional_field]

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        # Update the SMTP server in config
        valid_checker_config["imap_server"] = "smtp.example.com"
        result = handle_email_reply(valid_checker_config, email_data)
        assert result is True
