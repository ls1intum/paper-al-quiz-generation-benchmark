"""Tests for aggregation utilities."""

from datetime import datetime

import pytest

from src.analysis.aggregator import ResultsAggregator
from src.models.result import BenchmarkResult, MetricResult


def make_result(run_number: int, score: float) -> BenchmarkResult:
    metric = MetricResult(
        metric_name="difficulty",
        metric_version="1.0",
        score=score,
        evaluator_model="mock",
        quiz_id="quiz_1",
        question_id="q1",
    )

    return BenchmarkResult(
        benchmark_id=f"bench_{run_number}",
        benchmark_version="1.0",
        config_hash="hash",
        quiz_id="quiz_1",
        run_number=run_number,
        metrics=[metric],
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )


def test_aggregate_results():
    results = [make_result(1, 40.0), make_result(2, 60.0)]
    aggregated = ResultsAggregator.aggregate(results, "test")

    assert aggregated.total_runs == 2
    assert aggregated.get_all_metrics() == ["difficulty"]
    agg = aggregated.get_aggregation("difficulty", "mock")
    assert agg is not None
    assert agg.mean == 50.0
    assert agg.min == 40.0
    assert agg.max == 60.0


def test_aggregate_by_metric():
    results = [make_result(1, 10.0), make_result(2, 20.0)]
    aggregations = ResultsAggregator.aggregate_by_metric(results, "difficulty")
    assert "mock" in aggregations
    assert aggregations["mock"].mean == 15.0


def test_compare_evaluators():
    results = [make_result(1, 10.0), make_result(2, 30.0)]
    comparison = ResultsAggregator.compare_evaluators(results, "difficulty")
    assert comparison["mock"]["mean"] == 20.0


def test_aggregate_empty_results():
    with pytest.raises(ValueError):
        ResultsAggregator.aggregate([], "test")
