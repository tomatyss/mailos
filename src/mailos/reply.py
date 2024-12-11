"""Email reply functions."""

from typing import List

from mailos.tools import TOOL_MAP
from mailos.utils.config_utils import get_attachment_settings
from mailos.utils.email_utils import send_email
from mailos.utils.logger_utils import logger
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory
from mailos.vendors.models import Content, ContentType, Message, RoleType


def create_email_prompt(email_data, available_tools, has_images: bool = False):
    """Create a prompt for the LLM based on the email data."""
    tools_description = ""
    if available_tools:
        tools_description = "You have access to the following tools:\n"
        for tool in available_tools:
            tools_description += f"- {tool.name}: {tool.description}\n"

    # Process attachments information
    attachment_context = ""
    pdf_paths = []

    if email_data.get("attachments"):
        image_count = 0
        for attachment in email_data["attachments"]:
            if attachment["type"].startswith("image/"):
                image_count += 1
            elif attachment["type"] == "application/pdf":
                pdf_paths.append(
                    {"name": attachment["original_name"], "path": attachment["path"]}
                )

        # Add context about images if present
        if image_count > 0:
            attachment_context += (
                f"\nThis email contains {image_count} image attachments which "
                "I've included for your analysis. Please examine them and "
                "incorporate relevant details in your response."
            )

        # Add context about PDFs if present
        if pdf_paths:
            # Get storage settings for context
            settings = get_attachment_settings()
            attachment_context += (
                f"\nThis email contains {len(pdf_paths)} PDF attachments stored in "
                f"the {settings['base_storage_path']} directory. You can use the "
                "PDF tools to work with these files at the following paths:\n"
            )
            for pdf in pdf_paths:
                attachment_context += f"- {pdf['name']}: {pdf['path']}\n"

    return f"""
Context: You are responding to an email. Here are the details:{attachment_context}

From: {email_data['from']}
Subject: {email_data['subject']}
Message: {email_data['body']}

{tools_description}

Please compose a professional and helpful response. Keep your response concise and
relevant. Your response will be followed by the original message, so you don't need
to quote it.
"""


def process_attachments(attachments: List[dict]) -> List[Content]:
    """Process email attachments and convert images to Content objects.

    Args:
        attachments: List of attachment dictionaries

    Returns:
        List of Content objects for valid images
    """
    image_contents = []
    supported_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}

    for attachment in attachments:
        if attachment["type"] in supported_types:
            try:
                with open(attachment["path"], "rb") as f:
                    image_data = f.read()

                image_contents.append(
                    Content(
                        type=ContentType.IMAGE,
                        data=image_data,
                        mime_type=attachment["type"],
                    )
                )
                logger.info(
                    f"Successfully processed image: {attachment['original_name']}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to process image {attachment['original_name']}: {e}"
                )

    return image_contents


def handle_email_reply(checker_config, email_data):
    """Handle the email reply process using the configured LLM."""
    # Only require the essential fields
    required_fields = ["from", "subject"]  # These are the minimum required fields
    optional_fields = ["body", "msg_date", "message_id", "attachments"]

    # Check required fields
    missing_fields = [
        field
        for field in required_fields
        if field not in email_data or email_data[field] is None
    ]
    if missing_fields:
        logger.error(f"Missing required email fields: {missing_fields}")
        logger.debug(f"Email data received: {email_data}")
        return False

    # Set defaults for optional fields
    for field in optional_fields:
        if field not in email_data or email_data[field] is None:
            email_data[field] = [] if field == "attachments" else ""
            logger.warning(f"Missing optional field '{field}', using default value")

    if not checker_config.get("auto_reply", False):
        logger.debug("Auto-reply is disabled for this checker")
        return False

    try:
        # Initialize the LLM with appropriate credentials
        llm_args = {
            "provider": checker_config["llm_provider"],
            "model": checker_config["model"],
        }

        # Get vendor configuration
        vendor_config = VENDOR_CONFIGS.get(checker_config["llm_provider"])
        if not vendor_config:
            logger.error(f"Unknown LLM provider: {checker_config['llm_provider']}")
            return False

        # Add vendor-specific credentials based on configuration
        for field in vendor_config.fields:
            field_name = field.name
            # Map 'region' to 'aws_region' for consistency
            if field_name == "region":
                field_name = "aws_region"

            if field_name in checker_config:
                llm_args[field_name] = checker_config[field_name]
            elif field.required:
                logger.error(
                    f"Missing required field '{field_name}' for {vendor_config.name}"
                )
                return False
            elif field.default is not None:
                llm_args[field_name] = field.default

        # Initialize the LLM with the appropriate arguments
        llm = LLMFactory.create(**llm_args)

        if not hasattr(llm, "generate_sync"):
            logger.error(
                f"LLM provider {checker_config['llm_provider']} "
                "does not support synchronous generation"
            )
            return False

        # Process image attachments if present and supported by the model
        image_contents: List[Content] = []
        model_supports_images = any(
            model_prefix in checker_config["model"].lower()
            for model_prefix in ["claude-3", "claude-3-5"]
        )

        if email_data["attachments"] and model_supports_images:
            image_contents = process_attachments(email_data["attachments"])
            if image_contents:
                logger.info(f"Processing {len(image_contents)} images with Claude")

        # Get enabled tools for this checker
        enabled_tools = []
        if "enabled_tools" in checker_config:
            for tool_name in checker_config["enabled_tools"]:
                if tool_name in TOOL_MAP:
                    enabled_tools.append(TOOL_MAP[tool_name])
                    logger.debug(f"Added tool: {tool_name}")
                else:
                    logger.warning(f"Unknown tool: {tool_name}")

        # Create message content list
        message_content = [
            Content(
                type=ContentType.TEXT,
                data=create_email_prompt(
                    email_data, enabled_tools, has_images=bool(image_contents)
                ),
            )
        ]

        # Add image contents if present
        message_content.extend(image_contents)

        # Create the messages list
        messages = [
            Message(
                role=RoleType.SYSTEM,
                content=[
                    Content(
                        type="text",
                        data=checker_config.get(
                            "system_prompt", "You are a helpful email assistant."
                        ),
                    )
                ],
            ),
            Message(
                role=RoleType.USER,
                content=message_content,
            ),
        ]

        logger.debug(f"Messages: {messages}")
        logger.debug(f"Enabled tools: {[tool.name for tool in enabled_tools]}")

        # Get the response from LLM with enabled tools
        response = llm.generate_sync(
            messages=messages,
            stream=False,
            tools=enabled_tools,
        )

        if not response or not response.content:
            logger.error("Empty response from LLM")
            return False

        response_text = response.content[0].data

        # Extract SMTP settings from IMAP settings
        smtp_server = checker_config["imap_server"].replace("imap", "smtp")
        smtp_port = 465  # Standard SSL port for SMTP

        # Send the reply
        success = send_email(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            sender_email=checker_config["monitor_email"],
            password=checker_config["password"],
            recipient=email_data["from"],
            subject=email_data["subject"],
            body=response_text,
            email_data=email_data,
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
