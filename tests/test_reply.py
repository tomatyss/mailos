"""Tests for email reply functionality."""

from unittest.mock import patch

import pytest

from mailos.reply import EmailData, create_email_prompt, handle_email_reply
from mailos.utils.reply_utils import should_reply
from mailos.vendors.config import VENDOR_CONFIGS


def test_create_email_prompt(valid_email_data, mock_tools):
    """Test email prompt creation."""
    email = EmailData(
        sender=valid_email_data["from"],
        subject=valid_email_data["subject"],
        body=valid_email_data["body"],
        msg_date=valid_email_data["msg_date"],
        message_id=valid_email_data["message_id"],
        attachments=valid_email_data.get("attachments", []),
    )
    prompt = create_email_prompt(email, mock_tools)

    assert email.sender in prompt
    assert email.subject in prompt
    assert email.body in prompt
    assert "Test tool" in prompt  # Tool description should be in prompt


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


def test_handle_email_reply_missing_required_fields(base_checker_config):
    """Test handle_email_reply with missing required fields."""
    email_data = {
        "subject": "Test Subject",  # missing 'from' field
        "body": "Test body",
    }
    result = handle_email_reply(base_checker_config, email_data)
    assert result is False


def test_handle_email_reply_auto_reply_disabled(base_checker_config, valid_email_data):
    """Test handle_email_reply with auto-reply disabled."""
    base_checker_config["auto_reply"] = False
    result = handle_email_reply(base_checker_config, valid_email_data)
    assert result is False


def test_handle_email_reply_smtp_error(
    base_checker_config, valid_email_data, mock_llm, mock_smtp
):
    """Test handle_email_reply with SMTP error."""
    mock_smtp.return_value.__enter__.return_value.send_message.side_effect = Exception(
        "SMTP Error"
    )

    with patch("mailos.reply.LLMFactory.create", return_value=mock_llm):
        # Update the SMTP server in config
        base_checker_config["imap_server"] = "smtp.example.com"
        result = handle_email_reply(base_checker_config, valid_email_data)
        assert result is False


def test_handle_email_reply_unknown_provider(base_checker_config, valid_email_data):
    """Test handle_email_reply with unknown provider."""
    base_checker_config["llm_provider"] = "unknown_provider"
    result = handle_email_reply(base_checker_config, valid_email_data)
    assert result is False


def test_handle_email_reply_missing_credentials(base_checker_config, valid_email_data):
    """Test handle_email_reply with missing credentials."""
    del base_checker_config["api_key"]
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
