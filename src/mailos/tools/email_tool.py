"""Email sending tool."""

from typing import Dict, List, Optional

from mailos.utils.config_utils import load_config
from mailos.utils.email_utils import send_email as send_email_util
from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def send_email(
    to: str,
    subject: str,
    body: str,
    checker_id: str,
    attachments: Optional[List[str]] = None,
) -> Dict:
    """Send an email using the specified checker's SMTP configuration.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        checker_id: ID of the checker configuration to use
        attachments: Optional list of file paths to attach

    Returns:
        Dict with operation status and details
    """
    try:
        # Load configuration
        config = load_config()
        if not config:
            return {"status": "error", "message": "No configuration found"}

        # Find checker configuration
        checker = next(
            (c for c in config.get("checkers", []) if c.get("id") == checker_id),
            None,
        )
        if not checker:
            return {
                "status": "error",
                "message": f"Checker configuration not found for ID: {checker_id}",
            }

        # Get SMTP settings from checker config
        smtp_server = checker["imap_server"].replace("imap", "smtp")
        smtp_port = 465  # Standard SSL port

        # Create email_data structure
        email_data = {
            "body": body,  # Include the body in email_data
            "from": checker["monitor_email"],  # Include sender email
            "subject": subject,  # Include subject
        }

        # Add attachments if provided
        if attachments:
            email_data["attachments"] = [
                {"path": path, "original_name": path.split("/")[-1]}
                for path in attachments
            ]

        # Send email using the utility function
        success = send_email_util(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            sender_email=checker["monitor_email"],
            password=checker["password"],
            recipient=to,
            subject=subject,
            body=body,
            email_data=email_data,  # Now includes body and other required fields
        )

        if success:
            return {
                "status": "success",
                "message": f"Email sent successfully to {to}",
                "details": {
                    "to": to,
                    "from": checker["monitor_email"],
                    "subject": subject,
                    "attachments": attachments or [],
                },
            }
        else:
            return {"status": "error", "message": "Failed to send email"}

    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


# Define the email sending tool
email_tool = Tool(
    name="send_email",
    description=(
        "Send an email with optional attachments using a configured checker's SMTP settings"  # noqa E501
    ),
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address",
            },
            "subject": {
                "type": "string",
                "description": "Email subject",
            },
            "body": {
                "type": "string",
                "description": "Email body content",
            },
            "checker_id": {
                "type": "string",
                "description": "ID of the checker configuration to use for SMTP settings",  # noqa E501
            },
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of file paths to attach",
            },
        },
    },
    required_params=["to", "subject", "body", "checker_id"],
    function=send_email,
)
