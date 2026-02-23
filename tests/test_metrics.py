"""Tests for metric implementations."""

import pytest

from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.metrics.phase import PhaseInput, PhaseOutput
from src.models.quiz import QuizQuestion, QuestionType, Quiz
from tests.conftest import MockLLMProvider


def make_question() -> QuizQuestion:
    return QuizQuestion(
        question_id="q1",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="What is 2+2?",
        options=["2", "3", "4", "5"],
        correct_answer="4",
    )


def make_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz_1",
        title="Test Quiz",
        source_material="source.md",
        questions=[make_question()],
    )


@pytest.mark.parametrize("score", [42.0, 88.0, 85.5])
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric])
def test_simple_metric_parse_score_success(metric_cls, score):
    """Single-stage metrics should parse a PhaseOutput with a valid score."""
    metric = metric_cls()
    output = PhaseOutput(phase_name="scoring", data={"score": score})
    assert metric.parse_score(output) == score


@pytest.mark.parametrize("score", [-1, 101])
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric])
def test_simple_metric_parse_score_failure(metric_cls, score):
    """Single-stage metrics should reject out-of-range scores."""
    metric = metric_cls()
    output = PhaseOutput(phase_name="scoring", data={"score": score})
    with pytest.raises(ValueError):
        metric.parse_score(output)


def test_difficulty_phase_requires_question():
    """DifficultyScorePhase should raise ValueError when question is missing."""
    metric = DifficultyMetric()
    phase = metric.phases[0]
    with pytest.raises(ValueError, match="requires a question"):
        phase.build_prompt(PhaseInput())


def test_clarity_phase_requires_question():
    """ClarityScorePhase should raise ValueError when question is missing."""
    metric = ClarityMetric()
    phase = metric.phases[0]
    with pytest.raises(ValueError, match="requires a question"):
        phase.build_prompt(PhaseInput())


def test_difficulty_phase_builds_prompt():
    """DifficultyScorePhase should return a non-empty prompt string."""
    metric = DifficultyMetric()
    phase = metric.phases[0]
    prompt = phase.build_prompt(PhaseInput(question=make_question()))
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_clarity_phase_builds_prompt():
    """ClarityScorePhase should return a non-empty prompt string."""
    metric = ClarityMetric()
    phase = metric.phases[0]
    prompt = phase.build_prompt(PhaseInput(question=make_question()))
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_difficulty_param_validation():
    """DifficultyMetric should reject invalid param types and unknown params."""
    metric = DifficultyMetric()
    with pytest.raises(ValueError, match="should be of type str"):
        metric.validate_params(rubric=123)
    with pytest.raises(ValueError, match="Unknown parameter"):
        metric.validate_params(unknown_param="x")


def test_coverage_parse_score_success():
    """CoverageMetric should extract final_score from PhaseOutput."""
    metric = CoverageMetric()
    output = PhaseOutput(
        phase_name="coverage_scoring",
        data={
            "final_score": 67.5,
            "sub_scores": {"breadth": 20.0, "depth": 22.5, "balance": 15.0, "critical": 10.0},
            "topics_in_source": [],
            "topics_covered": [],
            "critical_concepts": [],
            "critical_covered": [],
            "breadth_reasoning": "",
            "depth_reasoning": "",
            "balance_reasoning": "",
            "critical_reasoning": "",
        },
    )
    assert metric.parse_score(output) == 67.5


def test_coverage_parse_score_invalid():
    """CoverageMetric should reject out-of-range final_score."""
    metric = CoverageMetric()
    output = PhaseOutput(phase_name="coverage_scoring", data={"final_score": 101})
    with pytest.raises(ValueError):
        metric.parse_score(output)


def test_coverage_scoring_phase_requires_quiz():
    """CoverageScoringPhase should raise ValueError when quiz is missing."""
    metric = CoverageMetric()
    scoring_phase = metric.phases[-1]
    with pytest.raises(ValueError, match="requires a quiz"):
        scoring_phase.build_prompt(PhaseInput(source_text="text"))


def test_coverage_scoring_phase_requires_source_text():
    """CoverageScoringPhase should raise ValueError when source_text is missing."""
    metric = CoverageMetric()
    scoring_phase = metric.phases[-1]
    accumulated = {
        "per_question_mapping": PhaseOutput(
            phase_name="per_question_mapping",
            data={"results": [{"topics": ["t1"], "cognitive_level": "recall"}]},
        )
    }
    with pytest.raises(ValueError, match="requires source_text"):
        scoring_phase.build_prompt(PhaseInput(quiz=make_quiz(), accumulated=accumulated))


def test_coverage_scoring_phase_requires_per_question_results():
    """CoverageScoringPhase should raise ValueError when per_question_mapping is missing."""
    metric = CoverageMetric()
    scoring_phase = metric.phases[-1]
    with pytest.raises(ValueError, match="requires per_question_mapping results"):
        scoring_phase.build_prompt(PhaseInput(quiz=make_quiz(), source_text="text"))


def test_coverage_evaluate_requires_quiz():
    """Coverage evaluate() should raise when quiz is missing."""
    metric = CoverageMetric()
    mock_llm = MockLLMProvider(model="mock-model")
    with pytest.raises(ValueError, match="requires a quiz"):
        metric.evaluate(source_text="text", llm_client=mock_llm)


def test_coverage_evaluate_requires_source_text():
    """Coverage evaluate() should raise when source_text is missing."""
    metric = CoverageMetric()
    mock_llm = MockLLMProvider(model="mock-model")
    with pytest.raises(ValueError, match="requires source_text"):
        metric.evaluate(quiz=make_quiz(), llm_client=mock_llm)


def test_coverage_param_validation():
    """CoverageMetric should validate granularity parameter type."""
    metric = CoverageMetric()
    with pytest.raises(ValueError, match="should be of type str"):
        metric.validate_params(granularity=10)