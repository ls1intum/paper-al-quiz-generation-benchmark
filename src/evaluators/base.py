"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel


class LLMProvider(ABC):
    """Abstract base class for LLM providers using Strategy pattern.

    This interface allows easy swapping of different LLM providers
    while maintaining consistent evaluation logic.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> None:
        """Initialize the LLM provider.

        Args:
            model: Model identifier
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.additional_params = kwargs
        self._usage_log: List[Dict[str, int]] = []

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional generation parameters

        Returns:
            The generated text response

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a schema-validated structured response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            schema: Pydantic schema describing required response structure
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional generation parameters

        Returns:
            Structured response as dictionary

        Raises:
            Exception: If generation or schema validation fails
        """
        pass

    def reset_usage(self) -> None:
        self._usage_log.clear()

    def get_accumulated_usage(self) -> Dict[str, int]:
        total = {"prompt_tokens": 0, "completion_tokens": 0}
        for entry in self._usage_log:
            total["prompt_tokens"] += entry.get("prompt_tokens", 0)
            total["completion_tokens"] += entry.get("completion_tokens", 0)
        return total

    def _record_usage(self, response: Any) -> None:
        usage = getattr(response, "usage_metadata", None)
        if usage:
            self._usage_log.append(
                {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                }
            )

    @property
    def model_name(self) -> str:
        """Return the model identifier.

        Returns:
            String identifier for the model
        """
        return self.model

    def __repr__(self) -> str:
        """String representation of the provider."""
        return (
            f"{self.__class__.__name__}(model={self.model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens})"
        )
