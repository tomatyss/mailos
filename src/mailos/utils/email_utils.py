"""
This module provides utility functions for handling email messages.

Functions:
    get_email_body(email_message): Extracts the email body from a potentially
    multipart email message.

Dependencies:
    mailos.utils.logger_utils: Provides the setup_logger function for logging.
    mailos.utils.attachment_utils: Provides attachment handling functionality.

Usage example:
    body = get_email_body(email_message)
    attachments = process_attachments(email_message, sender_email)
"""

import mimetypes
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from mailos.utils.attachment_utils import AttachmentManager
from mailos.utils.logger_utils import logger

attachment_manager = AttachmentManager()


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


def process_attachments(email_message, sender_email: str) -> List[Dict]:
    """Process and save attachments from an email message.

    Args:
        email_message: The email message containing attachments
        sender_email: Email address of the sender

    Returns:
        List of dictionaries containing attachment metadata
    """
    try:
        return attachment_manager.extract_attachments(email_message, sender_email)
    except Exception as e:
        logger.error(f"Failed to process attachments: {e}")
        return []


def _get_mime_type(filename: str) -> tuple[str, str]:
    """Get the MIME type and subtype for a file.

    Args:
        filename: Name of the file

    Returns:
        Tuple of (maintype, subtype)
    """
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        maintype, subtype = mime_type.split("/")
        return maintype, subtype
    return "application", "octet-stream"


def attach_files_from_current_thread(
    msg: MIMEMultipart, recipient: str, email_data: Dict
) -> None:
    """Attach only the files from the current email thread to the reply.

    Args:
        msg: The email message to attach files to
        recipient: Email address of the recipient (where files are stored)
        email_data: Dictionary containing the current email thread data
    """
    try:
        # Get attachments from the current thread
        current_attachments = email_data.get("attachments", [])
        if not current_attachments:
            logger.debug("No attachments in current thread")
            return

        # Get the recipient's directory
        sender_dir = attachment_manager._get_sender_directory(recipient)
        if not sender_dir.exists():
            logger.warning(f"Recipient directory does not exist: {sender_dir}")
            return

        # Only attach files that are part of the current thread
        for attachment in current_attachments:
            filepath = sender_dir / attachment["saved_name"]
            if filepath.is_file():
                try:
                    maintype, subtype = _get_mime_type(filepath.name)
                    with open(filepath, "rb") as f:
                        content = f.read()

                        if maintype == "image":
                            # Use MIMEImage for images
                            part = MIMEImage(content, _subtype=subtype)
                        else:
                            # Use MIMEApplication for other files
                            part = MIMEApplication(content, _subtype=subtype)

                        # Use original filename in the attachment
                        part.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=attachment["original_name"],
                        )
                        msg.attach(part)
                        logger.info(
                            f"Attached file from current thread: "
                            f"{attachment['original_name']} "
                            f"(type: {maintype}/{subtype})"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to attach file {attachment['original_name']}: {e}"
                    )

    except Exception as e:
        logger.error(f"Error attaching files from current thread: {e}")


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

        # Attach only files from the current thread
        attach_files_from_current_thread(msg, recipient, email_data)

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
