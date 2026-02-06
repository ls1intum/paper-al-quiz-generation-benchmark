"""Azure OpenAI provider implementation using the v1 API."""

import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI implementation of LLM provider using the v1 API.

    This implementation uses the new Azure OpenAI v1 API (GA August 2025)
    which provides a unified interface compatible with the standard OpenAI client.
    No api_version parameter is required with this approach.
    """

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
            AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL (without /openai/v1 suffix)
            AZURE_OPENAI_API_KEY: API key
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if not endpoint or not api_key:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in environment"
            )

        # Construct the v1 API base URL
        # Remove trailing slash if present, then append /openai/v1
        base_url = endpoint.rstrip("/") + "/openai/v1"

        self.llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_completion_tokens=max_tokens,
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

            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            base_url = endpoint.rstrip("/") + "/openai/v1"

            llm = ChatOpenAI(
                model=self.model,
                base_url=base_url,
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                temperature=temp,
                max_completion_tokens=tokens,
                **{**self.additional_params, **kwargs},
            )
            response = llm.invoke(prompt)
        else:
            response = self.llm.invoke(prompt)

        content = response.content
        if isinstance(content, str):
            return content
        return str(content)
