"""Tests for configuration loading and validation."""

import pathlib

import pytest

from src.metrics.registry import MetricRegistry
from src.utils.config_loader import ConfigLoader


def test_parse_config_missing_benchmark_fields():
    config_dict = {"benchmark": {"name": "test"}}
    with pytest.raises(ValueError):
        ConfigLoader.parse_config(config_dict)


def test_parse_config_unknown_evaluator_reference():
    config_dict = {
        "benchmark": {"name": "test", "version": "1.0", "runs": 1},
        "evaluators": {"e1": {"provider": "mock", "model": "m"}},
        "metrics": [
            {
                "name": "difficulty",
                "version": "1.0",
                "evaluators": ["missing_eval"],
                "enabled": True,
            }
        ],
        "inputs": {"quiz_directory": "data/quizzes", "source_directory": "data/inputs"},
        "outputs": {"results_directory": "data/results"},
    }
    with pytest.raises(ValueError):
        ConfigLoader.parse_config(config_dict)


def test_parse_config_runs_must_be_positive():
    config_dict = {
        "benchmark": {"name": "test", "version": "1.0", "runs": 0},
        "evaluators": {"e1": {"provider": "mock", "model": "m"}},
        "metrics": [],
        "inputs": {"quiz_directory": "data/quizzes", "source_directory": "data/inputs"},
        "outputs": {"results_directory": "data/results"},
    }
    with pytest.raises(ValueError):
        ConfigLoader.parse_config(config_dict)


def test_hash_config_is_deterministic():
    config_dict = {
        "benchmark": {"name": "test", "version": "1.0", "runs": 2},
        "evaluators": {"e1": {"provider": "mock", "model": "m"}},
        "metrics": [
            {
                "name": "difficulty",
                "version": "1.0",
                "evaluators": ["e1"],
                "enabled": True,
            }
        ],
        "inputs": {"quiz_directory": "data/quizzes", "source_directory": "data/inputs"},
        "outputs": {"results_directory": "data/results"},
    }
    config = ConfigLoader.parse_config(config_dict)
    first = ConfigLoader.hash_config(config)
    second = ConfigLoader.hash_config(config)
    assert first == second


def test_parse_config_preserves_openai_compatible_additional_params():
    config_dict = {
        "benchmark": {"name": "test", "version": "1.0", "runs": 1},
        "evaluators": {
            "local_eval": {
                "provider": "openai_compatible",
                "model": "qwen2.5-7b-instruct",
                "base_url": "http://localhost:1234/v1",
                "api_key": "not-required",
                "temperature": 0.0,
                "max_tokens": 300,
            }
        },
        "metrics": [
            {
                "name": "difficulty",
                "version": "1.0",
                "evaluators": ["local_eval"],
                "enabled": True,
            }
        ],
        "inputs": {"quiz_directory": "data/quizzes", "source_directory": "data/inputs"},
        "outputs": {"results_directory": "data/results"},
    }

    config = ConfigLoader.parse_config(config_dict)
    evaluator = config.evaluators["local_eval"]

    assert evaluator.provider == "openai_compatible"
    assert evaluator.model == "qwen2.5-7b-instruct"
    assert evaluator.additional_params["base_url"] == "http://localhost:1234/v1"
    assert evaluator.additional_params["api_key"] == "not-required"


def test_parse_config_preserves_ollama_additional_params():
    config_dict = {
        "benchmark": {"name": "test", "version": "1.0", "runs": 1},
        "evaluators": {
            "ollama_eval": {
                "provider": "ollama",
                "model": "llama3.1:8b-instruct",
                "base_url": "http://localhost:11434",
                "temperature": 0.0,
                "max_tokens": 300,
            }
        },
        "metrics": [
            {
                "name": "difficulty",
                "version": "1.0",
                "evaluators": ["ollama_eval"],
                "enabled": True,
            }
        ],
        "inputs": {"quiz_directory": "data/quizzes", "source_directory": "data/inputs"},
        "outputs": {"results_directory": "data/results"},
    }

    config = ConfigLoader.parse_config(config_dict)
    evaluator = config.evaluators["ollama_eval"]

    assert evaluator.provider == "ollama"
    assert evaluator.model == "llama3.1:8b-instruct"
    assert evaluator.additional_params["base_url"] == "http://localhost:11434"


# ── shipped configs ──────────────────────────────────────────────────────── #

SHIPPED_CONFIGS = sorted(pathlib.Path("config").rglob("*.yaml"))


def test_shipped_configs_are_discoverable():
    """Guard the premise of the two tests below."""
    assert SHIPPED_CONFIGS, "no config/*.yaml found -- the tests below would be vacuous"


@pytest.mark.parametrize("config_path", SHIPPED_CONFIGS, ids=lambda p: p.stem)
def test_shipped_config_parses_and_every_metric_resolves(config_path, registered_metrics):
    """A committed config must load and name only metrics the registry has.

    A config is not exercised by any other test, so a typo in a metric name or a
    stale field sits undetected until someone spends a sweep discovering it.
    """
    config = ConfigLoader.parse_config(ConfigLoader.load_yaml(str(config_path)))
    for metric in config.get_enabled_metrics():
        assert MetricRegistry.create(metric.name).name == metric.name


@pytest.mark.parametrize("config_path", SHIPPED_CONFIGS, ids=lambda p: p.stem)
def test_shipped_config_input_directories_exist(config_path):
    """Every path a committed config points at must be in the repository.

    `instructions_directory` is the one that bites: `IOUtils.load_instructions`
    warns and continues when the directory is missing, so a config that means
    "run without instructions" and a config with a typo behave identically at
    runtime and differ only in intent.
    """
    config = ConfigLoader.parse_config(ConfigLoader.load_yaml(str(config_path)))
    for field in ("quiz_directory", "source_directory", "instructions_directory"):
        path = getattr(config.input_output, field, None)
        if path:
            assert pathlib.Path(path).exists(), f"{config_path}: {field} -> {path} does not exist"
