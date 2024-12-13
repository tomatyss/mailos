"""Base class for LLM vendors."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from mailos.utils.logger_utils import setup_logger

from .models import Content, LLMResponse, Message, ModelConfig, Tool

logger = setup_logger("llm")


class BaseLLM(ABC):
    """Abstract base class for LLM vendors."""

    def __init__(self, api_key: str, model: str, max_tool_calls: int = 73, **kwargs):
        """Initialize BaseLLM instance."""
        self.api_key = api_key
        self.model = model
        self.config = ModelConfig(**kwargs)
        self.tools: Dict[str, Tool] = {}
        self.history: List[Message] = []
        self.max_tool_calls = max_tool_calls

    @abstractmethod
    def _format_messages(
        self, messages: List[Message], tools: Optional[List[Tool]] = None
    ) -> Any:
        """Format messages into vendor-specific format.

        Args:
            messages: List of messages to format
            tools: Optional list of tools to include

        Returns:
            Formatted messages in vendor-specific format
        """
        pass

    @abstractmethod
    def _format_tools(self, tools: Optional[List[Tool]] = None) -> Any:
        """Format tools into vendor-specific format.

        Args:
            tools: Optional list of tools to format

        Returns:
            Formatted tools in vendor-specific format
        """
        pass

    @abstractmethod
    async def _make_request(
        self, messages: Any, tools: Any = None, stream: bool = False
    ) -> Any:
        """Make request to vendor API.

        Args:
            messages: Formatted messages
            tools: Formatted tools
            stream: Whether to stream the response

        Returns:
            Raw vendor response
        """
        pass

    @abstractmethod
    def _create_response(
        self, raw_response: Any, tool_calls: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """Create LLMResponse from vendor response.

        Args:
            raw_response: Raw vendor response
            tool_calls: Optional list of tool calls made

        Returns:
            Unified LLMResponse object
        """
        pass

    async def _execute_tool(
        self, tool_call: Dict[str, Any], available_tools: List[Tool]
    ) -> Dict[str, Any]:
        """Execute a tool and format its result.

        Args:
            tool_call: Tool call details including name and either input or arguments
            available_tools: List of available tools

        Returns:
            Formatted tool result
        """
        tool_name = tool_call["name"]
        # Handle both input and arguments keys for different vendor implementations
        tool_input = tool_call.get("input") or tool_call.get("arguments", {})
        tool_id = tool_call["id"]

        # Find the matching tool
        tool = next((t for t in available_tools if t.name == tool_name), None)
        if not tool:
            logger.error(f"Tool {tool_name} not found")
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Error: Tool {tool_name} not found",
                "is_error": True,
            }

        try:
            # Execute the tool
            result = await asyncio.to_thread(tool.function, **tool_input)
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": str(result),  # Ensure result is string
            }
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            logger.error(error_msg)
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": error_msg,
                "is_error": True,
            }

    async def _process_response(
        self, raw_response: Any, tools: List[Tool], tool_call_count: int = 0
    ) -> LLMResponse:
        """Process a response, handling any tool uses recursively.

        Args:
            raw_response: Raw vendor response
            tools: List of available tools
            tool_call_count: Current number of tool calls made

        Returns:
            Processed LLMResponse
        """
        # Check if we've exceeded the maximum number of tool calls
        if tool_call_count >= self.max_tool_calls:
            logger.warning(f"Exceeded maximum tool calls ({self.max_tool_calls})")
            return LLMResponse(
                content=[
                    Content(
                        type="text",
                        data=(
                            f"Error: Exceeded maximum number of tool calls "
                            f"({self.max_tool_calls})"
                        ),
                    )
                ],
                model=self.model,
                finish_reason="max_tools_exceeded",
            )

        # Extract tool calls from response (vendor-specific implementation)
        tool_calls = self._extract_tool_calls(raw_response)
        if not tool_calls:
            return self._create_response(raw_response)

        # Execute all tools and collect results
        tool_results = []

        for tool_call in tool_calls:
            result = await self._execute_tool(tool_call, tools)
            tool_results.append(result)
            if result.get("is_error"):
                logger.error(f"Tool execution error: {result['content']}")

        # Format and make next request with tool results
        messages = self._format_tool_results(raw_response, tool_results)
        tools_format = self._format_tools(tools)

        new_response = await self._make_request(messages, tools_format)

        # Check if new response has tool calls
        if self._has_tool_calls(new_response):
            return await self._process_response(
                new_response, tools, tool_call_count + 1
            )

        # Return final response
        return self._create_response(new_response, tool_calls)

    @abstractmethod
    def _extract_tool_calls(self, raw_response: Any) -> List[Dict]:
        """Extract tool calls from vendor response.

        Args:
            raw_response: Raw vendor response

        Returns:
            List of tool calls
        """
        pass

    @abstractmethod
    def _has_tool_calls(self, raw_response: Any) -> bool:
        """Check if response contains tool calls.

        Args:
            raw_response: Raw vendor response

        Returns:
            True if response contains tool calls
        """
        pass

    @abstractmethod
    def _format_tool_results(self, raw_response: Any, tool_results: List[Dict]) -> Any:
        """Format tool results for next request.

        Args:
            raw_response: Previous raw response
            tool_results: List of tool results

        Returns:
            Formatted messages with tool results
        """
        pass

    async def generate(
        self,
        messages: List[Message],
        stream: bool = False,
        tools: Optional[List[Tool]] = None,
    ) -> Union[LLMResponse, AsyncIterator[LLMResponse]]:
        """Generate a response from the model.

        Args:
            messages: List of messages
            stream: Whether to stream the response
            tools: Optional list of tools to use

        Returns:
            Model response
        """
        try:
            formatted_messages = self._format_messages(messages, tools)
            formatted_tools = self._format_tools(tools)

            raw_response = await self._make_request(
                formatted_messages, formatted_tools, stream
            )

            if stream:
                return self._stream_response(raw_response)

            return await self._process_response(raw_response, tools or [])

        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            raise

    @abstractmethod
    async def _stream_response(self, raw_response: Any) -> AsyncIterator[LLMResponse]:
        """Stream response from vendor API.

        Args:
            raw_response: Raw streaming response

        Returns:
            AsyncIterator of responses
        """
        pass

    async def generate_embedding(
        self, content: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for the given content."""
        raise NotImplementedError("Embedding generation not supported by this model")

    async def process_image(self, image_data: bytes, prompt: str) -> Message:
        """Process an image with the model."""
        raise NotImplementedError("Image processing not supported by this model")

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio to text."""
        raise NotImplementedError("Audio transcription not supported by this model")

    def register_tool(self, tool: Tool) -> None:
        """Register a tool/function with the model."""
        self.tools[tool.name] = tool

    def add_to_history(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self.history.append(message)

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.history.clear()

    async def handle_rate_limit(self) -> None:
        """Handle rate limiting for the specific vendor."""
        raise NotImplementedError("Rate limit handling not implemented for this model")

    def generate_sync(
        self,
        messages: List[Message],
        stream: bool = False,
        tools: Optional[List[Tool]] = None,
    ) -> LLMResponse:
        """Wrap generate method for synchronous execution."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.generate(messages, stream=stream, tools=tools)
            )
        finally:
            loop.close()
