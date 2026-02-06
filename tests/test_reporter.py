"""Tests for result reporting."""

from datetime import datetime

from src.analysis.reporter import ResultsReporter
from src.models.result import AggregatedResults, MetricAggregation, BenchmarkResult, MetricResult


def test_generate_summary():
    agg = AggregatedResults(
        benchmark_config_name="test",
        benchmark_version="1.0",
        quiz_ids=["quiz_1"],
        total_runs=2,
        aggregations={
            "difficulty_mock": MetricAggregation(
                metric_name="difficulty",
                evaluator_model="mock",
                mean=50.0,
                median=50.0,
                std_dev=0.0,
                min=50.0,
                max=50.0,
                per_run_scores=[50.0, 50.0],
            )
        },
    )

    summary = ResultsReporter.generate_summary(agg)
    assert "BENCHMARK RESULTS SUMMARY" in summary
    assert "difficulty" in summary.lower()
    assert "mock" in summary


def test_generate_comparison_report_no_results():
    agg = AggregatedResults(
        benchmark_config_name="test",
        benchmark_version="1.0",
        quiz_ids=["quiz_1"],
        total_runs=1,
        aggregations={},
    )

    report = ResultsReporter.generate_comparison_report(agg, "difficulty")
    assert "No results found for metric: difficulty" in report


def test_generate_quiz_report():
    metric = MetricResult(
        metric_name="difficulty",
        metric_version="1.0",
        score=40.0,
        evaluator_model="mock",
        quiz_id="quiz_1",
        question_id="q1",
    )

    result = BenchmarkResult(
        benchmark_id="bench_1",
        benchmark_version="1.0",
        config_hash="hash",
        quiz_id="quiz_1",
        run_number=1,
        metrics=[metric],
        started_at=datetime.now(),
        completed_at=datetime.now(),
        metadata={"quiz_title": "Quiz", "num_questions": 1},
    )

    report = ResultsReporter.generate_quiz_report([result], "quiz_1")
    assert "QUIZ REPORT: quiz_1" in report
    assert "difficulty_mock" in report
