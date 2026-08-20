"""Tests for benchmark runner orchestration."""

from datetime import datetime

import pytest

from src.runners.benchmark import BenchmarkRunner
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
        instructions_directory="data/instructions",
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


def test_runner_produces_one_answer_key_result_per_question(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """The metric is question-level: N questions must yield N results, each with a question_id."""
    from dataclasses import replace

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="answer_key_correctness",
                version="1.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    results = BenchmarkRunner(config).run(quizzes=[sample_quiz], source_texts={})

    metrics = results[0].metrics
    assert len(metrics) == len(sample_quiz.questions)
    assert {m.question_id for m in metrics} == {"q1", "q2"}
    for metric in metrics:
        assert metric.metric_name == "answer_key_correctness"
        assert metric.question_id is not None
        assert metric.score in (0.0, 100.0)


def test_runner_produces_one_objective_alignment_result_per_question(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """Items without a stated objective must still yield a result per question."""
    from dataclasses import replace

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="objective_alignment",
                version="1.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    results = BenchmarkRunner(config).run(quizzes=[sample_quiz], source_texts={})

    metrics = results[0].metrics
    assert len(metrics) == len(sample_quiz.questions)
    assert {m.question_id for m in metrics} == {"q1", "q2"}
    for metric in metrics:
        assert metric.metric_name == "objective_alignment"
        # sample_quiz carries no learning objectives, so every item is excluded.
        assert '"applicable": false' in metric.raw_response


def test_runner_expands_homogeneous_options_to_per_question_rows(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """The quiz-level aggregate row is replaced by one row per question."""
    from dataclasses import replace

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="homogeneous_options",
                version="1.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    results = BenchmarkRunner(config).run(quizzes=[sample_quiz], source_texts={})

    metrics = results[0].metrics
    assert len(metrics) == len(sample_quiz.questions)
    assert {m.question_id for m in metrics} == {"q1", "q2"}
    # No aggregate row survives: pooling it with the item scores under one
    # metric_name would corrupt every downstream mean.
    assert all(m.question_id is not None for m in metrics)
    for metric in metrics:
        assert metric.metric_name == "homogeneous_options"
        assert '"severity"' in metric.raw_response
