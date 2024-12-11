"""
This module provides utility functions for handling email messages.

Functions:
    get_email_body(email_message): Extracts the email body from a potentially
    multipart email message.

Dependencies:
    mailos.utils.logger_utils: Provides the setup_logger function for logging.

Usage example:
    body = get_email_body(email_message)
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mailos.utils.logger_utils import setup_logger

logger = setup_logger("email_utils")


def get_email_body(email_message):
    """Extract the email body from a potentially multipart message."""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode()
                except (UnicodeDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to decode email part: {e}")
                    return part.get_payload()
    else:
        try:
            return email_message.get_payload(decode=True).decode()
        except (UnicodeDecodeError, AttributeError) as e:
            logger.warning(f"Failed to decode email payload: {e}")
            return email_message.get_payload()
    return ""


def send_email(
    smtp_server, smtp_port, sender_email, password, recipient, subject, body, email_data
):
    """Send an email using SMTP."""
    try:
        # Add logging to debug email_data contents
        logger.debug(f"Email data received: {email_data}")

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient
        msg["Subject"] = f"Re: {subject}"

        # Handle potentially None values with defaults
        original_body = email_data.get("body", "")
        if original_body is None:
            original_body = ""
            logger.warning("Email body was None, using empty string instead")

        # Combine AI response with quoted original message
        full_message = (
            f"{body}\n\n"
            f"> -------- Original Message --------\n"
            f"> Subject: {email_data.get('subject', '(No subject)')}\n"
            f"> Date: {email_data.get('msg_date', '(No date)')}\n"
            f"> From: {email_data.get('from', '(No sender)')}\n"
            f"> Message-ID: {email_data.get('message_id', '(No ID)')}\n"
            f">\n"
            f"> {original_body.replace('\n', '\n> ')}"
        )

        msg.attach(MIMEText(full_message, "plain"))

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, password)
            server.send_message(msg)

        logger.info(f"Reply sent successfully to {recipient}")
        return True

    except Exception as e:
        logger.error(
            f"Failed to send reply: {str(e)}", exc_info=True
        )  # Added exc_info for better error tracking
        return False
