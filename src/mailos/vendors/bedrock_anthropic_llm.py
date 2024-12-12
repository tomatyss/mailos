"""AWS Bedrock implementation of the LLM interface."""

import base64
import json
from io import BytesIO
from typing import Any, AsyncIterator, Dict, List, Optional

import boto3
from PIL import Image

from mailos.utils.logger_utils import logger
from mailos.vendors.base import BaseLLM
from mailos.vendors.models import (
    Content,
    ContentType,
    LLMResponse,
    Message,
    RoleType,
    Tool,
)

# Supported image formats and max size (10MB)
SUPPORTED_IMAGE_FORMATS = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
MAX_IMAGE_DIMENSION = 4096  # Maximum dimension allowed by Claude


class BedrockAnthropicLLM(BaseLLM):
    """Anthropic implementation using AWS Bedrock."""

    def __init__(
        self,
        aws_access_key: str,
        aws_secret_key: str,
        aws_session_token: str = None,
        aws_region: str = "us-east-1",
        model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        **kwargs,
    ):
        """Initialize BedrockAnthropicLLM instance."""
        super().__init__(None, model, **kwargs)
        self.aws_region = aws_region
        self.aws_credentials = {
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
            "region_name": aws_region,
        }
        if aws_session_token:
            self.aws_credentials["aws_session_token"] = aws_session_token

        self.session = boto3.Session(**self.aws_credentials)
        self.client = self.session.client(
            service_name="bedrock-runtime",
            region_name=self.aws_region,
        )

    def _process_image(
        self, image_data: bytes, mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process and validate image data for Claude.

        Args:
            image_data: Raw image data
            mime_type: MIME type of the image (optional)

        Returns:
            Dictionary containing processed image data and metadata

        Raises:
            ValueError: If image validation fails
        """
        try:
            # Validate MIME type first
            if mime_type and mime_type not in SUPPORTED_IMAGE_FORMATS:
                raise ValueError(f"Unsupported image format: {mime_type}")

            # Check file size before attempting to open image
            if len(image_data) > MAX_IMAGE_SIZE:
                raise ValueError(
                    f"Image size exceeds maximum allowed size of "
                    f"{MAX_IMAGE_SIZE / 1024 / 1024}MB"
                )

            # Open and validate image
            img = Image.open(BytesIO(image_data))

            # Set MIME type if not provided
            if mime_type is None:
                mime_type = f"image/{img.format.lower()}"
                if mime_type not in SUPPORTED_IMAGE_FORMATS:
                    raise ValueError(f"Unsupported image format: {mime_type}")

            # Check dimensions
            if max(img.size) > MAX_IMAGE_DIMENSION:
                # Resize image while maintaining aspect ratio
                ratio = MAX_IMAGE_DIMENSION / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Convert back to bytes
                buffer = BytesIO()
                img.save(buffer, format=img.format or "PNG")
                buffer.seek(0)
                image_data = buffer.getvalue()

            # Convert to base64
            base64_image = base64.b64encode(image_data).decode("utf-8")

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64_image,
                },
            }

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")

    def _format_tools(self, tools: Optional[List[Tool]] = None) -> List[dict]:
        """Format tools into Anthropic's format."""
        if not tools:
            return []

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters.get("properties", {}),
                    "required": tool.required_params or [],
                },
            }
            for tool in tools
        ]

    def _format_messages(
        self, messages: List[Message], tools: Optional[List[Tool]] = None
    ) -> Dict[str, Any]:
        """Format messages into Claude format."""
        formatted_messages = []
        system = None

        for msg in messages:
            if msg.role == RoleType.SYSTEM:
                system = next(
                    (c.data for c in msg.content if c.type == ContentType.TEXT), None
                )
                continue

            content = []
            for c in msg.content:
                if c.type == ContentType.TEXT:
                    content.append({"type": "text", "text": c.data})
                elif c.type == ContentType.IMAGE:
                    try:
                        content.append(self._process_image(c.data, c.mime_type))
                    except ValueError as e:
                        logger.warning(f"Skipping invalid image: {str(e)}")
                        continue

            if content:  # Only add message if it has valid content
                formatted_messages.append({"role": msg.role.value, "content": content})

        return {"messages": formatted_messages, "system": system}

    async def _make_request(
        self, messages: Dict[str, Any], tools: List[dict] = None, stream: bool = False
    ) -> Any:
        """Make request to Bedrock."""
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_tokens or 4096,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "messages": messages["messages"],
        }

        if messages["system"]:
            request_body["system"] = messages["system"]

        if tools:
            request_body["tools"] = tools

        if stream:
            return self.client.invoke_model_with_response_stream(
                modelId=self.model, body=json.dumps(request_body)
            )

        try:
            response = self.client.invoke_model(
                modelId=self.model, body=json.dumps(request_body)
            )
            return json.loads(response["body"].read().decode())
        except Exception as e:
            logger.error(
                f"Request body that caused error: {json.dumps(request_body, indent=2)}"
            )
            raise e

    def _create_response(
        self, raw_response: Dict, tool_calls: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """Create LLMResponse from Bedrock response."""
        return LLMResponse(
            content=[
                Content(type=ContentType.TEXT, data=block["text"])
                for block in raw_response.get("content", [])
                if block["type"] == "text"
            ],
            model=self.model,
            finish_reason=raw_response.get("stop_reason"),
            usage=raw_response.get("usage"),
            tool_calls=tool_calls,
        )

    def _extract_tool_calls(self, raw_response: Dict) -> List[Dict]:
        """Extract tool calls from Bedrock response."""
        tool_calls = []
        for block in raw_response.get("content", []):
            if block["type"] == "tool_use":
                tool_calls.append(
                    {"id": block["id"], "name": block["name"], "input": block["input"]}
                )
        return tool_calls

    def _has_tool_calls(self, raw_response: Dict) -> bool:
        """Check if response contains tool calls."""
        return raw_response.get("stop_reason") == "tool_use"

    def _format_tool_results(
        self, raw_response: Dict, tool_results: List[Dict]
    ) -> Dict[str, Any]:
        """Format tool results for next request."""
        messages = raw_response.get("messages", [])

        # Add the assistant's response with tool uses
        messages.append({"role": "assistant", "content": raw_response["content"]})

        # Add tool results as a user message with proper tool_result blocks
        tool_result_content = []
        for result in tool_results:
            tool_result_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": result["tool_use_id"],
                    "content": result["content"],
                }
            )

        messages.append({"role": "user", "content": tool_result_content})

        return {"messages": messages, "system": raw_response.get("system")}

    async def _stream_response(self, raw_response: Any) -> AsyncIterator[LLMResponse]:
        """Stream response from Bedrock."""
        for event in raw_response["body"]:
            chunk = json.loads(event["chunk"]["bytes"].decode())
            if "content" in chunk:
                yield LLMResponse(
                    content=[Content(type=ContentType.TEXT, data=chunk["content"])],
                    model=self.model,
                )

    async def handle_rate_limit(self) -> None:
        """Handle AWS Bedrock rate limiting."""
        await super().handle_rate_limit()

    async def process_image(self, image_data: bytes, prompt: str) -> LLMResponse:
        """Process an image with Claude.

        Args:
            image_data: Raw image data
            prompt: Text prompt to accompany the image

        Returns:
            LLMResponse containing Claude's analysis
        """
        if "claude-3" not in self.model.lower():
            raise NotImplementedError(
                "Image processing is only supported in Claude 3 models"
            )

        messages = [
            Message(
                role=RoleType.USER,
                content=[
                    Content(type=ContentType.IMAGE, data=image_data),
                    Content(type=ContentType.TEXT, data=prompt),
                ],
            )
        ]
        return await self.generate(messages)
