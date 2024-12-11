"""Email reply functions."""

from mailos.tools import TOOL_MAP
from mailos.utils.email_utils import send_email
from mailos.utils.logger_utils import setup_logger
from mailos.vendors.config import VENDOR_CONFIGS
from mailos.vendors.factory import LLMFactory
from mailos.vendors.models import Content, Message, RoleType

logger = setup_logger("reply")


def create_email_prompt(email_data, available_tools):
    """Create a prompt for the LLM based on the email data."""
    tools_description = ""
    if available_tools:
        tools_description = "You have access to the following tools:\n"
        for tool in available_tools:
            tools_description += f"- {tool.name}: {tool.description}\n"

    return f"""
Context: You are responding to an email. Here are the details:

From: {email_data['from']}
Subject: {email_data['subject']}
Message: {email_data['body']}

{tools_description}

Please compose a professional and helpful response. Keep your response concise and
relevant. Your response will be followed by the original message, so you don't need
to quote it.
"""


def handle_email_reply(checker_config, email_data):
    """Handle the email reply process using the configured LLM."""
    # Only require the essential fields
    required_fields = ["from", "subject"]  # These are the minimum required fields
    optional_fields = ["body", "msg_date", "message_id"]

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
            email_data[field] = ""
            logger.warning(f"Missing optional field '{field}', using empty string")

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

        # Get enabled tools for this checker
        enabled_tools = []
        if "enabled_tools" in checker_config:
            for tool_name in checker_config["enabled_tools"]:
                if tool_name in TOOL_MAP:
                    enabled_tools.append(TOOL_MAP[tool_name])
                    logger.debug(f"Added tool: {tool_name}")
                else:
                    logger.warning(f"Unknown tool: {tool_name}")

        # Create the messages list with available tools
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
                content=[
                    Content(
                        type="text", data=create_email_prompt(email_data, enabled_tools)
                    )
                ],
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
