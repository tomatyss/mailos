"""Email checking and task execution functions."""

import email
import imaplib
import sys
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from mailos.reply import handle_email_reply
from mailos.utils.attachment_utils import AttachmentManager
from mailos.utils.config_utils import load_config, update_checker_field
from mailos.utils.email_utils import get_email_body
from mailos.utils.logger_utils import logger
from mailos.utils.reply_utils import should_reply
from mailos.utils.task_utils import TaskManager


def check_emails(checker_config):
    """Check emails for a given checker configuration."""
    try:
        logger.info(f"Connecting to {checker_config['imap_server']}...")
        mail = imaplib.IMAP4_SSL(
            checker_config["imap_server"], checker_config["imap_port"]
        )
        mail.login(checker_config["monitor_email"], checker_config["password"])

        logger.info("Connected successfully")

        # Initialize attachment manager
        attachment_manager = AttachmentManager()

        # Select inbox
        status, messages = mail.select("INBOX")
        logger.info(f"Inbox select status: {status}")

        # Search for unread emails
        logger.info("Searching for unread emails...")
        result, data = mail.search(None, "UNSEEN")

        if result == "OK":
            if not data[0]:
                logger.info("No unread emails found")
            else:
                email_ids = data[0].split()
                logger.info(f"Found {len(email_ids)} unread emails")

                for num in email_ids:
                    result, email_data = mail.fetch(num, "(RFC822)")
                    if result == "OK":
                        email_body = email_data[0][1]
                        email_message = email.message_from_bytes(email_body)

                        # Debug: Log email structure
                        logger.info("Email structure:")
                        for part in email_message.walk():
                            logger.info(f"Content type: {part.get_content_type()}")
                            logger.info(
                                f"Content Disposition: "
                                f"{part.get('Content-Disposition')}"
                            )
                            if part.get_filename():
                                logger.info(f"Found attachment: {part.get_filename()}")

                        # Extract attachments if present
                        sender_email = email.utils.parseaddr(email_message["from"])[1]
                        logger.info(f"Processing attachments from {sender_email}")

                        try:
                            attachments = attachment_manager.extract_attachments(
                                email_message, sender_email
                            )

                            if attachments:
                                logger.info(
                                    f"Saved {len(attachments)} attachments from "
                                    f"{sender_email}"
                                )
                                for att in attachments:
                                    logger.info(
                                        f"Saved attachment: {att['original_name']} -> "
                                        f"{att['saved_name']}"
                                    )
                                    logger.info(f"Saved to path: {att['path']}")
                            else:
                                logger.info("No attachments found in the email")

                        except Exception as e:
                            logger.error(
                                f"Error extracting attachments: {str(e)}", exc_info=True
                            )
                            attachments = []

                        # Create a properly formatted email_data dictionary
                        parsed_email = {
                            "from": email_message["from"],
                            "subject": email_message["subject"],
                            "body": get_email_body(email_message),
                            "msg_date": email_message["date"],
                            "message_id": email_message["message-id"]
                            or f"generated-{num.decode()}",
                            "attachments": attachments,
                        }

                        logger.info(
                            f"New email found: Subject='{parsed_email['subject']}'"
                            f"From='{parsed_email['from']}'"
                        )

                        # Optionally mark as read after processing
                        mail.store(num, "+FLAGS", "\\Seen")

                        if checker_config.get("auto_reply", False) and should_reply(
                            parsed_email
                        ):
                            handle_email_reply(checker_config, parsed_email)
                    else:
                        logger.error(f"Failed to fetch email {num}: {result}")
        else:
            logger.error(f"Search failed: {result}")

        # Manage attachment storage
        attachment_manager.manage_storage_space()

        # Update last_run timestamp using the dedicated function
        checker_id = checker_config.get("id")
        if checker_id:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if update_checker_field(checker_id, "last_run", current_time):
                logger.info(f"Updated last_run for checker ID: {checker_id}")
            else:
                logger.warning(
                    f"Failed to update last_run for checker ID: {checker_id}"
                )
        else:
            logger.warning("Checker has no ID, cannot update last_run timestamp")

        mail.close()
        mail.logout()
        logger.info("Connection closed")

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error for {checker_config['monitor_email']}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing email: {str(e)}", exc_info=True)


def check_tasks(checker_config):
    """Check and execute scheduled tasks for a checker.

    Args:
        checker_config: Configuration dictionary for the checker
    """
    if not checker_config.get("enable_tasks", False):
        return

    tasks = checker_config.get("tasks", [])
    if not tasks:
        return

    logger.info(f"Checking tasks for checker {checker_config.get('name', 'unknown')}")
    for task in tasks:
        try:
            # Support both old (name) and new (title) task formats
            task_name = task.get("title", task.get("name", "Untitled Task"))

            if TaskManager.should_run_task(task):
                logger.info(f"Executing task: {task_name}")
                if TaskManager.execute_task(checker_config, task):
                    logger.info(f"Successfully executed task: {task_name}")
                else:
                    logger.error(f"Failed to execute task: {task_name}")
        except Exception as e:
            logger.error(f"Error checking task: {str(e)}")


def main():
    """Check emails and execute tasks for all enabled checkers."""
    logger.info("Starting email check and task execution...")
    config = load_config()
    if not config:
        logger.info("No configuration found")
        return

    for checker in config.get("checkers", []):
        if checker.get("enabled"):
            logger.info(f"Checking {checker['monitor_email']}...")
            # TODO: Add asyncio support for parallel email checking
            # TODO: add validation for chekers for the same email
            check_emails(checker)
            # Check tasks if task execution is enabled
            check_tasks(checker)


def init_scheduler():
    """Initialize the scheduler for email checking and task execution."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(main, "interval", minutes=1)
    scheduler.start()
    return scheduler


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        logger.info("Running single check...")
        main()
        logger.info("Single check completed")
    else:
        logger.info("Starting scheduler...")
        scheduler = init_scheduler()
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
