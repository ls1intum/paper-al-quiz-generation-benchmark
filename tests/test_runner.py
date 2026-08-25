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
        assert '"homogeneity_level"' in metric.raw_response


def test_runner_produces_one_cueing_result_per_question(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """Cueing is question-level: N questions must yield N results, each with a question_id."""
    from dataclasses import replace

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="absence_of_cueing",
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
        assert metric.metric_name == "absence_of_cueing"
        assert metric.question_id is not None
        assert metric.score in (0.0, 100.0)


def _grammar_only_config(sample_config):
    from dataclasses import replace

    return replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="grammatical_correctness",
                version="2.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )


def test_runner_produces_one_grammar_result_per_question(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """Grammar is now scored per item, so one broken item can no longer hide in a quiz mean."""
    results = BenchmarkRunner(_grammar_only_config(sample_config)).run(
        quizzes=[sample_quiz], source_texts={}
    )

    metrics = results[0].metrics
    assert len(metrics) == len(sample_quiz.questions)
    assert {m.question_id for m in metrics} == {"q1", "q2"}
    for metric in metrics:
        assert metric.metric_name == "grammatical_correctness"
        assert metric.question_id is not None
        assert metric.score in (0.0, 33.3, 66.7, 100.0)

    # No language instruction -> no compliance call, nothing to record.
    assert results[0].metadata["adjusted_grammar"] is None


def test_runner_language_compliance_does_not_touch_item_scores(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz, tmp_path
):
    """A language mismatch is an instruction failure, not a grammar defect."""
    import json as _json
    from dataclasses import replace

    instructions_dir = tmp_path / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)
    (instructions_dir / "intent.json").write_text(_json.dumps({"language": "German"}))

    config = _grammar_only_config(sample_config)
    config = replace(
        config,
        input_output=replace(config.input_output, instructions_directory=str(instructions_dir)),
    )
    quiz = replace(sample_quiz, instructions="intent.json")

    results = BenchmarkRunner(config).run(quizzes=[quiz], source_texts={})
    metrics = results[0].metrics

    # Per-question rows stay pure grammar...
    assert len(metrics) == len(quiz.questions)
    for metric in metrics:
        assert metric.score in (0.0, 33.3, 66.7, 100.0)
    # ...and the compliance verdict is recorded once, beside the difficulty one,
    # computed from those same rows (the mock returns a zero adjustment, so the
    # value must be exactly their mean -- proving the aggregation path ran).
    expected_mean = round(sum(m.score for m in metrics) / len(metrics), 1)
    assert results[0].metadata["adjusted_grammar"] == expected_mean


def test_runner_raises_when_metric_fails_every_question(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """P0-2a: if a question-level metric fails for every question, the runner must raise."""
    from dataclasses import replace
    from unittest.mock import patch

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="clarity",
                version="2.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    runner = BenchmarkRunner(config)

    # Make the metric's evaluate() always raise
    with patch.object(
        runner.metrics["clarity"],
        "evaluate",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="failed for every question"):
            runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "text"})


def test_runner_tolerates_partial_question_failure(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """If only some questions fail, the runner continues and includes the rest."""
    from dataclasses import replace
    from unittest.mock import patch

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="clarity",
                version="2.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    runner = BenchmarkRunner(config)

    original_evaluate = runner.metrics["clarity"].evaluate
    call_count = [0]

    def fail_first(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("boom")
        return original_evaluate(*args, **kwargs)

    with patch.object(runner.metrics["clarity"], "evaluate", side_effect=fail_first):
        results = runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "text"})

    # One question failed, one succeeded
    assert len(results[0].metrics) == 1


def test_evaluator_init_failure_raises(monkeypatch, sample_config):
    """A declared evaluator that cannot be created must abort the run, not be skipped.

    Silently dropping one leaves a sweep with fewer judges than planned, visible only in
    metadata.json after the calls have been spent -- and two of the four models reported in
    the paper are locally served.
    """
    from src.evaluators.factory import LLMProviderFactory
    from src.runners.benchmark import BenchmarkRunner

    def boom(cfg):
        raise ConnectionError("model not served")

    monkeypatch.setattr(LLMProviderFactory, "create", staticmethod(boom))
    with pytest.raises(RuntimeError, match="Failed to initialize evaluator"):
        BenchmarkRunner(sample_config)


def test_usage_accumulator():
    """Base accumulator: reset, record, read."""
    from tests.conftest import MockLLMProvider

    provider = MockLLMProvider(model="test")
    provider.reset_usage()
    assert provider.get_accumulated_usage() == {"prompt_tokens": 0, "completion_tokens": 0}

    # Simulate two LLM calls
    class FakeMsg:
        usage_metadata = {"input_tokens": 100, "output_tokens": 25}

    provider._record_usage(FakeMsg())
    provider._record_usage(FakeMsg())
    usage = provider.get_accumulated_usage()
    assert usage == {"prompt_tokens": 200, "completion_tokens": 50}

    provider.reset_usage()
    assert provider.get_accumulated_usage() == {"prompt_tokens": 0, "completion_tokens": 0}


def test_metric_results_carry_usage_field(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """Every MetricResult must have a usage dict (zeroes from mock, but present)."""
    runner = BenchmarkRunner(sample_config)
    results = runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "source text"})

    for result in results:
        for m in result.metrics:
            assert m.usage is not None, f"{m.metric_name} missing usage"
            assert "prompt_tokens" in m.usage
            assert "completion_tokens" in m.usage


def test_runner_populates_phase_details_on_metadata(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """BenchmarkResult.metadata must contain phase_details with phase data for each evaluation."""
    runner = BenchmarkRunner(sample_config)
    results = runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "source text"})

    for result in results:
        assert "phase_details" in result.metadata
        details = result.metadata["phase_details"]
        assert len(details) > 0
        for entry in details:
            assert "metric_name" in entry
            assert "evaluator_model" in entry
            assert "quiz_id" in entry
            assert "run_number" in entry
            assert "phases" in entry
            assert isinstance(entry["phases"], dict)


def test_transient_503_is_retried():
    """Transient 503 triggers retry and succeeds on second attempt."""
    from unittest.mock import patch

    from tests.conftest import MockLLMProvider

    provider = MockLLMProvider(model="test")

    class FakeAPIError(Exception):
        status_code = 503

    call_count = [0]

    def fail_then_succeed(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise FakeAPIError("Service Unavailable")
        return "success"

    with (
        patch.object(provider, "_do_generate", side_effect=fail_then_succeed),
        patch("src.evaluators.base.time.sleep") as mock_sleep,
    ):
        result = provider.generate("test prompt")

    assert result == "success"
    assert call_count[0] == 2
    mock_sleep.assert_called_once()


def test_non_transient_400_not_retried():
    """Non-transient 400 propagates immediately without retry."""
    from unittest.mock import patch

    from tests.conftest import MockLLMProvider

    provider = MockLLMProvider(model="test")

    class FakeAPIError(Exception):
        status_code = 400

    with (
        patch.object(provider, "_do_generate", side_effect=FakeAPIError("Bad Request")),
        patch("src.evaluators.base.time.sleep") as mock_sleep,
    ):
        with pytest.raises(FakeAPIError):
            provider.generate("test prompt")

    mock_sleep.assert_not_called()


def test_transient_failure_reports_incomplete(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """TransientLLMError marks the run as incomplete."""
    from dataclasses import replace
    from unittest.mock import patch

    from src.evaluators.base import TransientLLMError

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="clarity",
                version="2.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    runner = BenchmarkRunner(config)

    original_evaluate = runner.metrics["clarity"].evaluate
    call_count = [0]

    def fail_first(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise TransientLLMError("timeout", original=TimeoutError(), attempts=4)
        return original_evaluate(*args, **kwargs)

    with patch.object(runner.metrics["clarity"], "evaluate", side_effect=fail_first):
        runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "text"})

    report = runner.get_completeness_report()
    assert not report["complete"]
    assert report["failed"] == 1
    assert len(report["failed_cells"]) == 1
    assert report["failed_cells"][0]["category"] == "transient"


def test_skipped_error_does_not_fail_completeness(
    registered_metrics, mock_llm_provider, sample_config, sample_quiz
):
    """A ValueError (e.g. distractor on true/false) is a skip, not a failure."""
    from dataclasses import replace
    from unittest.mock import patch

    config = replace(
        sample_config,
        runs=1,
        metrics=[
            MetricConfig(
                name="clarity",
                version="2.0",
                evaluators=["mock_eval"],
                parameters={},
                enabled=True,
            )
        ],
    )
    runner = BenchmarkRunner(config)

    original_evaluate = runner.metrics["clarity"].evaluate
    call_count = [0]

    def skip_first(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("Not applicable for true/false")
        return original_evaluate(*args, **kwargs)

    with patch.object(runner.metrics["clarity"], "evaluate", side_effect=skip_first):
        runner.run(quizzes=[sample_quiz], source_texts={"quiz_1": "text"})

    report = runner.get_completeness_report()
    assert report["complete"]
    assert report["skipped"] == 1
    assert len(report["skipped_cells"]) == 1
