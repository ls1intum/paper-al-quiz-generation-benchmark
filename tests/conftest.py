"""Shared pytest fixtures for deterministic tests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Type

import pytest
from pydantic import BaseModel

from src.evaluators.base import LLMProvider
from src.evaluators.factory import LLMProviderFactory
from src.metrics.registry import MetricRegistry
from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.metrics.homogeneous_options import HomogeneousOptionsMetric
from src.metrics.accuracy import FactualAccuracyMetric
from src.metrics.answer_key_correctness import AnswerKeyCorrectnessMetric
from src.metrics.objective_alignment import ObjectiveAlignmentMetric
from src.metrics.absence_of_cueing import AbsenceOfCueingMetric
from src.metrics.grammatic import GrammaticalCorrectnessMetric
from src.metrics.cognitive_level import CognitiveLevelMetric
from src.models.config import BenchmarkConfig, EvaluatorConfig, InputOutputConfig, MetricConfig
from src.models.quiz import Quiz, QuizQuestion, QuestionType


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for tests.

    Prompt-sniffing detects which phase is running by inspecting
    JSON key names the prompt asks the LLM to return. All other calls
    fall back to a deterministic hash-based score.
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
    def _answer_key_response() -> Dict[str, Any]:
        return {
            "key_correct": True,
            "defensible_correct_options": ["4"],
            "misclassified_options": [],
            "issue_flags": [],
            "rationale": "Mock answer-key verdict",
        }

    @staticmethod
    def _objective_alignment_response() -> Dict[str, Any]:
        return {
            "alignment_level": "direct",
            "matched_objective_aspects": ["mock aspect"],
            "missing_or_misaligned_aspects": [],
            "rationale": "Mock alignment verdict",
        }

    @staticmethod
    def _grammar_response() -> Dict[str, Any]:
        return {
            "severity": "none",
            "grammar_issues": [],
            "spelling_issues": [],
            "punctuation_issues": [],
            "rationale": "Mock grammar verdict",
        }

    @staticmethod
    def _cueing_response() -> Dict[str, Any]:
        return {
            "cue_present": False,
            "severity": "none",
            "cue_types": [],
            "key_revealed_by": [],
            "rationale": "Mock cueing verdict",
        }

    @staticmethod
    def _clarity_judge_response() -> Dict[str, Any]:
        return {
            "clarity_level": "excellent",
            "question_clarity_issues": [],
            "option_clarity_issues": [],
            "contains_negation": False,
            "rationale": "Mock clarity verdict",
        }

    @staticmethod
    def _distractor_analyze_response() -> Dict[str, Any]:
        return {
            "plausibility_analysis": "mock",
            "misconception_analysis": "mock",
            "discrimination_analysis": "mock",
            "collective_analysis": "mock",
            "difficulty_calibration": "mock",
            "source_grounded": True,
        }

    @staticmethod
    def _distractor_judge_response() -> Dict[str, Any]:
        return {
            "quality_level": "good",
            "deduction_summary": "No issues.",
            "rationale": "Mock distractor verdict",
        }

    @staticmethod
    def _cognitive_level_response() -> Dict[str, Any]:
        return {
            "assigned_level": "UNDERSTAND",
            "rationale": "Mock cognitive level assignment",
        }

    @staticmethod
    def _question_id_from_prompt(prompt: str) -> str:
        """Echo back the question id the prompt asked about, so fan-out phases align."""
        match = re.search(r"Question ID: (\S+)", prompt)
        return match.group(1) if match else "q1"

    @classmethod
    def _homogeneous_analyze_response(cls, prompt: str) -> Dict[str, Any]:
        return {
            "question_id": cls._question_id_from_prompt(prompt),
            "applicable": True,
            "exclusion_reason": None,
            "option_analyses": [],
            "dominant_grammatical_pattern": "noun_phrase",
            "dominant_content_type": "concept_term",
            "structural_outliers": [],
        }

    @classmethod
    def _homogeneous_score_response(cls, prompt: str) -> Dict[str, Any]:
        return {
            "question_id": cls._question_id_from_prompt(prompt),
            "applicable": True,
            "homogeneity_level": "excellent",
            "issues": [],
            "rationale": "Mock homogeneity verdict",
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

    def _sniff_response(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Detect the phase from prompt content and return the appropriate mock response."""
        if '"key_correct"' in prompt:
            return self._answer_key_response()

        if '"alignment_level"' in prompt:
            return self._objective_alignment_response()

        if '"cue_present"' in prompt:
            return self._cueing_response()

        if '"grammar_issues"' in prompt:
            return self._grammar_response()

        # clarity judge (verdict-based)
        if '"clarity_level"' in prompt:
            return self._clarity_judge_response()

        # distractor judge (verdict-based)
        if '"quality_level"' in prompt:
            return self._distractor_judge_response()

        # distractor analyze
        if '"plausibility_analysis"' in prompt and '"source_grounded"' in prompt:
            return self._distractor_analyze_response()

        # cognitive_level judge
        if '"assigned_level"' in prompt and "Bloom" in prompt:
            return self._cognitive_level_response()

        # homogeneous options phases
        if '"dominant_grammatical_pattern"' in prompt:
            return self._homogeneous_analyze_response(prompt)

        if '"homogeneity_level"' in prompt:
            return self._homogeneous_score_response(prompt)

        phase = self._detect_coverage_phase(prompt)
        if phase == "extract":
            return self._coverage_extract_response()
        if phase == "map":
            return self._coverage_map_response()
        if phase == "score":
            return self._coverage_score_response()

        return None

    def _do_generate(
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

        sniffed = self._sniff_response(prompt)
        if sniffed is not None:
            return json.dumps(sniffed)

        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return str(int(digest, 16) % 101)

    def _do_generate_structured(
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

        sniffed = self._sniff_response(prompt)
        if sniffed is not None:
            return sniffed

        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return {"score": float(int(digest, 16) % 101)}


@pytest.fixture
def registered_metrics() -> Iterable[str]:
    MetricRegistry.clear()
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(CoverageMetric)
    MetricRegistry.register(ClarityMetric)
    MetricRegistry.register(HomogeneousOptionsMetric)
    MetricRegistry.register(FactualAccuracyMetric)
    MetricRegistry.register(AnswerKeyCorrectnessMetric)
    MetricRegistry.register(ObjectiveAlignmentMetric)
    MetricRegistry.register(AbsenceOfCueingMetric)
    MetricRegistry.register(GrammaticalCorrectnessMetric)
    MetricRegistry.register(CognitiveLevelMetric)
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
        instructions_directory=str(tmp_path / "instructions"),
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
