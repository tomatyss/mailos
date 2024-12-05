from typing import AsyncIterator, List, Union
from openai import OpenAI, RateLimitError
from .base import BaseLLM
from .models import Message, Content, RoleType
import asyncio


class OpenAILLM(BaseLLM):
    """OpenAI implementation of the LLM interface."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(api_key=api_key)

    async def generate(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> Union[Message, AsyncIterator[Message]]:
        """Generate a response using OpenAI's API."""

        formatted_messages = [
            {
                "role": msg.role.value,
                "content": [c.data for c in msg.content][0],  # Take first content item
                **({"name": msg.name} if msg.name else {}),
                **({"function_call": msg.function_call} if msg.function_call else {})
            }
            for msg in messages
        ]

        tools = [tool.to_dict() for tool in self.tools.values()]

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=formatted_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=stream,
                tools=tools if tools else None
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

            # Handle function calls
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                return Message(
                    role=RoleType.ASSISTANT,
                    content=[Content(
                        type="text",
                        data=response.choices[0].message.content or ""
                    )],
                    function_call={
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                )

            # Handle regular responses
            return Message(
                role=RoleType.ASSISTANT,
                content=[Content(
                    type="text",
                    data=response.choices[0].message.content
                )]
            )

        except RateLimitError:
            await self.handle_rate_limit()
            return await self.generate(messages, stream)

    def generate_sync(
        self,
        messages: List[Message],
        stream: bool = False
    ) -> Message:
        """Synchronous wrapper for generate()."""
        return asyncio.run(self.generate(messages, stream))
