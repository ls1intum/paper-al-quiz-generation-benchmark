"""Factory for creating LLM providers."""

from typing import Any, Dict

from ..models.config import EvaluatorConfig
from .anthropic import AnthropicProvider
from .azure_openai import AzureOpenAIProvider
from .base import LLMProvider
from .openai import OpenAIProvider
from .openai_compatible import OpenAICompatibleProvider


class LLMProviderFactory:
    """Factory class for creating LLM providers from configuration."""

    _PROVIDER_MAP = {
        "azure_openai": AzureOpenAIProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }

    @classmethod
    def create(cls, config: EvaluatorConfig) -> LLMProvider:
        """Create an LLM provider from configuration.

        Args:
            config: Evaluator configuration

        Returns:
            Initialized LLM provider

        Raises:
            ValueError: If provider type is unknown
        """
        provider_class = cls._PROVIDER_MAP.get(config.provider)
        if provider_class is None:
            raise ValueError(
                f"Unknown provider type: {config.provider}. "
                f"Available providers: {list(cls._PROVIDER_MAP.keys())}"
            )

        return provider_class(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **config.additional_params,
        )

    @classmethod
    def create_from_dict(cls, provider_dict: Dict[str, Any]) -> LLMProvider:
        """Create an LLM provider from a dictionary.

        Args:
            provider_dict: Dictionary with provider configuration

        Returns:
            Initialized LLM provider

        Raises:
            ValueError: If required fields are missing or provider type is unknown
        """
        required_fields = ["provider", "model"]
        for field in required_fields:
            if field not in provider_dict:
                raise ValueError(f"Missing required field: {field}")

        provider_type = provider_dict["provider"]
        provider_class = cls._PROVIDER_MAP.get(provider_type)

        if provider_class is None:
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available providers: {list(cls._PROVIDER_MAP.keys())}"
            )

        # Extract standard parameters
        model = provider_dict["model"]
        temperature = provider_dict.get("temperature", 0.0)
        max_tokens = provider_dict.get("max_tokens", 500)

        # Collect additional parameters
        additional_params = {
            k: v
            for k, v in provider_dict.items()
            if k not in ["provider", "model", "temperature", "max_tokens"]
        }

        return provider_class(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **additional_params,
        )

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a new provider type.

        Args:
            name: Name to register the provider under
            provider_class: Provider class to register

        Raises:
            ValueError: If provider_class doesn't inherit from LLMProvider
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError("provider_class must inherit from LLMProvider")

        cls._PROVIDER_MAP[name] = provider_class
