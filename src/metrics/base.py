"""Base metric interface."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from ..models.quiz import Quiz, QuizQuestion
from ..models.result import EvaluationResult
from .phase import Phase, PhaseInput, PhaseOutput


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

    Orchestrates the evaluation pipeline by iterating over a metric's
    declared phases in order. Each phase receives a PhaseInput containing
    the source text, quiz, accumulated outputs from all prior phases, and
    the phase's prompt builder. The phase is the sole point of LLM contact.

    Subclasses define their pipeline by implementing the `phases` property
    and `get_prompt_builder()`:
     - Single-stage metrics: declare one Phase.
     - Multi-stage metrics: declare multiple phases in order
       (e.g. extract → map → score).
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

    @property
    @abstractmethod
    def phases(self) -> List[Phase]:
        """Ordered list of phases that define this metric's evaluation pipeline.

        Returns:
            List of Phase instances to execute in order. Each phase's output
            is accumulated and made available to all subsequent phases via
            PhaseInput.accumulated.
        """
        pass

    @abstractmethod
    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        """Return the prompt builder callable for the given phase name."""
        pass

    def evaluate(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        llm_client: Optional[Any] = None,
        **params: Any,
    ) -> EvaluationResult:
        """Evaluate and return a score by executing all declared phases in order.

        Iterates over self.phases, building a PhaseInput for each phase that
        includes the source text, quiz, and all previously accumulated
        PhaseOutputs. Fan-out phases are executed once per question.
        The final phase's output is parsed for the score.

        Args:
            question: Question to evaluate (for question-level metrics).
            quiz: Quiz to evaluate (for quiz-level metrics).
            source_text: Source material text.
            llm_client: LLM provider for generating responses.
            **params: Metric-specific parameters passed to phases.

        Returns:
            EvaluationResult with score and metadata.

        Raises:
            ValueError: If llm_client is None or no phases are declared.
        """
        if llm_client is None:
            raise ValueError(f"{self.name} requires an llm_client")

        if not self.phases:
            raise ValueError(f"{self.name} must declare at least one phase")

        accumulated: Dict[str, PhaseOutput] = {}

        for phase in self.phases:
            builder = self.get_prompt_builder(phase.name)

            if phase.fan_out:
                if quiz is None:
                    raise ValueError(f"Fan-out phase '{phase.name}' requires a quiz")

                results = []
                for q in quiz.questions:
                    inp = PhaseInput(
                        prompt_builder=builder,
                        source_text=source_text,
                        quiz=quiz,
                        question=q,
                        accumulated=accumulated,
                    )
                    results.append(phase.process(inp, llm_client))

                accumulated[phase.name] = PhaseOutput(
                    phase_name=phase.name, data={"results": results}
                )
            else:
                inp = PhaseInput(
                    prompt_builder=builder,
                    source_text=source_text,
                    quiz=quiz,
                    question=question,
                    accumulated=accumulated,
                )
                result_data = phase.process(inp, llm_client)
                accumulated[phase.name] = PhaseOutput(phase_name=phase.name, data=result_data)

            # Final phase determines the score
        final_phase_output = accumulated[self.phases[-1].name]
        score = self.parse_score(final_phase_output)

        return EvaluationResult(
            score=score,
            raw_response=json.dumps(final_phase_output.data, ensure_ascii=True),
            metadata={"phases": {name: output.data for name, output in accumulated.items()}},
        )

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract the final score from the last phase's output.

        Override in subclasses that use a non-standard score field
        (e.g. CoverageMetric uses "final_score" instead of "score").

        Args:
            final_output: PhaseOutput from the last phase in the pipeline.

        Returns:
            Score as a float between 0 and 100.

        Raises:
            ValueError: If the score is missing or out of range.
        """
        score = float(final_output.data["score"])
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")
        return score

    def validate_params(self, **params: Any) -> None:
        """Validate provided parameters against metric's parameter definitions.

        Args:
            **params: Parameters to validate.

        Raises:
            ValueError: If parameters are invalid or of wrong type.
        """
        expected_params = {p.name: p for p in self.parameters}

        for param_name in params:
            if param_name not in expected_params:
                raise ValueError(
                    f"Unknown parameter '{param_name}' for metric '{self.name}'. "
                    f"Expected: {list(expected_params.keys())}"
                )

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
            param_name: Name of the parameter.
            **params: Provided parameters.

        Returns:
            Parameter value from params, or the defined default.

        Raises:
            ValueError: If the parameter is not defined for this metric.
        """
        param_def = next((p for p in self.parameters if p.name == param_name), None)

        if param_def is None:
            raise ValueError(f"Parameter '{param_name}' not defined for metric '{self.name}'")

        return params.get(param_name, param_def.default)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"
