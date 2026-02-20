"""Tests for LLM provider factory creation."""

from src.evaluators.factory import LLMProviderFactory
from src.evaluators.openai_compatible import OpenAICompatibleProvider
from src.models.config import EvaluatorConfig


def test_factory_creates_openai_compatible_from_config():
    config = EvaluatorConfig(
        name="lmstudio_fast",
        provider="openai_compatible",
        model="qwen2.5-7b-instruct",
        temperature=0.0,
        max_tokens=300,
        additional_params={"base_url": "http://localhost:1234/v1", "api_key": "not-required"},
    )

    provider = LLMProviderFactory.create(config)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.model_name == "qwen2.5-7b-instruct"
    assert provider.base_url == "http://localhost:1234/v1"

