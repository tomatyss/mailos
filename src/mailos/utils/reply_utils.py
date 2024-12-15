"""Reply utilities for MailOS."""

from mailos.utils.config_utils import load_config
from mailos.utils.logger_utils import logger


def should_reply(email_data):
    """Determine if an email should receive an auto-reply."""
    try:
        config = load_config()
        no_reply_indicators = config.get(
            "no_reply_indicators",
            [
                "no-reply",
                "noreply",
                "do-not-reply",
                "automated",
                "notification",
                "mailer-daemon",
                "postmaster",
            ],
        )  # Default indicators if none in config
    except Exception as e:
        logger.error(f"Error loading no-reply indicators from config: {str(e)}")
        # Fallback to default indicators if config load fails
        no_reply_indicators = [
            "no-reply",
            "noreply",
            "do-not-reply",
            "automated",
            "notification",
            "mailer-daemon",
            "postmaster",
        ]

    sender = email_data["from"].lower()
    subject = email_data["subject"].lower()

    # Don't reply to no-reply addresses
    if any(indicator in sender for indicator in no_reply_indicators):
        logger.debug(f"No reply: sender '{sender}' matches no-reply indicator")
        return False

    # Don't reply to automated notifications
    if any(indicator in subject for indicator in no_reply_indicators):
        logger.debug(f"No reply: subject '{subject}' matches no-reply indicator")
        return False

    return True
