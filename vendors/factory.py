from typing import Dict, Type
from .base import BaseLLM
from .openai_llm import OpenAILLM
from .anthropic_llm import AnthropicLLM
from .bedrock_anthropic import BedrockAnthropicLLM

from utils.logger_utils import setup_logger

logger = setup_logger('llm_factory')

class LLMFactory:
    """Factory for creating LLM instances."""
    
    _providers: Dict[str, Type[BaseLLM]] = {
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
        "bedrock-anthropic": BedrockAnthropicLLM
    }

    @classmethod
    def create(
        cls, 
        provider: str,
        api_key: str,
        model: str,
        **kwargs
    ) -> BaseLLM:
        """Create an instance of an LLM provider."""
        if provider not in cls._providers:
            raise ValueError(f"Provider {provider} not supported")
        
        return cls._providers[provider](api_key, model, **kwargs)

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: Type[BaseLLM]
    ) -> None:
        """Register a new LLM provider."""
        cls._providers[name] = provider_class 