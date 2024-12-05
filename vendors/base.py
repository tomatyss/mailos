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

    @abstractmethod
    async def generate_embedding(
        self, 
        content: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for the given content."""
        pass

    @abstractmethod
    async def process_image(
        self, 
        image_data: bytes,
        prompt: str
    ) -> Message:
        """Process an image with the model."""
        pass

    @abstractmethod
    async def transcribe_audio(
        self, 
        audio_data: bytes
    ) -> str:
        """Transcribe audio to text."""
        pass

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

    @abstractmethod
    async def handle_rate_limit(self) -> None:
        """Handle rate limiting for the specific vendor."""
        pass 