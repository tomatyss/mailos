"""Tests for email review tool."""

import email
from unittest.mock import MagicMock, patch

import pytest

from mailos.tools.email_review_tool import build_search_criteria, check_emails


def test_build_search_criteria_empty():
    """Test build_search_criteria with no parameters."""
    assert build_search_criteria() == "ALL"


def test_build_search_criteria_since_date():
    """Test build_search_criteria with since_date."""
    since_date = "2024-01-01"
    expected = '(SINCE "01-Jan-2024")'
    assert build_search_criteria(since_date=since_date) == expected


def test_build_search_criteria_until_date():
    """Test build_search_criteria with until_date."""
    until_date = "2024-01-01"
    # Add one day to make it inclusive
    expected = '(BEFORE "02-Jan-2024")'
    assert build_search_criteria(until_date=until_date) == expected


def test_build_search_criteria_sender():
    """Test build_search_criteria with sender."""
    sender = "test@example.com"
    expected = '(FROM "test@example.com")'
    assert build_search_criteria(sender=sender) == expected


def test_build_search_criteria_unread():
    """Test build_search_criteria with unread_only."""
    expected = "(UNSEEN)"
    assert build_search_criteria(unread_only=True) == expected


def test_build_search_criteria_all_params():
    """Test build_search_criteria with all parameters."""
    params = {
        "since_date": "2024-01-01",
        "until_date": "2024-01-31",
        "sender": "test@example.com",
        "unread_only": True,
    }
    expected = (
        '(SINCE "01-Jan-2024" BEFORE "01-Feb-2024" FROM "test@example.com" UNSEEN)'
    )
    assert build_search_criteria(**params) == expected


@pytest.fixture
def mock_config():
    """Fixture for mocked config."""
    return {
        "checkers": [
            {
                "id": "test-checker",
                "imap_server": "imap.test.com",
                "imap_port": 993,
                "monitor_email": "monitor@test.com",
                "password": "test-password",
            }
        ]
    }


@pytest.fixture
def mock_email_message():
    """Fixture for a mock email message."""
    msg = email.message.EmailMessage()
    msg["from"] = "sender@example.com"
    msg["subject"] = "Test Subject"
    msg["date"] = "Thu, 1 Jan 2024 12:00:00 +0000"
    msg["message-id"] = "<test123@example.com>"
    return msg


@patch("mailos.tools.email_review_tool.load_config")
@patch("imaplib.IMAP4_SSL")
def test_check_emails_success(
    mock_imap, mock_load_config, mock_config, mock_email_message
):
    """Test successful email check."""
    # Setup mocks
    mock_load_config.return_value = mock_config
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance

    # Mock email search and fetch responses
    mock_imap_instance.search.return_value = (None, [b"1"])
    mock_imap_instance.fetch.return_value = (
        None,
        [(b"", mock_email_message.as_bytes())],
    )

    # Call function
    result = check_emails(
        checker_id="test-checker",
        expected_senders=["sender@example.com"],
    )

    # Verify IMAP interactions
    mock_imap.assert_called_once_with("imap.test.com", 993)
    mock_imap_instance.login.assert_called_once_with(
        "monitor@test.com", "test-password"
    )
    mock_imap_instance.select.assert_called_once_with("inbox")

    # Verify result
    assert result["status"] == "GOOD"
    assert len(result["received_emails"]) == 1
    assert result["received_emails"][0]["from"] == "sender@example.com"
    assert result["received_emails"][0]["subject"] == "Test Subject"
    assert not result["missing_senders"]
    assert not result["unexpected_senders"]


@patch("mailos.tools.email_review_tool.load_config")
@patch("imaplib.IMAP4_SSL")
def test_check_emails_missing_sender(
    mock_imap, mock_load_config, mock_config, mock_email_message
):
    """Test email check with missing expected sender."""
    # Setup mocks
    mock_load_config.return_value = mock_config
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance

    # Mock empty email search response
    mock_imap_instance.search.return_value = (None, [b""])

    # Call function
    result = check_emails(
        checker_id="test-checker",
        expected_senders=["expected@example.com"],
    )

    # Verify result
    assert result["status"] == "BAD"
    assert not result["received_emails"]
    assert result["missing_senders"] == ["expected@example.com"]
    assert not result["unexpected_senders"]


@patch("mailos.tools.email_review_tool.load_config")
def test_check_emails_invalid_checker(mock_load_config, mock_config):
    """Test email check with invalid checker ID."""
    mock_load_config.return_value = mock_config

    result = check_emails(checker_id="invalid-checker")

    assert result["status"] == "ERROR"
    assert "Checker not found" in result["error"]
    assert not result["received_emails"]


@patch("mailos.tools.email_review_tool.load_config")
@patch("imaplib.IMAP4_SSL")
def test_check_emails_mark_as_read(
    mock_imap, mock_load_config, mock_config, mock_email_message
):
    """Test marking emails as read."""
    # Setup mocks
    mock_load_config.return_value = mock_config
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance

    # Mock email search and fetch responses
    mock_imap_instance.search.return_value = (None, [b"1"])
    mock_imap_instance.fetch.return_value = (
        None,
        [(b"", mock_email_message.as_bytes())],
    )

    # Call function with mark_as_read=True
    check_emails(checker_id="test-checker", mark_as_read=True)

    # Verify email was marked as read
    mock_imap_instance.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")


@patch("mailos.tools.email_review_tool.load_config")
@patch("imaplib.IMAP4_SSL")
def test_check_emails_date_range(
    mock_imap, mock_load_config, mock_config, mock_email_message
):
    """Test email check with date range."""
    # Setup mocks
    mock_load_config.return_value = mock_config
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance

    # Mock email search and fetch responses
    mock_imap_instance.search.return_value = (None, [b"1"])
    mock_imap_instance.fetch.return_value = (
        None,
        [(b"", mock_email_message.as_bytes())],
    )

    # Call function with date range
    since_date = "2024-01-01"
    until_date = "2024-01-31"
    result = check_emails(
        checker_id="test-checker",
        since_date=since_date,
        until_date=until_date,
    )

    # Verify date range in result
    assert result["check_period"]["from"] == "01-Jan-2024"
    assert result["check_period"]["to"] == "31-Jan-2024"


@patch("mailos.tools.email_review_tool.load_config")
@patch("imaplib.IMAP4_SSL")
def test_check_emails_imap_error(mock_imap, mock_load_config, mock_config):
    """Test handling of IMAP errors."""
    # Setup mocks
    mock_load_config.return_value = mock_config
    mock_imap_instance = MagicMock()
    mock_imap.return_value = mock_imap_instance

    # Mock IMAP error
    mock_imap_instance.login.side_effect = Exception("IMAP error")

    # Call function
    result = check_emails(checker_id="test-checker")

    # Verify error handling
    assert result["status"] == "ERROR"
    assert "IMAP error" in result["error"]
    assert not result["received_emails"]
