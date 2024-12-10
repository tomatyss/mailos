"""AWS Bedrock implementation of the LLM interface."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import boto3

from mailos.utils.logger_utils import setup_logger
from mailos.vendors.base import BaseLLM
from mailos.vendors.models import (
    Content,
    ContentType,
    LLMResponse,
    Message,
    RoleType,
    Tool,
)

logger = setup_logger("bedrock_anthropic_llm")


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
                # Extract system prompt from the first text content
                system = next(
                    (c.data for c in msg.content if c.type == ContentType.TEXT), None
                )
                continue

            content = []
            for c in msg.content:
                if c.type == ContentType.TEXT:
                    content.append({"type": "text", "text": c.data})
                elif c.type == ContentType.IMAGE:
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": c.mime_type or "image/jpeg",
                                "data": c.data,
                            },
                        }
                    )

            if content:  # Only add message if it has content
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

        # Only add system if it's present
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

        # Add tool results as a user message
        messages.append({"role": "user", "content": tool_results})

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
        """Process an image (if supported by the model version)."""
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
