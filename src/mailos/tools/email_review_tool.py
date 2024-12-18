"""Email review and monitoring tool."""

import email
import imaplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from mailos.utils.config_utils import load_config
from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def build_search_criteria(
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    sender: Optional[str] = None,
    unread_only: bool = False,
) -> str:
    """Build IMAP search criteria based on filters.

    Args:
        since_date: Start date in ISO format
        until_date: End date in ISO format
        sender: Specific sender email to filter by
        unread_only: Only return unread emails if True

    Returns:
        IMAP search criteria string
    """
    criteria = []

    if since_date:
        date_str = datetime.fromisoformat(since_date).strftime("%d-%b-%Y")
        criteria.append(f'SINCE "{date_str}"')

    if until_date:
        # Add 1 day to until_date to make it inclusive
        date_str = (datetime.fromisoformat(until_date) + timedelta(days=1)).strftime(
            "%d-%b-%Y"
        )
        criteria.append(f'BEFORE "{date_str}"')

    if sender:
        criteria.append(f'FROM "{sender}"')

    if unread_only:
        criteria.append("UNSEEN")

    return f'({" ".join(criteria)})' if criteria else "ALL"


def check_emails(
    checker_id: str,
    expected_senders: Optional[List[str]] = None,
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    sender: Optional[str] = None,
    unread_only: bool = False,
    mark_as_read: bool = False,
) -> Dict:
    """Check emails with flexible filtering options.

    Args:
        checker_id: ID of the checker to use credentials from
        expected_senders: Optional list of expected email senders for monitoring
        since_date: Optional ISO date to check emails since
        until_date: Optional ISO date to check emails until
        sender: Optional specific sender email to filter by
        unread_only: Only return unread emails if True
        mark_as_read: Mark retrieved emails as read if True

    Returns:
        Dict containing:
        - received_emails: List of actual received emails
        - missing_senders: List of expected senders who didn't send emails
        (if expected_senders provided)
        - unexpected_senders: List of senders not in expected list
        (if expected_senders provided)
        - status: "GOOD" if all expected emails received or no monitoring required,
        "BAD" otherwise
    """
    try:
        # Get checker config
        config = load_config()
        checker_config = None
        for checker in config["checkers"]:
            if checker.get("id") == checker_id:
                checker_config = checker
                break

        if not checker_config:
            error_msg = f"Checker not found with ID: {checker_id}"
            logger.error(error_msg)
            return {
                "status": "ERROR",
                "error": error_msg,
                "received_emails": [],
                "missing_senders": expected_senders or [],
                "unexpected_senders": [],
                "total_emails": 0,
            }

        # Connect to IMAP server using checker credentials
        mail = imaplib.IMAP4_SSL(
            checker_config["imap_server"], checker_config["imap_port"]
        )
        mail.login(checker_config["monitor_email"], checker_config["password"])
        mail.select("inbox")

        # Set default date range if not provided
        if not since_date and not until_date:
            since_date = (datetime.now() - timedelta(days=1)).isoformat()

        # Build search criteria
        search_criteria = build_search_criteria(
            since_date=since_date,
            until_date=until_date,
            sender=sender,
            unread_only=unread_only,
        )

        # Search for emails
        _, message_numbers = mail.search(None, search_criteria)
        received_emails = []
        actual_senders = set()

        for num in message_numbers[0].split():
            _, msg_data = mail.fetch(num, "(RFC822)")
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            msg_sender = email.utils.parseaddr(email_message["from"])[1]
            subject = email_message["subject"]
            date = email_message["date"]

            received_emails.append(
                {
                    "from": msg_sender,
                    "subject": subject,
                    "date": date,
                    "message_id": email_message["message-id"]
                    or f"generated-{num.decode()}",
                }
            )
            actual_senders.add(msg_sender)

            # Mark as read if requested
            if mark_as_read:
                mail.store(num, "+FLAGS", "\\Seen")

        # Compare against expected senders if provided
        status = "GOOD"
        missing_senders = []
        unexpected_senders = []

        if expected_senders:
            expected_set = set(expected_senders)
            missing_senders = list(expected_set - actual_senders)
            unexpected_senders = list(actual_senders - expected_set)
            status = "GOOD" if not missing_senders else "BAD"

        # Clean up
        mail.close()
        mail.logout()

        # Determine date range for response
        start_date = (
            datetime.fromisoformat(since_date)
            if since_date
            else datetime.now() - timedelta(days=1)
        )
        end_date = datetime.fromisoformat(until_date) if until_date else datetime.now()

        return {
            "status": status,
            "received_emails": received_emails,
            "missing_senders": missing_senders,
            "unexpected_senders": unexpected_senders,
            "check_period": {
                "from": start_date.strftime("%d-%b-%Y"),
                "to": end_date.strftime("%d-%b-%Y"),
            },
            "total_emails": len(received_emails),
        }

    except Exception as e:
        error_msg = f"Error checking emails: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "ERROR",
            "error": error_msg,
            "received_emails": [],
            "missing_senders": expected_senders or [],
            "unexpected_senders": [],
            "total_emails": 0,
        }


# Define the email review tool
email_review_tool = Tool(
    name="email_review",
    description="Review and filter emails with flexible search options using checker credentials",  # noqa E501
    parameters={
        "type": "object",
        "properties": {
            "checker_id": {
                "type": "string",
                "description": "ID of the checker to use credentials from",
            },
            "expected_senders": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of expected email senders for monitoring",
            },
            "since_date": {
                "type": "string",
                "description": "Optional ISO date to check emails since (e.g. 2024-01-01)",  # noqa E501
            },
            "until_date": {
                "type": "string",
                "description": "Optional ISO date to check emails until (e.g. 2024-01-31)",  # noqa E501
            },
            "sender": {
                "type": "string",
                "description": "Optional specific sender email to filter by",
            },
            "unread_only": {
                "type": "boolean",
                "description": "Only return unread emails if True",
                "default": False,
            },
            "mark_as_read": {
                "type": "boolean",
                "description": "Mark retrieved emails as read if True",
                "default": False,
            },
        },
        "required": [
            "checker_id",
        ],
    },
    required_params=[
        "checker_id",
    ],
    function=check_emails,
)
