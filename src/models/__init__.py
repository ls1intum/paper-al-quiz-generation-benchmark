"""Data models for quiz benchmark framework."""

from .quiz import Quiz, QuizQuestion, QuestionType
from .result import (
    MetricResult,
    BenchmarkResult,
    AggregatedResults,
    MetricAggregation,
)
from .config import (
    BenchmarkConfig,
    EvaluatorConfig,
    MetricConfig,
    InputOutputConfig,
)

__all__ = [
    "Quiz",
    "QuizQuestion",
    "QuestionType",
    "MetricResult",
    "BenchmarkResult",
    "AggregatedResults",
    "MetricAggregation",
    "BenchmarkConfig",
    "EvaluatorConfig",
    "MetricConfig",
    "InputOutputConfig",
]
