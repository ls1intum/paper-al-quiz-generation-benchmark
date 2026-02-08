"""Tests for benchmark runner orchestration."""

from datetime import datetime

import pytest

from src.runners.benchmark import BenchmarkRunner
from src.models.quiz import QuizQuestion, QuestionType
from src.models.config import MetricConfig


def test_runner_produces_expected_results(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    runner = BenchmarkRunner(sample_config)
    results = runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "source text"})

    # runs=2 and 1 quiz => 2 BenchmarkResult entries
    assert len(results) == 2

    # 2 questions => difficulty + clarity are question-level: 2 each
    # coverage is quiz-level: 1
    expected_metric_results = 2 + 2 + 1
    for result in results:
        assert len(result.metrics) == expected_metric_results
        assert result.quiz_id == "quiz_1"
        assert result.started_at <= result.completed_at
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.completed_at, datetime)


def test_runner_skips_missing_evaluator(registered_metrics, mock_llm_provider, sample_quiz):
    # Replace evaluator name with missing to force skip
    from src.models.config import BenchmarkConfig, EvaluatorConfig, InputOutputConfig

    evaluators = {
        "mock_eval": EvaluatorConfig(
            name="mock_eval", provider="mock", model="mock", temperature=0.0, max_tokens=10
        )
    }
    metrics = [
        MetricConfig(
            name="difficulty",
            version="1.0",
            evaluators=["missing_eval"],
            parameters={},
            enabled=True,
        )
    ]
    io_config = InputOutputConfig(
        quiz_directory="data/quizzes",
        source_directory="data/inputs",
        results_directory="data/results",
    )

    config = BenchmarkConfig(
        name="test_benchmark",
        version="1.0",
        runs=1,
        evaluators=evaluators,
        metrics=metrics,
        input_output=io_config,
        metadata={},
    )

    runner = BenchmarkRunner(config)
    results = runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "source text"})
    assert len(results) == 1
    assert results[0].metrics == []


def test_runner_skips_missing_metric(mock_llm_provider, sample_config, sample_quiz):
    # Do not register metrics to force missing metric
    runner = BenchmarkRunner(sample_config)
    results = runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "source text"})
    assert len(results) == 2
    for result in results:
        assert result.metrics == []


def test_runner_errors_on_empty_quizzes(registered_metrics, mock_llm_provider, sample_config):
    runner = BenchmarkRunner(sample_config)
    with pytest.raises(ValueError):
        runner.run(quizzes=[], source_texts={})
