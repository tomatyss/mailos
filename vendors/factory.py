from typing import Dict, Type
from .base import BaseLLM
from .openai_llm import OpenAILLM
from .anthropic_llm import AnthropicLLM
from .bedrock_anthropic import BedrockAnthropicLLM

from utils.logger_utils import setup_logger

logger = setup_logger('llm_factory')

class LLMFactory:
    """Factory for creating LLM instances."""
    
    _providers = {}
    
    @classmethod
    def register(cls, name: str, provider_class):
        """Register a new LLM provider."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create(cls, provider: str, model: str, **kwargs):
        """Create an LLM instance.
        
        Args:
            provider: The name of the provider (e.g., 'openai', 'anthropic', 'bedrock-anthropic')
            model: The model name to use
            **kwargs: Additional arguments passed to the provider constructor
                     (e.g., api_key, aws_access_key, aws_secret_key, etc.)
        """
        if provider not in cls._providers:
            raise ValueError(f"Unknown provider: {provider}")
            
        provider_class = cls._providers[provider]
        
        kwargs.pop('provider', None)
        kwargs.pop('model', None)
        
        return provider_class(model=model, **kwargs)

# Register the default providers
LLMFactory.register("openai", OpenAILLM)
LLMFactory.register("anthropic", AnthropicLLM)
LLMFactory.register("bedrock-anthropic", BedrockAnthropicLLM)