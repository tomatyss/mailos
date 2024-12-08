import imaplib
import email
from datetime import datetime
import time
import sys
from mailos.utils.config_utils import load_config, save_config
from apscheduler.schedulers.background import BackgroundScheduler
from mailos.utils.logger_utils import setup_logger
from mailos.reply import handle_email_reply, should_reply

logger = setup_logger('email_checker')

def get_email_body(email_message):
    """Extract the email body from a potentially multipart message."""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode()
                except:
                    return part.get_payload()
    else:
        try:
            return email_message.get_payload(decode=True).decode()
        except:
            return email_message.get_payload()
    return ""

def check_emails(checker_config):
    try:
        logger.info(f"Connecting to {checker_config['imap_server']}...")
        mail = imaplib.IMAP4_SSL(checker_config['imap_server'], checker_config['imap_port'])
        mail.login(checker_config['monitor_email'], checker_config['password'])
        
        logger.info("Connected successfully")
        
        # Select inbox
        status, messages = mail.select('INBOX')
        logger.info(f"Inbox select status: {status}")
        
        # Search for unread emails
        logger.info("Searching for unread emails...")
        result, data = mail.search(None, 'UNSEEN')
        
        if result == 'OK':
            if not data[0]:
                logger.info("No unread emails found")
            else:
                email_ids = data[0].split()
                logger.info(f"Found {len(email_ids)} unread emails")
                
                for num in email_ids:
                    result, email_data = mail.fetch(num, '(RFC822)')
                    if result == 'OK':
                        email_body = email_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        # Create a properly formatted email_data dictionary
                        parsed_email = {
                            'from': email_message['from'],
                            'subject': email_message['subject'],
                            'body': get_email_body(email_message),
                            'msg_date': email_message['date'],
                            'message_id': email_message['message-id'] or f"generated-{num.decode()}"
                        }
                        
                        logger.info(
                            f"New email found: Subject='{parsed_email['subject']}' "
                            f"From='{parsed_email['from']}'"
                        )
                        
                        # Optionally mark as read after processing
                        mail.store(num, '+FLAGS', '\\Seen')
                        
                        if checker_config.get('auto_reply', False) and should_reply(parsed_email):
                            handle_email_reply(checker_config, parsed_email)
                    else:
                        logger.error(f"Failed to fetch email {num}: {result}")
        else:
            logger.error(f"Search failed: {result}")
                
        # Update last_run timestamp
        checker_config['last_run'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        mail.close()
        mail.logout()
        logger.info("Connection closed")
        
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error for {checker_config['monitor_email']}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error checking {checker_config['monitor_email']}: {str(e)}")

def main():
    logger.info("Starting email check...")
    config = load_config()
    if not config:
        logger.info("No configuration found")
        return
        
    modified = False
    for checker in config.get('checkers', []):
        if checker.get('enabled'):
            logger.info(f"Checking {checker['monitor_email']}...")
            check_emails(checker)
            modified = True
    
    if modified:
        logger.info("Saving updated configuration...")
        save_config(config)
    else:
        logger.info("No enabled email checkers found")

def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(main, 'interval', minutes=1)
    scheduler.start()
    return scheduler

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
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