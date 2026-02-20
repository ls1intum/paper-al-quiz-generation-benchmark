"""LM Studio provider implementation."""

import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..models.config import EvaluatorConfig
from .openai_compatible import OpenAICompatibleProvider


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio specialization of the OpenAI-compatible provider."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize LM Studio provider with sensible local defaults."""
        resolved_base_url = self._normalize_base_url(
            base_url
            or os.getenv("LM_STUDIO_ENDPOINT")
            or os.getenv("CUSTOM_LLM_ENDPOINT")
            or "http://localhost:1234/v1"
        )
        resolved_api_key = (
            api_key
            or os.getenv("LM_STUDIO_API_KEY")
            or os.getenv("CUSTOM_LLM_API_KEY")
            or "not-required"
        )

        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            **kwargs,
        )

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        """Ensure base URL points to OpenAI-compatible /v1 endpoint."""
        stripped = base_url.rstrip("/")
        if stripped.endswith("/v1"):
            return stripped
        return f"{stripped}/v1"

    @classmethod
    def preflight(cls, evaluators: Dict[str, EvaluatorConfig]) -> None:
        """Fail early for LM Studio configuration/server/model issues."""
        lm_evaluators = {
            name: cfg for name, cfg in evaluators.items() if cfg.provider == "lm_studio"
        }
        if not lm_evaluators:
            return

        endpoint_env = os.getenv("LM_STUDIO_ENDPOINT") or os.getenv("CUSTOM_LLM_ENDPOINT")
        api_key = os.getenv("LM_STUDIO_API_KEY") or os.getenv("CUSTOM_LLM_API_KEY") or "not-required"

        grouped_models: Dict[str, List[str]] = defaultdict(list)
        unresolved = []

        for eval_name, cfg in lm_evaluators.items():
            configured_base_url = cfg.additional_params.get("base_url")
            base_url = configured_base_url or endpoint_env
            if not base_url:
                unresolved.append(eval_name)
                continue

            normalized_base_url = cls._normalize_base_url(str(base_url))
            grouped_models[normalized_base_url].append(cfg.model)

        if unresolved:
            unresolved_str = ", ".join(unresolved)
            raise RuntimeError(
                "LM Studio preflight failed: endpoint not configured for evaluator(s): "
                f"{unresolved_str}. Set LM_STUDIO_ENDPOINT (or CUSTOM_LLM_ENDPOINT) in .env, "
                "or define base_url in each lm_studio evaluator."
            )

        for base_url, required_models in grouped_models.items():
            available_models = cls._fetch_available_model_ids(base_url=base_url, api_key=api_key)
            missing = sorted(set(required_models) - set(available_models))
            if missing:
                raise RuntimeError(
                    "LM Studio preflight failed: required model(s) not available on "
                    f"{base_url}: {missing}. Available model IDs: {available_models}. "
                    "Check /v1/models output and update your config model IDs."
                )

    @staticmethod
    def _fetch_available_model_ids(base_url: str, api_key: str, timeout: int = 5) -> List[str]:
        """Fetch available model IDs from an OpenAI-compatible /v1/models endpoint."""
        models_url = f"{base_url}/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request = Request(models_url, headers=headers)

        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(
                "LM Studio preflight failed: cannot reach server at "
                f"{models_url}. Ensure LM Studio local server is running."
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "LM Studio preflight failed: invalid /v1/models response from "
                f"{models_url}."
            ) from exc

        data = payload.get("data", [])
        model_ids = [item["id"] for item in data if isinstance(item, dict) and "id" in item]
        return sorted(model_ids)

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate response and raise actionable LM Studio errors."""
        try:
            return super().generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except Exception as exc:
            message = str(exc)
            if "No models loaded" in message:
                raise RuntimeError(
                    "LM Studio reports no model loaded. "
                    "Enable JIT loading or load a model manually, and ensure the configured "
                    "model ID matches one of /v1/models."
                ) from exc
            raise
