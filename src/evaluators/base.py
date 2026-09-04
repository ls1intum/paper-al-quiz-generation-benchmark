"""Base LLM provider interface."""

import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class TransientLLMError(Exception):
    """Raised when retries are exhausted on a transient LLM failure."""

    def __init__(self, message: str, original: Exception, attempts: int) -> None:
        super().__init__(message)
        self.original = original
        self.attempts = attempts


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
        self.retry_max_attempts = kwargs.pop("retry_max_attempts", 4)
        self.retry_base_delay = kwargs.pop("retry_base_delay", 30)
        self.retry_max_delay = kwargs.pop("retry_max_delay", 300)
        self.additional_params = kwargs
        self._usage_log: list[dict[str, int]] = []
        self._warned_missing_usage: bool = False

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        if status is not None and status in {408, 429, 500, 502, 503, 504}:
            return True
        return type(exc).__name__ in ("APIConnectionError", "APITimeoutError")

    def _call_with_retry(self, fn: Callable[[], _T]) -> _T:
        for attempt in range(1, self.retry_max_attempts + 1):
            try:
                return fn()
            except Exception as exc:
                if not self._is_transient_error(exc):
                    raise
                if attempt == self.retry_max_attempts:
                    raise TransientLLMError(
                        f"Transient failure after {attempt} attempts: {exc}",
                        original=exc,
                        attempts=attempt,
                    ) from exc
                delay = min(self.retry_base_delay * (2 ** (attempt - 1)), self.retry_max_delay)
                jitter = random.uniform(0, delay * 0.25)
                wait = delay + jitter
                logger.warning(
                    "Transient error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt,
                    self.retry_max_attempts,
                    wait,
                    exc,
                )
                time.sleep(wait)
        raise AssertionError("unreachable: retry_max_attempts must be >= 1")

    def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        return self._call_with_retry(
            lambda: self._do_generate(
                prompt, temperature=temperature, max_tokens=max_tokens, **kwargs
            )
        )

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._call_with_retry(
            lambda: self._do_generate_structured(
                prompt, schema, temperature=temperature, max_tokens=max_tokens, **kwargs
            )
        )

    @abstractmethod
    def _do_generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a response from the LLM."""

    @abstractmethod
    def _do_generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a schema-validated structured response from the LLM."""

    def reset_usage(self) -> None:
        self._usage_log.clear()

    def get_accumulated_usage(self) -> dict[str, int]:
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
            return

        # A response with no usage metadata is not a zero-token call, it is an
        # unmeasured one -- some self-hosted OpenAI-compatible servers omit the
        # field entirely. Counting it as nothing silently produces a complete,
        # plausible and wrong usage report, so say it once per provider rather
        # than never.
        if not self._warned_missing_usage:
            self._warned_missing_usage = True
            logging.getLogger(__name__).warning(
                "%s returned no token usage metadata; token totals for this evaluator "
                "will under-report. Every later call is affected, this warning is not.",
                self.model_name,
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
