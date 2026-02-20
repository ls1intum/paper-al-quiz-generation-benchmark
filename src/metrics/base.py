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
    """Defines the scope at which a metric operates."""

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


class BaseMetric(ABC):
    """Abstract base class for all metrics.

    Subclasses must implement the abstract methods to define
    metric behavior and prompt generation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this metric.

        Returns:
            Metric name
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of this metric implementation.

        Returns:
            Version string (e.g., "1.0")
        """
        pass

    @property
    @abstractmethod
    def scope(self) -> MetricScope:
        """Scope at which this metric operates.

        Returns:
            MetricScope.QUESTION_LEVEL or MetricScope.QUIZ_LEVEL
        """
        pass

    @property
    def parameters(self) -> List[MetricParameter]:
        """Configurable parameters for this metric.

        Override in subclass to define custom parameters.

        Returns:
            List of MetricParameter objects
        """
        return []

    def evaluate(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        llm_client: Optional[Any] = None,
        **params: Any,
    ) -> EvaluationResult:
        """
        Evaluate and return a score.

        Default implementation uses get_prompt() + structured parsing.
        Metrics can override this for custom evaluation logic (e.g., multi-stage).

        Args:
            question: Question to evaluate (for question-level metrics)
            quiz: Quiz to evaluate (for quiz-level metrics)
            source_text: Source material text
            llm_client: LLM provider for generating responses
            **params: Metric-specific parameters

        Returns:
            Numeric score (0-100)
        """
        if llm_client is None:
            raise ValueError(f"{self.name} requires an llm_client")

        # Default behavior: single structured output evaluation
        prompt = self.get_prompt(question=question, quiz=quiz, source_text=source_text, **params)
        structured = llm_client.generate_structured(
            prompt=prompt,
            schema=self.get_response_schema(question=question, quiz=quiz, source_text=source_text),
        )
        score = self.parse_structured_response(structured)

        return EvaluationResult(
            score=score,
            raw_response=json.dumps(structured, ensure_ascii=True),
            metadata={"structured_response": structured},
        )

    class ScoreResponse(BaseModel):
        """Default structured response schema for score-only metrics."""

        score: float = Field(ge=0, le=100)

    def get_response_schema(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
    ) -> Type[BaseModel]:
        """Schema used for structured LLM responses."""
        return self.ScoreResponse

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
        **params: Any,
    ) -> str:
        """Generate the LLM prompt for evaluating this metric.

        Args:
            question: Question to evaluate (for question-level metrics)
            quiz: Quiz to evaluate (for quiz-level metrics)
            source_text: Original source material text
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
