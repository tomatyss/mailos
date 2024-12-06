import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from vendors.factory import LLMFactory
from utils.logger_utils import setup_logger
from vendors.models import Message, Content, RoleType

logger = setup_logger('email_reply')

def create_email_prompt(email_data):
    """Create a prompt for the LLM based on the email data."""
    return f"""
Context: You are responding to an email. Here are the details:

From: {email_data['from']}
Subject: {email_data['subject']}
Message: {email_data['body']}

Please compose a professional and helpful response. Keep your response concise and relevant.
Your response will be followed by the original message, so you don't need to quote it.
"""

def send_email(smtp_server, smtp_port, sender_email, password, recipient, subject, body, email_data):
    """Send an email using SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = f"Re: {subject}"

        # Combine AI response with quoted original message
        full_message = (
            f"{body}\n\n"
            f"> -------- Original Message --------\n"
            f"> Subject: {email_data['subject']}\n"
            f"> Date: {email_data['msg_date']}\n"
            f"> From: {email_data['from']}\n"
            f"> Message-ID: {email_data['message_id']}\n"
            f">\n"
            f"> {email_data['body'].replace('\n', '\n> ')}"
        )

        msg.attach(MIMEText(full_message, 'plain'))

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, password)
            server.send_message(msg)
            
        logger.info(f"Reply sent successfully to {recipient}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send reply: {str(e)}")
        return False

def handle_email_reply(checker_config, email_data):
    """Handle the email reply process using the configured LLM."""
    if not checker_config.get('auto_reply', False):
        logger.debug("Auto-reply is disabled for this checker")
        return False

    try:
        # Initialize the LLM with appropriate credentials
        llm_args = {
            'provider': checker_config['llm_provider'],
            'model': checker_config['model']
        }
        
        # Add provider-specific credentials
        if checker_config['llm_provider'] == 'bedrock-anthropic':
            llm_args.update({
                'aws_access_key': checker_config['aws_access_key'],
                'aws_secret_key': checker_config['aws_secret_key'],
                'region': checker_config.get('aws_region', 'us-east-1')
            })
            if 'aws_session_token' in checker_config:
                llm_args['aws_session_token'] = checker_config['aws_session_token']
        else:
            llm_args['api_key'] = checker_config['api_key']

        # Initialize the LLM with the appropriate arguments
        llm = LLMFactory.create(**llm_args)

        if not hasattr(llm, 'generate_sync'):
            logger.error(f"LLM provider {checker_config['llm_provider']} does not support synchronous generation")
            return False

        # Create the messages list
        messages = [
            Message(
                role=RoleType.SYSTEM,
                content=[Content(
                    type="text",
                    data=checker_config.get('system_prompt', 'You are a helpful email assistant.')
                )]
            ),
            Message(
                role=RoleType.USER,
                content=[Content(
                    type="text",
                    data=create_email_prompt(email_data)
                )]
            )
        ]
        
        # Get the response from LLM
        response = llm.generate_sync(messages=messages, stream=False)
        
        if not response or not response.content:
            logger.error("Empty response from LLM")
            return False

        response_text = response.content[0].data if isinstance(response.content, list) else response.content.data

        # Extract SMTP settings from IMAP settings
        smtp_server = checker_config['imap_server'].replace('imap', 'smtp')
        smtp_port = 465  # Standard SSL port for SMTP

        # Send the reply
        success = send_email(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            sender_email=checker_config['monitor_email'],
            password=checker_config['password'],
            recipient=email_data['from'],
            subject=email_data['subject'],
            body=response_text,
            email_data=email_data  # Pass the email_data to include in the reply
        )

        if success:
            logger.info(f"Successfully sent AI reply to {email_data['from']}")
            return True
        else:
            logger.error("Failed to send AI reply")
            return False

    except Exception as e:
        logger.error(f"Error in handle_email_reply: {str(e)}")
        return False

def should_reply(email_data):
    """Determine if an email should receive an auto-reply."""
    # Add logic here to determine if an email should get an auto-reply
    # For example, don't reply to no-reply addresses or automated messages
    
    no_reply_indicators = [
        'no-reply',
        'noreply',
        'do-not-reply',
        'automated',
        'notification',
        'mailer-daemon',
        'postmaster'
    ]
    
    sender = email_data['from'].lower()
    subject = email_data['subject'].lower()
    
    # Don't reply to no-reply addresses
    if any(indicator in sender for indicator in no_reply_indicators):
        return False
        
    # Don't reply to automated notifications
    if any(indicator in subject for indicator in no_reply_indicators):
        return False
        
    # Add more conditions as needed
    
    return True
