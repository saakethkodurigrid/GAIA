"""
Factory for creating LLM provider instances
"""
from typing import Optional
from core.config import settings
from .base import BaseLLMProvider
from .groq_provider import GroqProvider
from .anthropic_provider import AnthropicProvider


class LLMProviderFactory:
    """Factory to create LLM provider instances"""
    
    _providers = {
        "groq": GroqProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def create_provider(
        cls,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create LLM provider instance
        
        Args:
            provider_name: Provider name (defaults to LLM_PROVIDER from config)
            model: Model name (defaults to provider-specific default)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Initialized LLM provider instance
        """
        # Get provider name from config if not specified
        provider_name = provider_name or settings.LLM_PROVIDER or "groq"
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[provider_name]
        
        # Get API key based on provider
        api_key = cls._get_api_key(provider_name)
        
        # Get default model if not specified
        if not model:
            model = cls._get_default_model(provider_name)
        
        # Create provider instance
        return provider_class(api_key=api_key, model=model, **kwargs)
    
    @classmethod
    def _get_api_key(cls, provider_name: str) -> str:
        """Get API key for provider"""
        key_map = {
            "groq": settings.GROQ_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
        }
        api_key = key_map.get(provider_name, "")
        if not api_key:
            raise ValueError(
                f"{provider_name.upper()}_API_KEY not found in configuration. "
                f"Please set it in your environment or .env file."
            )
        return api_key
    
    @classmethod
    def _get_default_model(cls, provider_name: str) -> str:
        """Get default model for provider"""
        defaults = {
            "groq": getattr(settings, 'GROQ_DEFAULT_MODEL', 'llama-3.1-8b-instant'),
            "anthropic": getattr(settings, 'ANTHROPIC_DEFAULT_MODEL', 'claude-sonnet-4-20250514'),
        }
        return defaults.get(provider_name, "")

