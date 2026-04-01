"""Tests for I/O utilities."""

import json
from datetime import datetime

import pytest

from src.utils.io import IOUtils
from src.models.quiz import QuizQuestion, QuestionType, Quiz
from src.models.result import BenchmarkResult, MetricResult, AggregatedResults, MetricAggregation


def test_load_quiz_and_all_quizzes(tmp_path):
    quiz_data = {
        "quiz_id": "quiz_1",
        "title": "Test Quiz",
        "source_material": "source.md",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "single_choice",
                "question_text": "What is 2+2?",
                "options": ["2", "3", "4"],
                "correct_answer": "4",
            }
        ],
    }

    quiz_dir = tmp_path / "quizzes"
    quiz_dir.mkdir()
    quiz_path = quiz_dir / "quiz.json"
    quiz_path.write_text(json.dumps(quiz_data))

    quiz = IOUtils.load_quiz(str(quiz_path))
    assert quiz.quiz_id == "quiz_1"
    assert quiz.num_questions == 1

    quizzes = IOUtils.load_all_quizzes(str(quiz_dir))
    assert len(quizzes) == 1

    quizzes_single = IOUtils.load_all_quizzes(str(quiz_path))
    assert len(quizzes_single) == 1
    assert quizzes_single[0].quiz_id == "quiz_1"

def test_load_all_quizzes_skips_invalid(tmp_path):
    quiz_dir = tmp_path / "quizzes"
    quiz_dir.mkdir()

    # valid quiz
    valid = {
        "quiz_id": "quiz_valid",
        "title": "Valid",
        "source_material": "source.md",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "single_choice",
                "question_text": "Q?",
                "options": ["A"],
                "correct_answer": "A",
            }
        ],
    }
    (quiz_dir / "valid.json").write_text(json.dumps(valid))

    # invalid quiz (missing required fields)
    (quiz_dir / "invalid.json").write_text("{}")

    quizzes = IOUtils.load_all_quizzes(str(quiz_dir))
    assert len(quizzes) == 1
    assert quizzes[0].quiz_id == "quiz_valid"

def test_load_quiz_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        IOUtils.load_quiz(str(tmp_path / "nonexistent.json"))

def test_load_all_quizzes_directory_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        IOUtils.load_all_quizzes(str(tmp_path / "nonexistent"))

def test_load_source_text_markdown(tmp_path):
    source_path = tmp_path / "source.md"
    source_path.write_text("hello")
    assert IOUtils.load_source_text(str(source_path)) == "hello"

def test_load_source_text_unsupported_format(tmp_path):
    source_path = tmp_path / "source.txt"
    source_path.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file format"):
        IOUtils.load_source_text(str(source_path))

def test_load_source_text_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        IOUtils.load_source_text(str(tmp_path / "nonexistent.md"))

def test_save_results_and_aggregated_results(tmp_path):
    question = QuizQuestion(
        question_id="q1",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="Test",
        options=["A", "B"],
        correct_answer="A",
    )
    quiz = Quiz(
        quiz_id="quiz_1",
        title="Test Quiz",
        source_material="source.md",
        questions=[question],
    )

    metric_result = MetricResult(
        metric_name="difficulty",
        metric_version="1.0",
        score=50.0,
        evaluator_model="mock",
        quiz_id=quiz.quiz_id,
        question_id=question.question_id,
    )

    result = BenchmarkResult(
        benchmark_id="bench_1",
        benchmark_version="1.0",
        config_hash="hash",
        quiz_id=quiz.quiz_id,
        run_number=1,
        metrics=[metric_result],
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )

    output_path = tmp_path / "results.json"
    IOUtils.save_results([result], str(output_path))
    assert output_path.exists()

    # verify saved content is valid JSON with expected fields
    saved = json.loads(output_path.read_text())
    assert len(saved) == 1
    assert saved[0]["quiz_id"] == "quiz_1"
    assert saved[0]["metrics"][0]["metric_name"] == "difficulty"

    agg = AggregatedResults(
        benchmark_config_name="test",
        benchmark_version="1.0",
        quiz_ids=[quiz.quiz_id],
        total_runs=1,
        aggregations={
            "difficulty_mock": MetricAggregation(
                metric_name="difficulty",
                evaluator_model="mock",
                mean=50.0,
                median=50.0,
                std_dev=0.0,
                min=50.0,
                max=50.0,
                per_run_scores=[50.0],
            )
        },
    )

    agg_path = tmp_path / "agg.json"
    IOUtils.save_aggregated_results(agg, str(agg_path))
    assert agg_path.exists()

    saved_agg = json.loads(agg_path.read_text())
    assert saved_agg["benchmark_config_name"] == "test"
    assert "difficulty_mock" in saved_agg["aggregations"]