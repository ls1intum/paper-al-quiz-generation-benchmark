"""Shared pytest fixtures for deterministic tests."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Optional

import pytest

from src.evaluators.base import LLMProvider
from src.evaluators.factory import LLMProviderFactory
from src.metrics.registry import MetricRegistry
from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.models.config import BenchmarkConfig, EvaluatorConfig, InputOutputConfig, MetricConfig
from src.models.quiz import Quiz, QuizQuestion, QuestionType


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for tests."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        responses: Optional[Iterable[str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, temperature, max_tokens, **kwargs)
        self._responses = list(responses) if responses is not None else None

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        # If custom responses provided, use those
        if self._responses is not None:
            if not self._responses:
                return "0"
            return self._responses.pop(0)

        # Coverage Stage 1: Question topic extraction
        if "Question #" in prompt and "cognitive_level" in prompt:
            return """{
                "topics": ["test_topic"],
                "cognitive_level": "understanding",
                "reasoning": "Mock question analysis"
            }"""

        # Coverage Stage 2: Overall coverage analysis
        if "Scoring Framework" in prompt or ("sub_scores" in prompt and "final_score" in prompt):
            return """{
                "final_score": 67.5,
                "sub_scores": {
                    "breadth": 20.0,
                    "depth": 22.5,
                    "balance": 15.0,
                    "critical": 10.0
                },
                "topics_in_source": ["topic1", "topic2"],
                "topics_covered": ["topic1"],
                "critical_concepts": ["concept1"],
                "critical_covered": ["concept1"],
                "reasoning": "Mock coverage analysis"
            }"""

        # Default: deterministic score based on prompt hash (for simple metrics)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        score = int(digest, 16) % 101
        return str(score)


@pytest.fixture
def registered_metrics() -> Iterable[str]:
    MetricRegistry.clear()
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(CoverageMetric)
    MetricRegistry.register(ClarityMetric)
    yield MetricRegistry.list_metrics()
    MetricRegistry.clear()


@pytest.fixture
def mock_llm_provider(monkeypatch: pytest.MonkeyPatch) -> Iterable[Dict[str, Any]]:
    original_map = dict(LLMProviderFactory._PROVIDER_MAP)
    monkeypatch.setattr(
        LLMProviderFactory, "_PROVIDER_MAP", {**original_map, "mock": MockLLMProvider}
    )
    yield LLMProviderFactory._PROVIDER_MAP
    monkeypatch.setattr(LLMProviderFactory, "_PROVIDER_MAP", original_map)


@pytest.fixture
def sample_quiz() -> Quiz:
    questions: List[QuizQuestion] = [
        QuizQuestion(
            question_id="q1",
            question_type=QuestionType.SINGLE_CHOICE,
            question_text="What is 2+2?",
            options=["2", "3", "4", "5"],
            correct_answer="4",
        ),
        QuizQuestion(
            question_id="q2",
            question_type=QuestionType.TRUE_FALSE,
            question_text="Python is a snake.",
            options=["True", "False"],
            correct_answer="True",
        ),
    ]

    return Quiz(
        quiz_id="quiz_1",
        title="Sample Quiz",
        source_material="sample.md",
        questions=questions,
    )


@pytest.fixture
def sample_config(tmp_path) -> BenchmarkConfig:
    evaluators = {
        "mock_eval": EvaluatorConfig(
            name="mock_eval",
            provider="mock",
            model="mock-model",
            temperature=0.0,
            max_tokens=100,
        )
    }
    metrics = [
        MetricConfig(
            name="difficulty",
            version="1.0",
            evaluators=["mock_eval"],
            parameters={"rubric": "bloom_taxonomy", "target_audience": "undergraduate"},
            enabled=True,
        ),
        MetricConfig(
            name="coverage",
            version="1.0",
            evaluators=["mock_eval"],
            parameters={"granularity": "balanced"},
            enabled=True,
        ),
        MetricConfig(
            name="clarity",
            version="1.0",
            evaluators=["mock_eval"],
            parameters={},
            enabled=True,
        ),
    ]
    io_config = InputOutputConfig(
        quiz_directory=str(tmp_path / "quizzes"),
        source_directory=str(tmp_path / "sources"),
        results_directory=str(tmp_path / "results"),
    )

    return BenchmarkConfig(
        name="test_benchmark",
        version="1.0",
        runs=2,
        evaluators=evaluators,
        metrics=metrics,
        input_output=io_config,
        metadata={},
    )
