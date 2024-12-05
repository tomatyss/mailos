from typing import AsyncIterator, List, Union, Optional
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
        model: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        region: str = "us-east-1",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.region = region
        self.session = aioboto3.Session()
        
    def _format_prompt(self, messages: List[Message]) -> str:
        """Format messages into Claude prompt format."""
        formatted = []
        
        for msg in messages:
            if msg.role == RoleType.SYSTEM:
                formatted.append(f"System: {msg.content[0].data}")
            elif msg.role == RoleType.USER:
                formatted.append(f"Human: {msg.content[0].data}")
            elif msg.role == RoleType.ASSISTANT:
                formatted.append(f"Assistant: {msg.content[0].data}")
                
        return "\n\n".join(formatted) + "\n\nAssistant:"

    async def generate(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> Union[Message, AsyncIterator[Message]]:
        """Generate a response using Bedrock."""
        
        prompt = self._format_prompt(messages)
        
        request_body = {
            "prompt": prompt,
            "max_tokens_to_sample": self.config.max_tokens or 4096,
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