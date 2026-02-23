"""Base metric interface."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from ..models.quiz import Quiz, QuizQuestion
from ..models.result import EvaluationResult


class MetricScope(str, Enum):
    QUESTION_LEVEL = "question"
    QUIZ_LEVEL = "quiz"


@dataclass
class MetricParameter:
    """Defines a configurable parameter for a metric.

    Attributes:
        name: Parameter name
        param_type: Python type of the parameter
        default: Default value if not specified
        description: Human-readable description
    """

    name: str
    param_type: type
    default: Any
    description: str


class ScoreResponse(BaseModel):
    """Default structured response schema for score-only metrics."""

    score: float = Field(ge=0, le=100)


class BaseMetric(ABC):
    """Abstract base class for all metrics.

    Orchestrates the evaluation pipeline. Subclasses should override specific hook methods depending on their complexity:
    - For single-stage metrics: implement `get_prompt()`.
    - For two-stage metrics (fan-out): implement `get_per_question_prompt()` and `get_per_question_schema()`.
    - For metrics requiring pre-processing (e.g., extracting topics): override `generate_context()`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def scope(self) -> MetricScope:
        pass

    @property
    def parameters(self) -> List[MetricParameter]:
        return []

    def run_stage(
        self,
        prompts: List[str],
        schema: Type[BaseModel],
        llm_client: Any,
    ) -> List[Dict[str, Any]]:
        """Execute N structured LLM calls and return all responses.

        Args:
            prompts: List of prompts, one per LLM call
            schema: Pydantic model class for structured responses
            llm_client: LLM provider for generating responses

        Returns:
            List of structured response dicts, one per prompt
        """
        return [llm_client.generate_structured(prompt=p, schema=schema) for p in prompts]

    def generate_context(self, source_text: Optional[str], llm_client: Any) -> Dict[str, Any]:
        """Hook to generate shared context before per-question fan-out.

        Override in subclasses that require a pre-processing stage, e.g.
        extracting source topics before evaluating individual questions.
        Returns an empty dict by default (no-op for single-stage metrics).

        Args:
            source_text: Raw source material text to extract context from.
            llm_client: LLM provider for generating responses.

        Returns:
            Dict of context data passed downstream to get_per_question_prompt()
            and get_prompt(). Empty dict if no context is needed.
        """
        return {}

    def get_per_question_prompt(
        self,
        question: QuizQuestion,
        source_text: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Generate prompt for per-question fan-out stage.

        Override to enable per-question analysis before final scoring.

        Args:
            question: Question to analyze
            source_text: Raw source material text
            context: Additional info needed for a certain metric (e.g. topics for coverage)

        Returns:
            Prompt string, or None to skip this question
        """
        return None

    def get_per_question_schema(self) -> Type[BaseModel]:
        """Schema for per-question fan-out responses.

        Must override if get_per_question_prompt() is overridden.

        Returns:
            Pydantic model class for structured LLM response
        """
        raise NotImplementedError

    def evaluate(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        llm_client: Optional[Any] = None,
        **params: Any,
    ) -> EvaluationResult:
        """Evaluate and return a score.

        Orchestrates single- and multi-stage evaluation via hook methods:
        - Single-stage: implement get_prompt() only
        - Two-stage: implement get_per_question_prompt() + get_per_question_schema() + get_prompt()
        - Custom: override evaluate() and use run_stage() directly

        Args:
            question: Question to evaluate (for question-level metrics)
            quiz: Quiz to evaluate (for quiz-level metrics)
            source_text: Source material text
            llm_client: LLM provider for generating responses
            **params: Metric-specific parameters

        Returns:
            EvaluationResult with score and metadata
        """
        if llm_client is None:
            raise ValueError(f"{self.name} requires an llm_client")

        # 1. Generate any pre-evaluation context (e.g., source topics for coverage)
        context = self.generate_context(source_text, llm_client) if source_text else {}

        per_question_results = None
        if quiz is not None:
            prompts = [
                # 2. Pass the context down to per-question analysis
                self.get_per_question_prompt(q, source_text or "", context)
                for q in quiz.questions
            ]
            if any(p is not None for p in prompts):
                valid_prompts: List[str] = [p for p in prompts if p is not None]
                per_question_results = self.run_stage(
                    valid_prompts, self.get_per_question_schema(), llm_client
                )

        # 3. Pass the context down to the final scoring prompt
        prompt = self.get_prompt(
            question=question,
            quiz=quiz,
            source_text=source_text,
            per_question_results=per_question_results,
            context=context,
            **params,
        )
        [structured] = self.run_stage([prompt], self.get_response_schema(), llm_client)
        score = self.parse_structured_response(structured)

        return EvaluationResult(
            score=score,
            raw_response=json.dumps(structured, ensure_ascii=True),
            metadata={
                "evaluation_context": context,
                "structured_response": structured,
                "per_question_results": per_question_results,
            },
        )

    def get_response_schema(
        self,
    ) -> Type[BaseModel]:
        """Schema used for structured LLM responses."""
        return ScoreResponse

    def parse_structured_response(self, response: Dict[str, Any]) -> float:
        """Extract score from a structured response payload."""
        score = float(response["score"])
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")
        return score

    @abstractmethod
    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        per_question_results: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        **params: Any,
    ) -> str:
        """Generate the LLM prompt for evaluating this metric.

        Args:
            question: Question to evaluate (for question-level metrics)
            quiz: Quiz to evaluate (for quiz-level metrics)
            source_text: Original source material text
            per_question_results: Responses from stage 1 fan-out, if applicable
            context: Shared context produced by generate_context()
            **params: Metric-specific parameters

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If required inputs are missing
        """
        pass

    def validate_params(self, **params: Any) -> None:
        """Validate provided parameters against metric's parameter definitions.

        Args:
            **params: Parameters to validate

        Raises:
            ValueError: If parameters are invalid
        """
        # Get expected parameters
        expected_params = {p.name: p for p in self.parameters}

        # Check for unknown parameters
        for param_name in params:
            if param_name not in expected_params:
                raise ValueError(
                    f"Unknown parameter '{param_name}' for metric '{self.name}'. "
                    f"Expected: {list(expected_params.keys())}"
                )

        # Check types (basic validation)
        for param_name, param_value in params.items():
            expected_param = expected_params[param_name]
            if not isinstance(param_value, expected_param.param_type):
                raise ValueError(
                    f"Parameter '{param_name}' should be of type "
                    f"{expected_param.param_type.__name__}, "
                    f"got {type(param_value).__name__}"
                )

    def get_param_value(self, param_name: str, **params: Any) -> Any:
        """Get parameter value with fallback to default.

        Args:
            param_name: Name of the parameter
            **params: Provided parameters

        Returns:
            Parameter value (from params or default)

        Raises:
            ValueError: If parameter doesn't exist
        """
        # Find the parameter definition
        param_def = None
        for p in self.parameters:
            if p.name == param_name:
                param_def = p
                break

        if param_def is None:
            raise ValueError(f"Parameter '{param_name}' not defined for metric '{self.name}'")

        # Return provided value or default
        return params.get(param_name, param_def.default)

    def __repr__(self) -> str:
        """String representation of the metric."""
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"
