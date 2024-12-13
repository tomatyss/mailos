"""Email reply handling and processing module.

This module contains functions for handling email replies, including:
- Creating prompts for LLM responses
- Processing email attachments
- Sending automated replies using configured LLM providers
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from mailos.tools import TOOL_MAP
from mailos.utils.config_utils import get_attachment_settings
from mailos.utils.email_utils import send_email
from mailos.utils.logger_utils import logger
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory
from mailos.vendors.models import Content, ContentType, Message, RoleType

# Constants
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
DEFAULT_SMTP_PORT = 465  # Standard SSL port for SMTP


@dataclass
class EmailData:
    """Structure for validated email data."""

    sender: str
    subject: str
    body: str = ""
    msg_date: str = ""
    message_id: str = ""
    attachments: List[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailData":
        """Create EmailData instance from dictionary."""
        return cls(
            sender=data["from"],
            subject=data["subject"],
            body=data.get("body", ""),
            msg_date=data.get("msg_date", ""),
            message_id=data.get("message_id", ""),
            attachments=data.get("attachments", []),
        )


def create_email_prompt(
    email_data: EmailData, available_tools: List[Any], has_images: bool = False
) -> str:
    """Create a prompt for the LLM based on the email data.

    Args:
        email_data: Structured email data
        available_tools: List of available tools for the LLM
        has_images: Whether the email contains image attachments

    Returns:
        Formatted prompt string for the LLM
    """
    tools_description = ""
    if available_tools:
        tools_description = (
            "You have access to the following tools:\n"
            + "\n".join(
                f"- {tool.name}: {tool.description}" for tool in available_tools
            )
            + f"\n\nIMPORTANT: When using tools that create files (like create_pdf), "
            f"you MUST use the sender's email address ({email_data.sender}) as the "
            f"sender_email parameter. This ensures files are saved in the correct "
            f"directory and will be properly attached to your response email."
        )

    attachment_context = _build_attachment_context(email_data.attachments or [])

    return f"""
Context: You are responding to an email. Here are the details:{attachment_context}

From: {email_data.sender}
Subject: {email_data.subject}
Message: {email_data.body}

{tools_description}

Please compose a professional and helpful response. Keep your response concise and
relevant. Your response will be followed by the original message, so you don't need
to quote it.
"""


def _build_attachment_context(attachments: List[Dict[str, Any]]) -> str:
    """Build context string for email attachments.

    Args:
        attachments: List of attachment dictionaries

    Returns:
        Formatted attachment context string
    """
    if not attachments:
        return ""

    context_parts = []
    image_count = sum(1 for att in attachments if att["type"].startswith("image/"))
    pdf_paths = [
        {"name": att["original_name"], "path": att["path"]}
        for att in attachments
        if att["type"] == "application/pdf"
    ]

    if image_count:
        context_parts.append(
            f"\nThis email contains {image_count} image attachments which "
            "I've included for your analysis. Please examine them and "
            "incorporate relevant details in your response."
        )

    if pdf_paths:
        settings = get_attachment_settings()
        pdf_context = (
            f"\nThis email contains {len(pdf_paths)} PDF attachments stored in "
            f"the {settings['base_storage_path']} directory. You can use the "
            "PDF tools to work with these files at the following paths:\n"
        )
        pdf_context += "\n".join(f"- {pdf['name']}: {pdf['path']}" for pdf in pdf_paths)
        context_parts.append(pdf_context)

    return "".join(context_parts)


def process_attachments(attachments: List[Dict[str, Any]]) -> List[Content]:
    """Process email attachments and convert images to Content objects.

    Args:
        attachments: List of attachment dictionaries

    Returns:
        List of Content objects for valid images
    """
    image_contents = []
    logger.debug(f"Processing {len(attachments)} attachments")

    for attachment in attachments:
        logger.debug(
            f"Checking attachment: {attachment['original_name']} "
            f"(type: {attachment['type']})"
        )

        if attachment["type"] not in SUPPORTED_IMAGE_TYPES:
            logger.debug(
                f"Skipping unsupported type {attachment['type']}. "
                f"Supported types: {SUPPORTED_IMAGE_TYPES}"
            )
            continue

        try:
            with open(attachment["path"], "rb") as f:
                image_data = f.read()
                logger.debug(
                    f"Read {len(image_data)} bytes from {attachment['original_name']}"
                )

            image_contents.append(
                Content(
                    type=ContentType.IMAGE,
                    data=image_data,
                    mime_type=attachment["type"],
                )
            )
            logger.info(
                f"Successfully processed image: {attachment['original_name']} "
                f"({len(image_data)} bytes, type: {attachment['type']})"
            )
        except Exception as e:
            logger.error(
                f"Failed to process image {attachment['original_name']}: {str(e)}",
                exc_info=True,
            )

    logger.debug(f"Processed {len(image_contents)} valid images")
    return image_contents


def _initialize_llm(checker_config: Dict[str, Any]):
    """Initialize LLM with appropriate configuration.

    Args:
        checker_config: Configuration dictionary for the checker

    Returns:
        Initialized LLM instance or None if initialization fails
    """
    llm_args = {
        "provider": checker_config["llm_provider"],
        "model": checker_config["model"],
    }

    vendor_config = VENDOR_CONFIGS.get(checker_config["llm_provider"])
    if not vendor_config:
        logger.error(f"Unknown LLM provider: {checker_config['llm_provider']}")
        return None

    for field in vendor_config.fields:
        field_name = "aws_region" if field.name == "region" else field.name

        if field_name in checker_config:
            llm_args[field_name] = checker_config[field_name]
        elif field.required:
            logger.error(
                f"Missing required field '{field_name}' for {vendor_config.name}"
            )
            return None
        elif field.default is not None:
            llm_args[field_name] = field.default

    return LLMFactory.create(**llm_args)


def handle_email_reply(
    checker_config: Dict[str, Any], email_data: Dict[str, Any]
) -> bool:
    """Handle the email reply process using the configured LLM.

    Args:
        checker_config: Configuration for the email checker
        email_data: Dictionary containing email information

    Returns:
        bool: True if reply was sent successfully, False otherwise
    """
    if not checker_config.get("auto_reply", False):
        logger.debug("Auto-reply is disabled for this checker")
        return False

    try:
        # Validate and structure email data
        try:
            structured_email = EmailData.from_dict(email_data)
        except KeyError as e:
            logger.error(f"Missing required email field: {e}")
            logger.debug(f"Email data received: {email_data}")
            return False

        # Initialize LLM
        llm = _initialize_llm(checker_config)
        if not llm or not hasattr(llm, "generate_sync"):
            logger.error("Failed to initialize LLM or sync generation not supported")
            return False

        # Process attachments - always try to include images
        image_contents: List[Content] = []
        if structured_email.attachments:
            logger.debug(
                f"Found {len(structured_email.attachments)} attachments in email"
            )
            image_contents = process_attachments(structured_email.attachments)
            if image_contents:
                logger.info(f"Processing {len(image_contents)} images")
            else:
                logger.debug("No valid images found in attachments")

        # Setup enabled tools
        enabled_tools = [
            TOOL_MAP[tool_name]
            for tool_name in checker_config.get("enabled_tools", [])
            if tool_name in TOOL_MAP
        ]

        # Prepare message content
        message_content = [
            Content(
                type=ContentType.TEXT,
                data=create_email_prompt(
                    structured_email, enabled_tools, bool(image_contents)
                ),
            )
        ]
        if image_contents:
            logger.debug(
                f"Adding {len(image_contents)} images to message content "
                f"for {checker_config['llm_provider']}"
            )
            message_content.extend(image_contents)

        # Generate response
        messages = [
            Message(
                role=RoleType.SYSTEM,
                content=[
                    Content(
                        type=ContentType.TEXT,
                        data=checker_config.get(
                            "system_prompt", "You are a helpful email assistant."
                        ),
                    )
                ],
            ),
            Message(role=RoleType.USER, content=message_content),
        ]

        logger.debug(
            f"Sending request to {checker_config['llm_provider']} with "
            f"{len(messages)} messages ({len(message_content)} content items "
            f"in user message)"
        )

        response = llm.generate_sync(
            messages=messages,
            stream=False,
            tools=enabled_tools,
        )

        if not response or not response.content:
            logger.error("Empty response from LLM")
            return False

        # Send email reply
        smtp_server = checker_config["imap_server"].replace("imap", "smtp")
        success = send_email(
            smtp_server=smtp_server,
            smtp_port=DEFAULT_SMTP_PORT,
            sender_email=checker_config["monitor_email"],
            password=checker_config["password"],
            recipient=structured_email.sender,
            subject=structured_email.subject,
            body=response.content[0].data,
            email_data=email_data,
        )

        if success:
            logger.info(f"Successfully sent AI reply to {structured_email.sender}")
            return True
        else:
            logger.error("Failed to send AI reply")
            return False

    except Exception as e:
        logger.error(f"Error in handle_email_reply: {str(e)}", exc_info=True)
        return False
