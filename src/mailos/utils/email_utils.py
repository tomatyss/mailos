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
