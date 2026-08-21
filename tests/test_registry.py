"""Tests for MetricRegistry."""

import pytest

from src.metrics.registry import MetricRegistry
from src.metrics.difficulty import DifficultyMetric


class NotAMetric:
    pass


def test_register_and_list_create_clear():
    MetricRegistry.clear()
    MetricRegistry.register(DifficultyMetric)
    assert "difficulty" in MetricRegistry.list_metrics()

    metric = MetricRegistry.create("difficulty")
    assert metric.name == "difficulty"

    MetricRegistry.clear()
    assert MetricRegistry.list_metrics() == []


def test_register_requires_base_metric():
    MetricRegistry.clear()
    with pytest.raises(TypeError):
        MetricRegistry.register(NotAMetric)  # type: ignore[arg-type]


def test_create_unknown_metric():
    MetricRegistry.clear()
    with pytest.raises(ValueError):
        MetricRegistry.create("missing_metric")


def test_answer_key_correctness_is_registered(registered_metrics):
    assert "answer_key_correctness" in registered_metrics
    assert MetricRegistry.create("answer_key_correctness").name == "answer_key_correctness"


def test_objective_alignment_is_registered(registered_metrics):
    assert "objective_alignment" in registered_metrics
    assert MetricRegistry.create("objective_alignment").name == "objective_alignment"


def test_absence_of_cueing_is_registered(registered_metrics):
    assert "absence_of_cueing" in registered_metrics
    assert MetricRegistry.create("absence_of_cueing").name == "absence_of_cueing"
