"""Tests for configuration loading and validation."""

import pytest

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
