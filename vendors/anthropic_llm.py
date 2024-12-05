from typing import AsyncIterator, List, Union, Optional
import anthropic
import boto3
from .base import BaseLLM
from .models import Message, Content, RoleType, ContentType

class AnthropicLLM(BaseLLM):
    """Anthropic implementation of the LLM interface using direct API."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "claude-3-opus-20240229",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        
    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """Convert our Message objects to Anthropic format."""
        formatted = []
        
        for msg in messages:
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
            
        return formatted

    async def generate(
        self, 
        messages: List[Message],
        stream: bool = False
    ) -> Union[Message, AsyncIterator[Message]]:
        """Generate a response using Anthropic's API."""
        
        formatted_messages = self._format_messages(messages)
        
        try:
            if stream:
                stream_response = await self.client.messages.create(
                    model=self.model,
                    messages=formatted_messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
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
            
            response = await self.client.messages.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
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
        raise NotImplementedError("Anthropic does not currently support embeddings")

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
        raise NotImplementedError("Anthropic does not currently support audio transcription")

    async def handle_rate_limit(self) -> None:
        """Handle Anthropic rate limiting."""
        import asyncio
        await asyncio.sleep(20) 