from typing import AsyncIterator, List, Union
import openai
from .base import BaseLLM
from .models import Message, Content, RoleType

class OpenAILLM(BaseLLM):
    """OpenAI implementation of the LLM interface."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        openai.api_key = api_key

    async def generate(
        self, 
        messages: List[Message],
        stream: bool = False
    ) -> Union[Message, AsyncIterator[Message]]:
        """Generate a response using OpenAI's API."""
        
        formatted_messages = [
            {
                "role": msg.role.value,
                "content": [c.data for c in msg.content],
                **({"name": msg.name} if msg.name else {}),
                **({"function_call": msg.function_call} if msg.function_call else {})
            }
            for msg in messages
        ]

        functions = [tool.to_dict() for tool in self.tools.values()]
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=formatted_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=stream,
                functions=functions if functions else None
            )

            if stream:
                async def response_generator():
                    async for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield Message(
                                role=RoleType.ASSISTANT,
                                content=[Content(
                                    type="text",
                                    data=chunk.choices[0].delta.content
                                )]
                            )
                return response_generator()
            
            return Message(
                role=RoleType.ASSISTANT,
                content=[Content(
                    type="text",
                    data=response.choices[0].message.content
                )],
                function_call=response.choices[0].message.get("function_call")
            )

        except openai.error.RateLimitError:
            await self.handle_rate_limit()
            return await self.generate(messages, stream)

    async def handle_rate_limit(self) -> None:
        """Handle OpenAI rate limiting."""
        import asyncio
        await asyncio.sleep(20)  # Simple exponential backoff

    # Implement other abstract methods... 