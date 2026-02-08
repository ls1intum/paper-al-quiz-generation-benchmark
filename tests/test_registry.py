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
    with pytest.raises(ValueError):
        MetricRegistry.register(NotAMetric)  # type: ignore[arg-type]


def test_create_unknown_metric():
    MetricRegistry.clear()
    with pytest.raises(ValueError):
        MetricRegistry.create("missing_metric")
