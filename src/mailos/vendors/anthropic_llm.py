"""Anthropic implementation of the LLM interface."""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

import anthropic

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

logger = setup_logger("anthropic_llm")


class AnthropicLLM(BaseLLM):
    """Anthropic implementation of the LLM interface using direct API."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        """Initialize AnthropicLLM instance."""
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.Anthropic(api_key=api_key)

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
        """Format messages into Anthropic format."""
        formatted_messages = []
        system = None

        for msg in messages:
            if msg.role == RoleType.SYSTEM:
                system = next(
                    (c.data for c in msg.content if c.type == ContentType.TEXT), None
                )
                continue

            if msg.role not in [RoleType.USER, RoleType.ASSISTANT]:
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

            formatted_messages.append({"role": msg.role.value, "content": content})

        return {"messages": formatted_messages, "system": system}

    async def _make_request(
        self, messages: Dict[str, Any], tools: List[dict] = None, stream: bool = False
    ) -> Any:
        """Make request to Anthropic's API."""
        kwargs = {
            "model": self.model,
            "messages": messages["messages"],
            "max_tokens": self.config.max_tokens or 4096,
            "temperature": self.config.temperature,
        }

        if messages["system"]:
            kwargs["system"] = messages["system"]

        if tools:
            kwargs["tools"] = tools

        try:
            if stream:
                return await asyncio.to_thread(
                    self.client.messages.create, **kwargs, stream=True
                )
            return await asyncio.to_thread(self.client.messages.create, **kwargs)
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    def _create_response(
        self, raw_response: Any, tool_calls: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """Create LLMResponse from Anthropic response."""
        return LLMResponse(
            content=[Content(type=ContentType.TEXT, data=raw_response.content[0].text)],
            model=self.model,
            finish_reason=raw_response.stop_reason,
            usage=raw_response.usage,
            tool_calls=tool_calls,
            system_fingerprint=raw_response.id,
        )

    def _extract_tool_calls(self, raw_response: Any) -> List[Dict]:
        """Extract tool calls from Anthropic response."""
        tool_calls = []
        for message in raw_response.content:
            if message.type == "tool_calls":
                for tool_call in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.parameters,
                        }
                    )
        return tool_calls

    def _has_tool_calls(self, raw_response: Any) -> bool:
        """Check if response contains tool calls."""
        return any(message.type == "tool_calls" for message in raw_response.content)

    def _format_tool_results(
        self, raw_response: Any, tool_results: List[Dict]
    ) -> Dict[str, Any]:
        """Format tool results for next request."""
        messages = raw_response.messages

        # Add the assistant's response with tool calls
        messages.append(
            {
                "role": "assistant",
                "content": raw_response.content,
            }
        )

        # Add tool results as a user message
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": str(result)} for result in tool_results
                ],
            }
        )

        return {"messages": messages, "system": raw_response.system}

    async def _stream_response(self, raw_response: Any) -> AsyncIterator[LLMResponse]:
        """Stream response from Anthropic API."""
        async for chunk in raw_response:
            if chunk.delta.text:
                yield LLMResponse(
                    content=[Content(type=ContentType.TEXT, data=chunk.delta.text)],
                    model=self.model,
                )

    async def process_image(self, image_data: bytes, prompt: str) -> LLMResponse:
        """Process an image with Claude."""
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

    def generate_sync(
        self,
        messages: List[Message],
        stream: bool = False,
        tools: Optional[List[Tool]] = None,
    ) -> LLMResponse:
        """Generate response synchronously."""
        if stream:
            raise ValueError("Streaming is not supported in synchronous mode")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.generate(messages, stream=False, tools=tools)
            )
        finally:
            loop.close()

    async def handle_rate_limit(self) -> None:
        """Handle rate limiting by waiting."""
        await asyncio.sleep(60)  # Wait for 60 seconds before retrying
