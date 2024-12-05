from abc import ABC, abstractmethod
from typing import (
    AsyncIterator, Dict, List, Optional, Union, Any
)
from .models import Message, Tool, ModelConfig, Content


class BaseLLM(ABC):
    """Abstract base class for LLM vendors."""

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = ModelConfig(**kwargs)
        self.tools: Dict[str, Tool] = {}
        self.history: List[Message] = []

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> Union[Message, AsyncIterator[Message]]:
        """Generate a response from the model."""
        pass

    async def generate_embedding(
        self,
        content: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for the given content."""
        raise NotImplementedError("Embedding generation not supported by this model")

    async def process_image(
        self,
        image_data: bytes,
        prompt: str
    ) -> Message:
        """Process an image with the model."""
        raise NotImplementedError("Image processing not supported by this model")

    async def transcribe_audio(
        self,
        audio_data: bytes
    ) -> str:
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

    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Any:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        tool = self.tools[tool_name]
        result = await tool.function(**kwargs)

        return result

    async def handle_rate_limit(self) -> None:
        """Handle rate limiting for the specific vendor."""
        raise NotImplementedError("Rate limit handling not implemented for this model")
