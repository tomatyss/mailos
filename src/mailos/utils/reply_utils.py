"""Reply utilities for MailOS."""


def should_reply(email_data):
    """Determine if an email should receive an auto-reply."""
    no_reply_indicators = [
        "no-reply",
        "noreply",
        "do-not-reply",
        "automated",
        "notification",
        "mailer-daemon",
        "postmaster",
    ]
    # TODO: add option to set custom no-reply indicators in ui

    sender = email_data["from"].lower()
    subject = email_data["subject"].lower()

    # Don't reply to no-reply addresses
    if any(indicator in sender for indicator in no_reply_indicators):
        return False

    # Don't reply to automated notifications
    if any(indicator in subject for indicator in no_reply_indicators):
        return False

    return True
