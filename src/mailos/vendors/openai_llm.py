"""OpenAI implementation of the LLM interface."""

import asyncio
from typing import AsyncIterator, List, Union

from openai import OpenAI, RateLimitError

from mailos.vendors.base import BaseLLM
from mailos.vendors.models import Content, ContentType, LLMResponse, Message


class OpenAILLM(BaseLLM):
    """OpenAI implementation of the LLM interface."""

    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        """Initialize OpenAILLM instance."""
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(api_key=api_key)

    async def generate(
        self, messages: List[Message], stream: bool = False
    ) -> Union[LLMResponse, AsyncIterator[LLMResponse]]:
        """Generate a response using OpenAI's API."""
        formatted_messages = [
            {
                "role": msg.role.value,
                "content": [c.data for c in msg.content][0],  # Take first content item
                **({"name": msg.name} if msg.name else {}),
                **({"function_call": msg.function_call} if msg.function_call else {}),
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
                tools=tools if tools else None,
            )

            if stream:

                async def response_generator():
                    async for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield LLMResponse(
                                content=[
                                    Content(
                                        type=ContentType.TEXT,
                                        data=chunk.choices[0].delta.content,
                                    )
                                ],
                                model=self.model,
                            )

                return response_generator()

            # Create LLMResponse for completion
            return LLMResponse(
                content=[
                    Content(
                        type=ContentType.TEXT,
                        data=response.choices[0].message.content or "",
                    )
                ],
                model=self.model,
                finish_reason=response.choices[0].finish_reason,
                tool_calls=(
                    [
                        {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        }
                        for tool_call in response.choices[0].message.tool_calls
                    ]
                    if response.choices[0].message.tool_calls
                    else None
                ),
                usage=response.usage.model_dump() if response.usage else None,
                system_fingerprint=response.system_fingerprint,
            )

        except RateLimitError:
            await self.handle_rate_limit()
            return await self.generate(messages, stream)

    def generate_sync(
        self, messages: List[Message], stream: bool = False
    ) -> LLMResponse:
        """Synchronize wrapper for generate()."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate(messages, stream))
        finally:
            loop.close()
