from typing import AsyncIterator, List, Union
import anthropic

from utils.logger_utils import setup_logger
from .base import BaseLLM
from .models import Message, Content, RoleType, ContentType
import asyncio

logger = setup_logger('anthropic_llm')

class AnthropicLLM(BaseLLM):
    """Anthropic implementation of the LLM interface using direct API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        **kwargs
    ):
        # Set defaults only for missing values
        config = {
            'max_tokens': kwargs.get('max_tokens', 4096),
            'temperature': kwargs.get('temperature', 0.5),
            'top_p': kwargs.get('top_p', 1.0),
            'frequency_penalty': kwargs.get('frequency_penalty', 0.0),
            'presence_penalty': kwargs.get('presence_penalty', 0.0)
        }
        
        super().__init__(api_key, model, **config)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _format_messages(self, messages: List[Message]) -> tuple[str, List[dict]]:
        """Convert our Message objects to Anthropic format and extract system prompt."""
        formatted = []
        system_prompt = None

        for msg in messages:
            # Extract system message
            if msg.role == RoleType.SYSTEM:
                system_prompt = msg.content[0].data
                continue

            # Only include user and assistant messages
            if msg.role not in [RoleType.USER, RoleType.ASSISTANT]:
                continue

            content = []
            for c in msg.content:
                if c.type == ContentType.TEXT:
                    content.append({
                        "type": "text",
                        "text": c.data
                    })
                elif c.type == ContentType.IMAGE:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": c.mime_type or "image/jpeg",
                            "data": c.data
                        }
                    })

            formatted.append({
                "role": msg.role.value,
                "content": content
            })

        return system_prompt, formatted

    async def generate(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> Union[Message, AsyncIterator[Message]]:
        """Generate a response using Anthropic's API."""

        system_prompt, formatted_messages = self._format_messages(messages)

        try:
            kwargs = {
                "model": self.model,
                "messages": formatted_messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # Only add system if it exists
            if system_prompt:
                kwargs["system"] = system_prompt

            if stream:
                stream_response = await self.client.messages.create(
                    **kwargs,
                    stream=True
                )

                async def response_generator():
                    async for chunk in stream_response:
                        if chunk.delta.text:
                            yield Message(
                                role=RoleType.ASSISTANT,
                                content=[Content(
                                    type=ContentType.TEXT,
                                    data=chunk.delta.text
                                )]
                            )
                return response_generator()

            response = await self.client.messages.create(**kwargs)

            return Message(
                role=RoleType.ASSISTANT,
                content=[Content(
                    type=ContentType.TEXT,
                    data=response.content[0].text
                )]
            )

        except anthropic.RateLimitError:
            await self.handle_rate_limit()
            return await self.generate(messages, stream)

    async def generate_embedding(
        self,
        content: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using Anthropic's API."""
        raise NotImplementedError(
            "Anthropic does not currently support embeddings")

    async def process_image(
        self,
        image_data: bytes,
        prompt: str
    ) -> Message:
        """Process an image with Claude."""
        messages = [
            Message(
                role=RoleType.USER,
                content=[
                    Content(type=ContentType.IMAGE, data=image_data),
                    Content(type=ContentType.TEXT, data=prompt)
                ]
            )
        ]
        return await self.generate(messages)

    async def transcribe_audio(
        self,
        audio_data: bytes
    ) -> str:
        """Transcribe audio to text."""
        raise NotImplementedError(
            "Anthropic does not currently support audio transcription")

    async def handle_rate_limit(self) -> None:
        """Handle Anthropic rate limiting."""
        await asyncio.sleep(20)

    def generate_sync(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> Message:
        """Synchronous wrapper for generate method."""
        if stream:
            raise ValueError("Streaming is not supported in synchronous mode")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate(messages, stream=False))
        finally:
            loop.close()
