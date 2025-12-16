"""Azure OpenAI provider implementation."""

import os
from typing import Any, Optional

from langchain_openai import AzureChatOpenAI

from .base import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI implementation of LLM provider."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> None:
        """Initialize Azure OpenAI provider.

        Args:
            model: Azure deployment name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Environment variables required:
            AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
            AZURE_OPENAI_API_KEY: API key
            AZURE_OPENAI_API_VERSION: API version (optional)
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not endpoint or not api_key:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in environment"
            )

        self.llm = AzureChatOpenAI(
            azure_deployment=model,
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
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
        """Generate response using Azure OpenAI.

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
            llm = AzureChatOpenAI(
                azure_deployment=self.model,
                temperature=temp,
                max_tokens=tokens,
                **{**self.additional_params, **kwargs},
            )
            response = llm.invoke(prompt)
        else:
            response = self.llm.invoke(prompt)

        return response.content
