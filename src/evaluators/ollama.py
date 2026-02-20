"""Ollama provider implementation."""

import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..models.config import EvaluatorConfig
from .openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama specialization of the OpenAI-compatible provider."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Ollama provider with local defaults."""
        resolved_base_url = self._normalize_openai_base_url(
            base_url
            or os.getenv("OLLAMA_ENDPOINT")
            or os.getenv("CUSTOM_LLM_ENDPOINT")
            or "http://localhost:11434/v1"
        )
        resolved_api_key = (
            api_key or os.getenv("OLLAMA_API_KEY") or os.getenv("CUSTOM_LLM_API_KEY") or "not-required"
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
    def _normalize_openai_base_url(base_url: str) -> str:
        """Ensure base URL points to OpenAI-compatible /v1 endpoint."""
        stripped = base_url.rstrip("/")
        if stripped.endswith("/v1"):
            return stripped
        return f"{stripped}/v1"

    @staticmethod
    def _to_native_base_url(base_url: str) -> str:
        """Convert OpenAI-compatible base URL to native Ollama server base URL."""
        stripped = base_url.rstrip("/")
        if stripped.endswith("/v1"):
            return stripped[:-3]
        return stripped

    @classmethod
    def preflight(cls, evaluators: Dict[str, EvaluatorConfig]) -> None:
        """Fail early for Ollama configuration/server/model issues."""
        ollama_evaluators = {
            name: cfg for name, cfg in evaluators.items() if cfg.provider == "ollama"
        }
        if not ollama_evaluators:
            return

        endpoint_env = os.getenv("OLLAMA_ENDPOINT") or os.getenv("CUSTOM_LLM_ENDPOINT")
        api_key = os.getenv("OLLAMA_API_KEY") or os.getenv("CUSTOM_LLM_API_KEY") or "not-required"

        grouped_models: Dict[str, List[str]] = defaultdict(list)
        unresolved = []

        for eval_name, cfg in ollama_evaluators.items():
            configured_base_url = cfg.additional_params.get("base_url")
            base_url = configured_base_url or endpoint_env
            if not base_url:
                unresolved.append(eval_name)
                continue

            normalized_base_url = cls._normalize_openai_base_url(str(base_url))
            grouped_models[normalized_base_url].append(cfg.model)

        if unresolved:
            unresolved_str = ", ".join(unresolved)
            raise RuntimeError(
                "Ollama preflight failed: endpoint not configured for evaluator(s): "
                f"{unresolved_str}. Set OLLAMA_ENDPOINT (or CUSTOM_LLM_ENDPOINT) in .env, "
                "or define base_url in each ollama evaluator."
            )

        for base_url, required_models in grouped_models.items():
            available_models = cls._fetch_available_model_ids(base_url=base_url, api_key=api_key)
            missing = sorted(set(required_models) - set(available_models))
            if missing:
                cls._pull_missing_models(base_url=base_url, api_key=api_key, missing_models=missing)

                available_after_pull = cls._fetch_available_model_ids(base_url=base_url, api_key=api_key)
                still_missing = sorted(set(required_models) - set(available_after_pull))
                if still_missing:
                    pull_instructions = "; ".join(
                        f"ollama pull {model}" for model in still_missing
                    )
                    raise RuntimeError(
                        "Ollama preflight failed: required model(s) not available on "
                        f"{base_url}: {still_missing}. Available model names: {available_after_pull}. "
                        f"Pull missing models with: {pull_instructions}. "
                        "Then re-run the benchmark."
                    )

    @classmethod
    def _fetch_available_model_ids(cls, base_url: str, api_key: str, timeout: int = 5) -> List[str]:
        """Fetch available model names from native Ollama /api/tags."""
        native_base = cls._to_native_base_url(base_url)
        tags_url = f"{native_base}/api/tags"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request = Request(tags_url, headers=headers)

        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(
                "Ollama preflight failed: cannot reach server at "
                f"{tags_url}. Ensure Ollama is running (e.g., `ollama serve`)."
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Ollama preflight failed: invalid /api/tags response from "
                f"{tags_url}."
            ) from exc

        models = payload.get("models", [])
        model_names = [item["name"] for item in models if isinstance(item, dict) and "name" in item]
        return sorted(model_names)

    @classmethod
    def _pull_missing_models(cls, base_url: str, api_key: str, missing_models: List[str]) -> None:
        """Attempt pulling missing models from the Ollama server."""
        native_base = cls._to_native_base_url(base_url)
        pull_url = f"{native_base}/api/pull"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        for model in missing_models:
            payload = json.dumps({"model": model, "stream": False}).encode("utf-8")
            request = Request(pull_url, data=payload, headers=headers, method="POST")

            try:
                with urlopen(request, timeout=600):
                    pass
            except URLError as exc:
                raise RuntimeError(
                    "Ollama preflight failed while pulling missing model "
                    f"'{model}' from {pull_url}. Try running `ollama pull {model}` manually."
                ) from exc
