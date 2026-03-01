"""Evaluation phase DTOs for the metric pipeline."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type, Callable
from pydantic import BaseModel
from ..models.quiz import Quiz, QuizQuestion


@dataclass
class PhaseInput:
    """Container for data fed into a phase.

        Attributes:
            prompt_builder: Callable that builds the prompt from this input.
    15            Required — phases will raise if absent.
            source_text: Raw source material text.
            quiz: Full quiz being evaluated.
            question: Current question, populated only during fan-out phases.
            accumulated: Outputs from all previously completed phases, keyed by phase name.
    """

    prompt_builder: Callable[["PhaseInput"], str]
    source_text: Optional[str] = None
    quiz: Optional[Quiz] = None
    question: Optional[QuizQuestion] = None
    accumulated: Dict[str, "PhaseOutput"] = field(default_factory=dict)


@dataclass
class PhaseOutput:
    """DTO returned by a completed phase.

    Attributes:
        phase_name: Name of the phase that produced this output.
        data: Structured LLM response dict, validated against the phase's
            output_schema. For fan-out phases, this is a list of dicts
            under the key "results".
    """

    phase_name: str
    data: Dict[str, Any]


@dataclass
class Phase:
    """A single stage in a metric's evaluation pipeline.

    Each Phase is responsible for building its own prompt from a PhaseInput
    and declaring the schema the LLM response should conform to. The
    evaluation orchestrator in BaseMetric.evaluate() calls build_prompt(),
    runs the LLM call, and stores the result as a PhaseOutput which is
    passed forward to subsequent phases via PhaseInput.accumulated.

    Attributes:
        name: Unique identifier for this phase within the pipeline.
        output_schema: Pydantic model class the LLM response is validated against.
        fan_out: If True, build_prompt() is called once per question in the quiz,
            producing one LLM call per question. Results are collected as a list
            under PhaseOutput.data["results"].
    """

    name: str
    output_schema: Type[BaseModel]
    fan_out: bool = False

    def process(self, phase_input: PhaseInput, llm_client: Any) -> Dict[str, Any]:
        """Builds the prompt from phase_input and calls the LLM."""
        prompt = phase_input.prompt_builder(phase_input)
        result: Dict[str, Any] = llm_client.generate_structured(
            prompt=prompt, schema=self.output_schema
        )
        return result
