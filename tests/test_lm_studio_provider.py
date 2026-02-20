"""Tests for LM Studio preflight validation."""

import pytest

from src.evaluators.lm_studio import LMStudioProvider
from src.models.config import EvaluatorConfig


def test_preflight_fails_when_endpoint_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LM_STUDIO_ENDPOINT", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_ENDPOINT", raising=False)

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="lm_studio",
            model="model-a",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        )
    }

    with pytest.raises(RuntimeError, match="endpoint not configured"):
        LMStudioProvider.preflight(evaluators)


def test_preflight_fails_when_server_unreachable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LM_STUDIO_ENDPOINT", "http://localhost:1234/v1")

    def _raise_unreachable(base_url: str, api_key: str, timeout: int = 5):
        raise RuntimeError("LM Studio preflight failed: cannot reach server")

    monkeypatch.setattr(
        LMStudioProvider, "_fetch_available_model_ids", staticmethod(_raise_unreachable)
    )

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="lm_studio",
            model="model-a",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        )
    }

    with pytest.raises(RuntimeError, match="cannot reach server"):
        LMStudioProvider.preflight(evaluators)


def test_preflight_fails_when_required_model_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LM_STUDIO_ENDPOINT", "http://localhost:1234/v1")

    def _available_models(base_url: str, api_key: str, timeout: int = 5):
        return ["model-a"]

    monkeypatch.setattr(
        LMStudioProvider, "_fetch_available_model_ids", staticmethod(_available_models)
    )

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="lm_studio",
            model="model-a",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
        "local_b": EvaluatorConfig(
            name="local_b",
            provider="lm_studio",
            model="model-b",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
    }

    with pytest.raises(RuntimeError, match="required model\\(s\\) not available"):
        LMStudioProvider.preflight(evaluators)


def test_preflight_passes_when_all_models_available(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LM_STUDIO_ENDPOINT", "http://localhost:1234/v1")

    def _available_models(base_url: str, api_key: str, timeout: int = 5):
        return ["model-a", "model-b"]

    monkeypatch.setattr(
        LMStudioProvider, "_fetch_available_model_ids", staticmethod(_available_models)
    )

    evaluators = {
        "local_a": EvaluatorConfig(
            name="local_a",
            provider="lm_studio",
            model="model-a",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
        "local_b": EvaluatorConfig(
            name="local_b",
            provider="lm_studio",
            model="model-b",
            temperature=0.0,
            max_tokens=100,
            additional_params={},
        ),
    }

    LMStudioProvider.preflight(evaluators)
