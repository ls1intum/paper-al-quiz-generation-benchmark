"""Anthropic Claude provider implementation."""

import os
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation of LLM provider."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            model: Anthropic model name (e.g., claude-3-opus-20240229)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Environment variables required:
            ANTHROPIC_API_KEY: Anthropic API key
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment")

        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key,
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
        """Generate response using Anthropic Claude.

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
            llm = ChatAnthropic(
                model=self.model,
                temperature=temp,
                max_tokens=tokens,
                **{**self.additional_params, **kwargs},
            )
            response = llm.invoke(prompt)
        else:
            response = self.llm.invoke(prompt)

        return response.content
