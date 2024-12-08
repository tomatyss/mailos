from typing import AsyncIterator, List, Union
import json
import boto3
from mailos.vendors.base import BaseLLM
from mailos.vendors.models import Message, Content, RoleType, ContentType, LLMResponse
from mailos.utils.logger_utils import setup_logger

logger = setup_logger('bedrock_anthropic_llm')

class BedrockAnthropicLLM(BaseLLM):
    """Anthropic implementation using AWS Bedrock."""
    
    def __init__(
        self,
        aws_access_key: str,  # AWS access key
        aws_secret_key: str,  # AWS secret key
        aws_session_token: str = None,  # Optional session token
        region: str = "us-east-1",
        model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        **kwargs
    ):
        # We'll pass None as api_key to parent since we're using AWS credentials
        super().__init__(None, model, **kwargs)
        self.region = region
        self.aws_credentials = {
            'aws_access_key_id': aws_access_key,
            'aws_secret_access_key': aws_secret_key,
            'region_name': region
        }
        if aws_session_token:
            self.aws_credentials['aws_session_token'] = aws_session_token
        
        self.session = boto3.Session(**self.aws_credentials)
        
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
    ) -> Union[LLMResponse, AsyncIterator[LLMResponse]]:
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
                            if 'content' in chunk:
                                yield LLMResponse(
                                    content=[Content(
                                        type=ContentType.TEXT,
                                        data=chunk['content']
                                    )],
                                    model=self.model
                                )
                    return response_generator()
                
                # For non-streaming responses
                response = await bedrock.invoke_model(
                    modelId=self.model,
                    body=json.dumps(request_body)
                )
                
                response_bytes = await response['body'].read()
                response_body = json.loads(response_bytes.decode())
                
                return LLMResponse(
                    content=[Content(
                        type=ContentType.TEXT,
                        data=response_body['content'][0]['text']
                    )],
                    model=self.model,
                    finish_reason=response_body.get('stop_reason'),
                    usage=response_body.get('usage')
                )
                
        except Exception as e:
            if "ThrottlingException" in str(e):
                await self.handle_rate_limit()
                return await self.generate(messages, stream)
            logger.error(f"Bedrock generation error: {str(e)}")
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
    ) -> LLMResponse:
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

    def generate_sync(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> LLMResponse:
        """Synchronous version of generate method."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate(messages, stream=stream))
        finally:
            loop.close()