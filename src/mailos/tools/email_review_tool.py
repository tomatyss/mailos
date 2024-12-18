"""Email review and monitoring tool."""

import email
import imaplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def check_emails(
    imap_server: str,
    imap_port: int,
    email_addr: str,
    password: str,
    expected_senders: List[str],
    since_date: Optional[str] = None,
) -> Dict:
    """Check emails against expected senders and generate report.

    Args:
        imap_server: IMAP server address
        imap_port: IMAP port number
        email_addr: Email address to check
        password: Email account password
        expected_senders: List of expected email senders
        since_date: Optional ISO date to check emails since (defaults to last 24h)

    Returns:
        Dict containing:
        - received_emails: List of actual received emails
        - missing_senders: List of expected senders who didn't send emails
        - unexpected_senders: List of senders not in expected list
        - status: "GOOD" if all expected emails received, "BAD" otherwise
    """
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_addr, password)
        mail.select("inbox")

        # Set date range
        if since_date:
            search_date = datetime.fromisoformat(since_date)
        else:
            search_date = datetime.now() - timedelta(days=1)

        date_str = search_date.strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{date_str}")'

        # Search for emails
        _, message_numbers = mail.search(None, search_criteria)
        received_emails = []
        actual_senders = set()

        for num in message_numbers[0].split():
            _, msg_data = mail.fetch(num, "(RFC822)")
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            sender = email.utils.parseaddr(email_message["from"])[1]
            subject = email_message["subject"]
            date = email_message["date"]

            received_emails.append({"from": sender, "subject": subject, "date": date})
            actual_senders.add(sender)

        # Compare against expected senders
        expected_set = set(expected_senders)
        missing_senders = list(expected_set - actual_senders)
        unexpected_senders = list(actual_senders - expected_set)

        # Determine status
        status = "GOOD" if not missing_senders else "BAD"

        # Clean up
        mail.close()
        mail.logout()

        return {
            "status": status,
            "received_emails": received_emails,
            "missing_senders": missing_senders,
            "unexpected_senders": unexpected_senders,
            "check_period": {
                "from": date_str,
                "to": datetime.now().strftime("%d-%b-%Y"),
            },
        }

    except Exception as e:
        error_msg = f"Error checking emails: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "ERROR",
            "error": error_msg,
            "received_emails": [],
            "missing_senders": expected_senders,
            "unexpected_senders": [],
        }


# Define the email review tool
email_review_tool = Tool(
    name="email_review",
    description="Review incoming emails and compare against expected senders",
    parameters={
        "type": "object",
        "properties": {
            "imap_server": {"type": "string", "description": "IMAP server address"},
            "imap_port": {"type": "integer", "description": "IMAP port number"},
            "email_addr": {"type": "string", "description": "Email address to check"},
            "password": {"type": "string", "description": "Email account password"},
            "expected_senders": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of expected email senders",
            },
            "since_date": {
                "type": "string",
                "description": "Optional ISO date to check emails since",
            },
        },
        "required": [
            "imap_server",
            "imap_port",
            "email_addr",
            "password",
            "expected_senders",
        ],
    },
    required_params=[
        "imap_server",
        "imap_port",
        "email_addr",
        "password",
        "expected_senders",
    ],
    function=check_emails,
)
