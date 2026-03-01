"""Shared pytest fixtures for deterministic tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional, Type

import pytest
from pydantic import BaseModel

from src.evaluators.base import LLMProvider
from src.evaluators.factory import LLMProviderFactory
from src.metrics.registry import MetricRegistry
from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.models.config import BenchmarkConfig, EvaluatorConfig, InputOutputConfig, MetricConfig
from src.models.quiz import Quiz, QuizQuestion, QuestionType


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for tests.

    Prompt-sniffing detects which coverage phase is running:
      - extract: prompt contains '"critical_concepts"' and 'must-know'
      - map:     prompt contains '"cognitive_level_score"'
      - score:   prompt contains '"final_score"'
    All other calls fall back to a deterministic hash-based score.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        responses: Optional[Iterable[Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, temperature, max_tokens, **kwargs)
        self._responses = list(responses) if responses is not None else None

    @staticmethod
    def _coverage_extract_response() -> Dict[str, Any]:
        return {
            "topics": ["functions", "data types", "control flow"],
            "critical_concepts": ["functions", "data types"],
        }

    @staticmethod
    def _coverage_map_response() -> Dict[str, Any]:
        return {
            "topics": ["functions"],
            "cognitive_level_label": "understanding",
            "cognitive_level_score": 2,
            "reasoning": "Mock question analysis",
        }

    @staticmethod
    def _coverage_score_response() -> Dict[str, Any]:
        return {
            "final_score": 73.0,
            "sub_scores": {
                "breadth": 20.0,
                "depth": 20.0,
                "balance": 13.0,
                "critical": 20.0,
            },
            "topics_in_source": ["functions", "data types", "control flow"],
            "topics_covered": ["functions", "data types"],
            "critical_concepts": ["functions", "data types"],
            "critical_covered": ["functions", "data types"],
            "breadth_reasoning": "2 of 3 topics covered = 20.0",
            "depth_reasoning": "avg level 2/3 x 30 = 20.0",
            "balance_reasoning": "deduction_a=5, deduction_b=2, balance=13",
            "critical_reasoning": "2 of 2 critical concepts covered = 20.0",
        }

    @staticmethod
    def _detect_coverage_phase(prompt: str) -> Optional[str]:
        """Identify which coverage phase produced this prompt by inspecting
        the JSON key names the prompt asks the LLM to return."""
        if '"critical_concepts"' in prompt and "must-know" in prompt:
            return "extract"
        if '"cognitive_level_score"' in prompt:
            return "map"
        if '"final_score"' in prompt:
            return "score"
        return None

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        if self._responses is not None:
            if not self._responses:
                return "0"
            next_response = self._responses.pop(0)
            return next_response if isinstance(next_response, str) else json.dumps(next_response)

        phase = self._detect_coverage_phase(prompt)
        if phase == "extract":
            return json.dumps(self._coverage_extract_response())
        if phase == "map":
            return json.dumps(self._coverage_map_response())
        if phase == "score":
            return json.dumps(self._coverage_score_response())

        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return str(int(digest, 16) % 101)

    def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self._responses is not None:
            if not self._responses:
                return {"score": 0}
            return self._responses.pop(0)

        phase = self._detect_coverage_phase(prompt)
        if phase == "extract":
            return self._coverage_extract_response()
        if phase == "map":
            return self._coverage_map_response()
        if phase == "score":
            return self._coverage_score_response()

        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return {"score": float(int(digest, 16) % 101)}


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