"""Common test fixtures and configurations."""

from unittest.mock import MagicMock

import pytest

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
def base_checker_config():
    """Create base checker configuration for testing."""
    return {
        "monitor_email": "support@example.com",
        "password": "test_password",
        "imap_server": "imap.example.com",
        "imap_port": 993,
        "auto_reply": True,
    }


@pytest.fixture
def provider_configs():
    """Provider-specific configurations for testing."""
    return {
        "anthropic": {
            "llm_provider": "anthropic",
            "model": "claude-3-sonnet",
            "api_key": "test_api_key",
        },
        "openai": {
            "llm_provider": "openai",
            "model": "gpt-4",
            "api_key": "test_api_key",
        },
        "bedrock-anthropic": {
            "llm_provider": "bedrock-anthropic",
            "model": "anthropic.claude-3-sonnet",
            "aws_access_key": "test_key",
            "aws_secret_key": "test_secret",
            "aws_region": "us-east-1",
        },
    }


@pytest.fixture
def smtp_config():
    """SMTP configuration for testing."""
    return {"smtp_server": "smtp.example.com", "smtp_port": 465, "use_ssl": True}


@pytest.fixture
def mock_smtp(monkeypatch):
    """Mock SMTP connection."""
    smtp_mock = MagicMock()
    monkeypatch.setattr("smtplib.SMTP_SSL", smtp_mock)
    return smtp_mock


@pytest.fixture
def mock_imap(monkeypatch):
    """Mock IMAP connection."""
    imap_mock = MagicMock()
    monkeypatch.setattr("imaplib.IMAP4_SSL", imap_mock)
    return imap_mock
