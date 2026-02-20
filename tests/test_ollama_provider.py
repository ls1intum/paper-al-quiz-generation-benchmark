"""Tests for Ollama preflight validation."""

import pytest

from src.evaluators.ollama import OllamaProvider
from src.models.config import EvaluatorConfig


def test_preflight_fails_when_endpoint_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OLLAMA_ENDPOINT", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_ENDPOINT", raising=False)

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="ollama",
            model="llama3.1:8b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        )
    }

    with pytest.raises(RuntimeError, match="endpoint not configured"):
        OllamaProvider.preflight(evaluators)


def test_preflight_fails_when_server_unreachable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://localhost:11434")

    def _raise_unreachable(base_url: str, api_key: str, timeout: int = 5):
        raise RuntimeError("Ollama preflight failed: cannot reach server")

    monkeypatch.setattr(OllamaProvider, "_fetch_available_model_ids", classmethod(
        lambda cls, base_url, api_key, timeout=5: _raise_unreachable(base_url, api_key, timeout)
    ))

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="ollama",
            model="llama3.1:8b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        )
    }

    with pytest.raises(RuntimeError, match="cannot reach server"):
        OllamaProvider.preflight(evaluators)


def test_preflight_fails_when_required_model_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://localhost:11434")

    pulled = []

    monkeypatch.setattr(
        OllamaProvider,
        "_fetch_available_model_ids",
        classmethod(lambda cls, base_url, api_key, timeout=5: ["llama3.1:8b-instruct"]),
    )
    monkeypatch.setattr(
        OllamaProvider,
        "_pull_missing_models",
        classmethod(
            lambda cls, base_url, api_key, missing_models: pulled.extend(missing_models)
        ),
    )

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="ollama",
            model="llama3.1:8b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
        "local_b": EvaluatorConfig(
            name="local_b",
            provider="ollama",
            model="qwen2.5:7b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
    }

    with pytest.raises(RuntimeError, match="required model\\(s\\) not available"):
        OllamaProvider.preflight(evaluators)
    assert pulled == ["qwen2.5:7b-instruct"]


def test_preflight_passes_when_all_models_available(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://localhost:11434")

    monkeypatch.setattr(
        OllamaProvider,
        "_fetch_available_model_ids",
        classmethod(
            lambda cls, base_url, api_key, timeout=5: [
                "llama3.1:8b-instruct",
                "qwen2.5:7b-instruct",
            ]
        ),
    )

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="ollama",
            model="llama3.1:8b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
        "local_b": EvaluatorConfig(
            name="local_b",
            provider="ollama",
            model="qwen2.5:7b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
    }

    OllamaProvider.preflight(evaluators)


def test_preflight_auto_pulls_and_passes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://localhost:11434")

    available = {"llama3.1:8b-instruct"}

    monkeypatch.setattr(
        OllamaProvider,
        "_fetch_available_model_ids",
        classmethod(lambda cls, base_url, api_key, timeout=5: sorted(available)),
    )
    monkeypatch.setattr(
        OllamaProvider,
        "_pull_missing_models",
        classmethod(
            lambda cls, base_url, api_key, missing_models: available.update(missing_models)
        ),
    )

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="ollama",
            model="llama3.1:8b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
        "local_b": EvaluatorConfig(
            name="local_b",
            provider="ollama",
            model="qwen2.5:7b-instruct",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
    }

    OllamaProvider.preflight(evaluators)
