"""Tests for metric implementations."""

import pytest

from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.models.quiz import QuizQuestion, QuestionType, Quiz


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


@pytest.mark.parametrize(
    "response,expected",
    [
        ("42", 42.0),
        ("Score: 88", 88.0),
        ("85.5", 85.5),
    ],
)
@pytest.mark.parametrize(
    "metric_cls",
    [DifficultyMetric, ClarityMetric],  # Only simple metrics
)
def test_simple_metric_parse_response_success(metric_cls, response, expected):
    """Simple metrics should parse numeric responses."""
    metric = metric_cls()
    assert metric.parse_response(response) == expected


@pytest.mark.parametrize(
    "response",
    [
        "no number",
        "101",
    ],
)
@pytest.mark.parametrize(
    "metric_cls",
    [DifficultyMetric, ClarityMetric],  # Only simple metrics
)
def test_simple_metric_parse_response_failure(metric_cls, response):
    """Simple metrics should reject invalid responses."""
    metric = metric_cls()
    with pytest.raises(ValueError):
        metric.parse_response(response)


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


def test_coverage_parse_json_response():
    """Coverage should parse JSON responses with final_score."""
    metric = CoverageMetric()

    json_response = """{
        "final_score": 67.5,
        "sub_scores": {
            "breadth": 20.0,
            "depth": 22.5,
            "balance": 15.0,
            "critical": 10.0
        }
    }"""

    assert metric.parse_response(json_response) == 67.5


def test_coverage_parse_simple_fallback():
    """Coverage should fall back to parsing simple numbers."""
    metric = CoverageMetric()

    # Fallback patterns for compatibility
    assert metric.parse_response("42") == 42.0
    assert metric.parse_response("Score: 88") == 88.0
    assert metric.parse_response("85.5") == 85.5


def test_coverage_parse_invalid_response():
    """Coverage should reject responses without valid scores."""
    metric = CoverageMetric()

    with pytest.raises(ValueError):
        metric.parse_response("no number")

    with pytest.raises(ValueError):
        metric.parse_response("101")


def test_coverage_get_prompt_not_implemented():
    """Coverage should raise NotImplementedError for get_prompt()."""
    metric = CoverageMetric()

    with pytest.raises(NotImplementedError, match="two-stage evaluation"):
        metric.get_prompt(quiz=make_quiz())


def test_coverage_evaluate_requires_quiz():
    """Coverage evaluate() should require quiz parameter."""
    metric = CoverageMetric()

    with pytest.raises(ValueError, match="requires a quiz"):
        metric.evaluate(source_text="text", llm_client=None)


def test_coverage_evaluate_requires_source_text():
    """Coverage evaluate() should require source_text parameter."""
    metric = CoverageMetric()

    with pytest.raises(ValueError, match="requires source_text"):
        metric.evaluate(quiz=make_quiz(), llm_client=None)


def test_coverage_param_validation():
    """Coverage should validate granularity parameter type."""
    from tests.conftest import MockLLMProvider

    metric = CoverageMetric()
    quiz = make_quiz()
    mock_llm = MockLLMProvider(model="mock-model")

    # Invalid type (int instead of str)
    with pytest.raises(ValueError, match="should be of type str"):
        metric.evaluate(
            quiz=quiz, source_text="text", llm_client=mock_llm, granularity=10  # Wrong type
        )
