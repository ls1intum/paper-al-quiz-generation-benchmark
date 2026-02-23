"""Tests for metric implementations."""

import pytest

from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
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
def test_simple_metric_parse_structured_response_success(metric_cls, score):
    """Simple metrics should parse structured score responses."""
    metric = metric_cls()
    assert metric.parse_structured_response({"score": score}) == score


@pytest.mark.parametrize("score", [-1, 101])
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric])
def test_simple_metric_parse_structured_response_failure(metric_cls, score):
    """Simple metrics should reject out-of-range structured scores."""
    metric = metric_cls()
    with pytest.raises(ValueError):
        metric.parse_structured_response({"score": score})


def test_difficulty_prompt_requires_question():
    metric = DifficultyMetric()
    with pytest.raises(ValueError):
        metric.get_prompt()


def test_clarity_prompt_requires_question():
    metric = ClarityMetric()
    with pytest.raises(ValueError):
        metric.get_prompt()


def test_difficulty_param_validation():
    metric = DifficultyMetric()
    question = make_question()
    with pytest.raises(ValueError):
        metric.get_prompt(question=question, rubric=123)
    with pytest.raises(ValueError):
        metric.get_prompt(question=question, unknown_param="x")


def test_coverage_parse_structured_response():
    """Coverage should parse structured responses with final_score."""
    metric = CoverageMetric()

    response = {
        "final_score": 67.5,
        "sub_scores": {
            "breadth": 20.0,
            "depth": 22.5,
            "balance": 15.0,
            "critical": 10.0
        },
    }

    assert metric.parse_structured_response(response) == 67.5


def test_coverage_parse_structured_invalid_response():
    """Coverage should reject invalid structured scores."""
    metric = CoverageMetric()

    with pytest.raises(ValueError):
        metric.parse_structured_response({"final_score": 101})


def test_coverage_get_prompt_not_implemented():
    """Coverage get_prompt() should raise ValueError when per_question_results is missing."""
    metric = CoverageMetric()
    with pytest.raises(ValueError, match="requires per_question_results"):
        metric.get_prompt(quiz=make_quiz(), source_text="some text")


def test_coverage_evaluate_requires_quiz():
    """Coverage evaluate() should require quiz parameter."""
    metric = CoverageMetric()
    mock_llm = MockLLMProvider(model="mock-model")
    with pytest.raises(ValueError, match="requires a quiz"):
        metric.evaluate(source_text="text", llm_client=mock_llm)


def test_coverage_evaluate_requires_source_text():
    metric = CoverageMetric()
    mock_llm = MockLLMProvider(model="mock-model")
    with pytest.raises(ValueError, match="requires source_text"):
        metric.evaluate(quiz=make_quiz(), llm_client=mock_llm)


def test_coverage_param_validation():
    """Coverage should validate granularity parameter type."""
    metric = CoverageMetric()
    with pytest.raises(ValueError, match="should be of type str"):
        metric.validate_params(granularity=10)
