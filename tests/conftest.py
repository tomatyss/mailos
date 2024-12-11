"""Common test fixtures and configurations."""

from unittest.mock import MagicMock

import pytest
import requests

from mailos.vendors.models import Content, LLMResponse, RoleType, Tool


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
        "llm_provider": "anthropic",  # Added default provider
        "model": "claude-3-sonnet",  # Added default model
        "api_key": "test_api_key",  # Added default API key
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


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    return [
        Tool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: None,
        )
    ]


@pytest.fixture
def mock_weather_api(monkeypatch):
    """Mock OpenWeatherMap API responses."""

    def create_weather_response(city="London", country="GB"):
        return {
            "name": city,
            "sys": {"country": country},
            "weather": [{"description": "clear sky"}],
            "main": {
                "temp": 293.15,  # 20°C
                "feels_like": 292.15,
                "pressure": 1013,
                "humidity": 65,
            },
            "wind": {"speed": 3.6},  # ~13 km/h
            "clouds": {"all": 20},
        }

    mock_response = MagicMock(spec=requests.Response)
    mock_response.ok = True
    mock_response.json.return_value = create_weather_response()

    def mock_get(*args, **kwargs):
        if not kwargs.get("params", {}).get("appid"):
            mock_response.ok = False
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "API key required"
            )
        return mock_response

    monkeypatch.setattr("requests.get", mock_get)
    return mock_response
