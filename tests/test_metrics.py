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
    [DifficultyMetric, CoverageMetric, ClarityMetric],
)
def test_parse_response_success(metric_cls, response, expected):
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
    [DifficultyMetric, CoverageMetric, ClarityMetric],
)
def test_parse_response_failure(metric_cls, response):
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


def test_coverage_prompt_requires_quiz_and_source():
    metric = CoverageMetric()
    with pytest.raises(ValueError):
        metric.get_prompt(quiz=make_quiz())
    with pytest.raises(ValueError):
        metric.get_prompt(source_text="text")


def test_difficulty_param_validation():
    metric = DifficultyMetric()
    question = make_question()
    with pytest.raises(ValueError):
        metric.get_prompt(question=question, rubric=123)
    with pytest.raises(ValueError):
        metric.get_prompt(question=question, unknown_param="x")


def test_coverage_param_validation():
    metric = CoverageMetric()
    quiz = make_quiz()
    with pytest.raises(ValueError):
        metric.get_prompt(quiz=quiz, source_text="text", granularity=10)
