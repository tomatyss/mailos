"""Implement OpenAI interface for LLM operations."""

import asyncio
import base64
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from openai import OpenAI, RateLimitError

from mailos.utils.logger_utils import setup_logger
from mailos.vendors.base import BaseLLM
from mailos.vendors.models import Content, ContentType, LLMResponse, Message, Tool

logger = setup_logger("openai_llm")


class OpenAILLM(BaseLLM):
    """OpenAI implementation of the LLM interface."""

    def __init__(
        self, api_key: str, model: str = "gpt-4o", tool_choice: str = "auto", **kwargs
    ):
        """Initialize OpenAILLM instance."""
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(api_key=api_key)
        self.tool_choice = tool_choice
        logger.info(f"Initialized OpenAI LLM with model: {model}")

    def _format_tools(self, tools: Optional[List[Tool]] = None) -> List[dict]:
        """Format tools into OpenAI's format."""
        if not tools:
            return []

        formatted_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters.get("properties", {}),
                        "required": tool.required_params or [],
                    },
                },
            }
            for tool in tools
        ]

        logger.debug(f"Formatted {len(formatted_tools)} tools for OpenAI")
        return formatted_tools

    def _format_messages(
        self, messages: List[Message], tools: Optional[List[Tool]] = None
    ) -> List[Dict[str, Any]]:
        """Format messages into OpenAI format."""
        formatted_messages = []
        logger.debug(f"Formatting {len(messages)} messages for OpenAI")

        for msg in messages:
            logger.debug(
                f"Processing message with role {msg.role.value} "
                f"and {len(msg.content)} content items"
            )

            message_dict = {"role": msg.role.value}
            content_list = []

            for content in msg.content:
                if content.type == ContentType.TEXT:
                    logger.debug("Adding text content")
                    content_list.append({"type": "text", "text": content.data})
                elif content.type == ContentType.IMAGE:
                    logger.debug(
                        f"Adding image content with mime type: {content.mime_type}"
                    )
                    # Handle both base64 strings and raw bytes
                    if isinstance(content.data, bytes):
                        image_data = base64.b64encode(content.data).decode("utf-8")
                    else:
                        image_data = content.data

                    # Format according to OpenAI's vision API requirements
                    content_list.append(
                        {
                            "type": "image",
                            "image": {
                                "url": (
                                    image_data
                                    if image_data.startswith("data:")
                                    or image_data.startswith("http")
                                    else f"data:{content.mime_type or 'image/jpeg'};base64,{image_data}"  # noqa E501
                                )
                            },
                        }
                    )

            # For single text content in older models, use string format
            if len(content_list) == 1 and content_list[0]["type"] == "text":
                message_dict["content"] = content_list[0]["text"]
            else:
                message_dict["content"] = content_list

            if msg.name:
                message_dict["name"] = msg.name

            if msg.function_call:
                message_dict["function_call"] = msg.function_call

            formatted_messages.append(message_dict)
            logger.debug(f"Added message with {len(content_list)} content items")

        logger.debug(
            "Final formatted messages structure: %s",
            json.dumps(formatted_messages, indent=2),
        )
        return formatted_messages

    def _extract_tool_calls(self, response: Any) -> List[Dict]:
        """Extract tool calls from OpenAI response."""
        if not response.choices[0].message.tool_calls:
            return []

        tool_calls = []
        for tool_call in response.choices[0].message.tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments)
                logger.debug(
                    f"Successfully parsed tool call arguments for "
                    f"{tool_call.function.name}"
                )
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse tool arguments: {tool_call.function.arguments}"
                )
                arguments = tool_call.function.arguments

            tool_calls.append(
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": arguments,
                }
            )

        logger.debug(f"Extracted {len(tool_calls)} tool calls from response")
        return tool_calls

    def _has_tool_calls(self, response: Any) -> bool:
        """Check if response contains tool calls."""
        has_calls = bool(response.choices[0].message.tool_calls)
        logger.debug(f"Response has tool calls: {has_calls}")
        return has_calls

    def _format_tool_results(
        self, raw_response: Any, tool_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Format tool results for next request."""
        messages = []

        # Add the assistant's response with tool calls
        assistant_message = {
            "role": "assistant",
            "content": raw_response.choices[0].message.content,
        }

        # Convert tool calls to serializable format
        if raw_response.choices[0].message.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in raw_response.choices[0].message.tool_calls
            ]

        messages.append(assistant_message)

        # Add tool results
        for result in tool_results:
            messages.append(
                {
                    "role": "tool",
                    "content": result["content"],
                    "tool_call_id": result["tool_use_id"],
                }
            )

        logger.debug(f"Formatted {len(tool_results)} tool results into messages")
        return messages

    async def _make_request(
        self, messages: List[Dict], tools: List[dict] = None, stream: bool = False
    ) -> Any:
        """Make request to OpenAI's API."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": stream,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = self.tool_choice

            # Convert messages to JSON-serializable format for logging
            log_kwargs = kwargs.copy()
            if "messages" in log_kwargs:
                log_kwargs["messages"] = [
                    {k: v for k, v in msg.items() if k != "tool_calls"}
                    for msg in log_kwargs["messages"]
                ]

            logger.debug(
                f"Making OpenAI request with config: {json.dumps(log_kwargs, indent=2)}"
            )

            return await asyncio.to_thread(
                self.client.chat.completions.create, **kwargs
            )
        except RateLimitError:
            logger.warning("Hit rate limit, waiting before retry")
            await self.handle_rate_limit()
            return await self._make_request(messages, tools, stream)
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def _create_response(
        self, raw_response: Any, tool_calls: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """Create LLMResponse from OpenAI response."""
        content = []
        if raw_response.choices[0].message.content:
            content.append(
                Content(
                    type=ContentType.TEXT,
                    data=raw_response.choices[0].message.content,
                )
            )

        response = LLMResponse(
            content=content,
            model=self.model,
            finish_reason=raw_response.choices[0].finish_reason,
            tool_calls=tool_calls or self._extract_tool_calls(raw_response),
            usage=raw_response.usage.model_dump() if raw_response.usage else None,
            system_fingerprint=raw_response.system_fingerprint,
        )

        logger.debug(
            f"Created response with {len(content)} content items "
            f"and {len(response.tool_calls or [])} tool calls"
        )
        return response

    async def _stream_response(self, raw_response: Any) -> AsyncIterator[LLMResponse]:
        """Stream response from OpenAI API."""
        async for chunk in raw_response:
            if chunk.choices[0].delta.content:
                yield LLMResponse(
                    content=[
                        Content(
                            type=ContentType.TEXT,
                            data=chunk.choices[0].delta.content,
                        )
                    ],
                    model=self.model,
                )

    async def generate(
        self,
        messages: List[Message],
        stream: bool = False,
        tools: Optional[List[Tool]] = None,
    ) -> Union[LLMResponse, AsyncIterator[LLMResponse]]:
        """Generate a response using OpenAI's API."""
        logger.info(
            f"Generating response for {len(messages)} messages "
            f"with {len(tools or [])} tools"
        )

        formatted_messages = self._format_messages(messages, tools)
        formatted_tools = self._format_tools(tools)

        raw_response = await self._make_request(
            formatted_messages, formatted_tools, stream
        )

        if stream:
            logger.debug("Starting streaming response")
            return self._stream_response(raw_response)

        # Process tool calls if present
        if tools and self._has_tool_calls(raw_response):
            logger.debug("Processing response with tool calls")
            return await self._process_response(raw_response, tools)

        logger.debug("Creating final response")
        return self._create_response(raw_response)

    async def handle_rate_limit(self) -> None:
        """Handle rate limiting by waiting."""
        logger.info("Handling rate limit - waiting 60 seconds")
        await asyncio.sleep(60)  # Wait for 60 seconds before retrying

    def generate_sync(
        self,
        messages: List[Message],
        stream: bool = False,
        tools: Optional[List[Tool]] = None,
    ) -> LLMResponse:
        """Provide synchronous wrapper for generate()."""
        logger.debug("Starting synchronous generation")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.generate(messages, stream=stream, tools=tools)
            )
        finally:
            loop.close()
