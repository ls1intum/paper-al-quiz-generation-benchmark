"""I/O utilities for loading and saving data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..models.quiz import Quiz, QuizQuestion, QuestionType
from ..models.result import BenchmarkResult, MetricResult, AggregatedResults


class IOUtils:
    """Utilities for file I/O operations."""

    @staticmethod
    def load_quiz(quiz_path: str) -> Quiz:
        """Load a quiz from JSON file.

        Args:
            quiz_path: Path to quiz JSON file

        Returns:
            Quiz object

        Raises:
            FileNotFoundError: If quiz file doesn't exist
            ValueError: If JSON is invalid
        """
        path = Path(quiz_path)
        if not path.exists():
            raise FileNotFoundError(f"Quiz file not found: {quiz_path}")

        with open(path, "r") as f:
            quiz_dict = json.load(f)

        # Parse questions
        questions = []
        for q_dict in quiz_dict.get("questions", []):
            questions.append(
                QuizQuestion(
                    question_id=q_dict["question_id"],
                    question_type=QuestionType(q_dict["question_type"]),
                    question_text=q_dict["question_text"],
                    options=q_dict["options"],
                    correct_answer=q_dict["correct_answer"],
                    source_reference=q_dict.get("source_reference"),
                    metadata=q_dict.get("metadata", {}),
                )
            )

        # Parse created_at
        created_at = quiz_dict.get("created_at")
        if created_at:
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        quiz = Quiz(
            quiz_id=quiz_dict["quiz_id"],
            title=quiz_dict["title"],
            source_material=quiz_dict["source_material"],
            questions=questions,
            metadata=quiz_dict.get("metadata", {}),
            created_at=created_at,
        )

        return quiz

    @staticmethod
    def load_all_quizzes(quiz_directory: str) -> List[Quiz]:
        """Load all quizzes from a directory.

        Args:
            quiz_directory: Directory containing quiz JSON files

        Returns:
            List of Quiz objects
        """
        quiz_dir = Path(quiz_directory)
        if not quiz_dir.exists():
            raise FileNotFoundError(f"Quiz directory not found: {quiz_directory}")

        quizzes = []
        for quiz_file in quiz_dir.glob("*.json"):
            try:
                quiz = IOUtils.load_quiz(str(quiz_file))
                quizzes.append(quiz)
            except Exception as e:
                print(f"Warning: Failed to load {quiz_file}: {e}")

        return quizzes

    @staticmethod
    def load_source_text(source_path: str) -> str:
        """Load source material text from markdown file.

        Args:
            source_path: Path to source markdown file

        Returns:
            Source text content

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def save_results(
        results: List[BenchmarkResult], output_path: str, pretty: bool = True
    ) -> None:
        """Save benchmark results to JSON file.

        Args:
            results: List of benchmark results
            output_path: Path to output JSON file
            pretty: Whether to pretty-print JSON
        """
        # Convert to dictionaries
        results_dict = []
        for result in results:
            metrics_list = []
            for metric in result.metrics:
                metrics_list.append(
                    {
                        "metric_name": metric.metric_name,
                        "metric_version": metric.metric_version,
                        "score": metric.score,
                        "evaluator_model": metric.evaluator_model,
                        "quiz_id": metric.quiz_id,
                        "question_id": metric.question_id,
                        "parameters": metric.parameters,
                        "evaluated_at": metric.evaluated_at.isoformat(),
                        "raw_response": metric.raw_response,
                    }
                )

            results_dict.append(
                {
                    "benchmark_id": result.benchmark_id,
                    "benchmark_version": result.benchmark_version,
                    "config_hash": result.config_hash,
                    "quiz_id": result.quiz_id,
                    "run_number": result.run_number,
                    "metrics": metrics_list,
                    "started_at": result.started_at.isoformat(),
                    "completed_at": result.completed_at.isoformat(),
                    "metadata": result.metadata,
                }
            )

        # Save to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            if pretty:
                json.dump(results_dict, f, indent=2)
            else:
                json.dump(results_dict, f)

    @staticmethod
    def save_aggregated_results(
        aggregated: AggregatedResults, output_path: str, pretty: bool = True
    ) -> None:
        """Save aggregated results to JSON file.

        Args:
            aggregated: Aggregated results
            output_path: Path to output JSON file
            pretty: Whether to pretty-print JSON
        """
        # Convert aggregations to dict
        aggregations_dict = {}
        for key, agg in aggregated.aggregations.items():
            aggregations_dict[key] = {
                "metric_name": agg.metric_name,
                "evaluator_model": agg.evaluator_model,
                "mean": agg.mean,
                "median": agg.median,
                "std_dev": agg.std_dev,
                "min": agg.min,
                "max": agg.max,
                "per_run_scores": agg.per_run_scores,
                "num_runs": agg.num_runs,
            }

        result_dict = {
            "benchmark_config_name": aggregated.benchmark_config_name,
            "benchmark_version": aggregated.benchmark_version,
            "quiz_ids": aggregated.quiz_ids,
            "total_runs": aggregated.total_runs,
            "aggregations": aggregations_dict,
            "created_at": aggregated.created_at.isoformat(),
            "metadata": aggregated.metadata,
        }

        # Save to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            if pretty:
                json.dump(result_dict, f, indent=2)
            else:
                json.dump(result_dict, f)
