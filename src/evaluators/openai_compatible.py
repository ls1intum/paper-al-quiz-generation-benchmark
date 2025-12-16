"""OpenAI-compatible provider for local/open-source models."""

import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Generic provider for OpenAI-compatible APIs (e.g., local models, vLLM, etc.)."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI-compatible provider.

        Args:
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            base_url: Base URL for the API endpoint
            api_key: API key (if required)
            **kwargs: Additional parameters

        Environment variables (if not provided as args):
            CUSTOM_LLM_ENDPOINT: Base URL for the API
            CUSTOM_LLM_API_KEY: API key (optional)
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        self.base_url = base_url or os.getenv("CUSTOM_LLM_ENDPOINT")
        self.api_key = api_key or os.getenv("CUSTOM_LLM_API_KEY", "not-required")

        if not self.base_url:
            raise ValueError(
                "base_url must be provided or CUSTOM_LLM_ENDPOINT must be set in environment"
            )

        self.llm = ChatOpenAI(
            model=model,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate response using OpenAI-compatible endpoint.

        Args:
            prompt: Input prompt
            temperature: Override temperature
            max_tokens: Override max_tokens
            **kwargs: Additional parameters

        Returns:
            Generated text response
        """
        # Create a new LLM instance if parameters are overridden
        if temperature is not None or max_tokens is not None:
            temp = temperature if temperature is not None else self.temperature
            tokens = max_tokens if max_tokens is not None else self.max_tokens
            llm = ChatOpenAI(
                model=self.model,
                base_url=self.base_url,
                api_key=self.api_key,
                temperature=temp,
                max_tokens=tokens,
                **{**self.additional_params, **kwargs},
            )
            response = llm.invoke(prompt)
        else:
            response = self.llm.invoke(prompt)

        return response.content
