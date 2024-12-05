from typing import AsyncIterator, List, Union
import json
import asyncio
import aioboto3
from .base import BaseLLM
from .models import Message, Content, RoleType, ContentType

class BedrockAnthropicLLM(BaseLLM):
    """Anthropic implementation using AWS Bedrock."""
    
    def __init__(
        self,
        api_key: str,  # AWS credentials
        model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-east-1",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.region = region
        self.session = aioboto3.Session()
        
    def _format_messages(self, messages: List[Message]) -> tuple[str, List[dict]]:
        """Format messages into Claude format and extract system prompt."""
        formatted = []
        system_prompt = None
        
        for msg in messages:
            if msg.role == RoleType.SYSTEM:
                system_prompt = msg.content[0].data
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
        """Generate a response using Bedrock."""
        
        system_prompt, formatted_messages = self._format_messages(messages)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "system": system_prompt,
            "messages": formatted_messages,
            "max_tokens": self.config.max_tokens or 4096,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }
        
        try:
            async with self.session.client(
                service_name='bedrock-runtime',
                region_name=self.region
            ) as bedrock:
                
                if stream:
                    response = await bedrock.invoke_model_with_response_stream(
                        modelId=self.model,
                        body=json.dumps(request_body)
                    )
                    
                    async def response_generator():
                        async for event in response['body']:
                            chunk = json.loads(event['chunk']['bytes'].decode())
                            if chunk['completion']:
                                yield Message(
                                    role=RoleType.ASSISTANT,
                                    content=[Content(
                                        type=ContentType.TEXT,
                                        data=chunk['completion']
                                    )]
                                )
                    return response_generator()
                
                response = await bedrock.invoke_model(
                    modelId=self.model,
                    body=json.dumps(request_body)
                )
                
                response_body = json.loads(response['body'].read())
                
                return Message(
                    role=RoleType.ASSISTANT,
                    content=[Content(
                        type=ContentType.TEXT,
                        data=response_body['completion']
                    )]
                )
                
        except Exception as e:
            if "ThrottlingException" in str(e):
                await self.handle_rate_limit()
                return await self.generate(messages, stream)
            raise e

    async def generate_embedding(
        self,
        content: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings (not supported in Bedrock)."""
        raise NotImplementedError("Bedrock does not support embeddings for Anthropic models")

    async def process_image(
        self,
        image_data: bytes,
        prompt: str
    ) -> Message:
        """Process an image (if supported by the model version)."""
        if "claude-3" not in self.model.lower():
            raise NotImplementedError("Image processing is only supported in Claude 3 models")
            
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
        """Transcribe audio (not supported)."""
        raise NotImplementedError("Bedrock does not support audio transcription for Anthropic models")

    async def handle_rate_limit(self) -> None:
        """Handle AWS Bedrock rate limiting."""
        await asyncio.sleep(1)  # AWS has different rate limiting patterns 