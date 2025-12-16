"""Tests for data models."""

import pytest
from datetime import datetime

from src.models.quiz import Quiz, QuizQuestion, QuestionType
from src.models.result import MetricResult, BenchmarkResult, MetricAggregation


def test_quiz_question_creation():
    """Test creating a quiz question."""
    question = QuizQuestion(
        question_id="q1",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="What is 2+2?",
        options=["2", "3", "4", "5"],
        correct_answer="4",
    )

    assert question.question_id == "q1"
    assert question.question_type == QuestionType.SINGLE_CHOICE
    assert question.correct_answer == "4"


def test_true_false_validation():
    """Test that true/false questions are validated correctly."""
    with pytest.raises(ValueError):
        QuizQuestion(
            question_id="q1",
            question_type=QuestionType.TRUE_FALSE,
            question_text="Is Python great?",
            options=["Yes", "No"],  # Should be ["True", "False"]
            correct_answer="Yes",
        )


def test_quiz_creation():
    """Test creating a quiz."""
    questions = [
        QuizQuestion(
            question_id="q1",
            question_type=QuestionType.SINGLE_CHOICE,
            question_text="Question 1",
            options=["A", "B", "C"],
            correct_answer="A",
        ),
    ]

    quiz = Quiz(
        quiz_id="quiz_1",
        title="Test Quiz",
        source_material="test.md",
        questions=questions,
    )

    assert quiz.quiz_id == "quiz_1"
    assert quiz.num_questions == 1
    assert quiz.get_question_by_id("q1") is not None


def test_metric_result_score_validation():
    """Test that metric results validate score range."""
    with pytest.raises(ValueError):
        MetricResult(
            metric_name="test",
            metric_version="1.0",
            score=150,  # Invalid: > 100
            evaluator_model="gpt-4",
            quiz_id="quiz_1",
        )


def test_metric_aggregation():
    """Test metric aggregation creation."""
    agg = MetricAggregation(
        metric_name="difficulty",
        evaluator_model="gpt-4",
        mean=65.5,
        median=67.0,
        std_dev=8.2,
        min=55.0,
        max=74.0,
        per_run_scores=[55.0, 67.0, 74.0],
    )

    assert agg.num_runs == 3
    assert agg.mean == 65.5
