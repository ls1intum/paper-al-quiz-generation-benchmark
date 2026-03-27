"""Evaluation phase DTOs for the metric pipeline."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel

from ..models.quiz import Quiz, QuizQuestion
from ..models.instruction import QuizInstructions


@dataclass
class PhaseInput:
    """Container for data fed into a phase.

    Attributes:
        prompt_builder: Callable that builds the prompt from this input.
            Optional for deterministic Python phases.
        source_text: Raw source material text.
        quiz: Full quiz being evaluated.
        question: Current question, populated only during fan-out phases.
        params: Metric-specific runtime parameters passed from evaluate(), used by prompt builders.
        accumulated: Outputs from all previously completed phases, keyed by phase name.
    """

    prompt_builder: Optional[Callable[["PhaseInput"], str]]
    source_text: Optional[str] = None
    quiz: Optional[Quiz] = None
    question: Optional[QuizQuestion] = None
    params: Dict[str, Any] = field(default_factory=dict)
    accumulated: Dict[str, "PhaseOutput"] = field(default_factory=dict)
    instructions: Optional["QuizInstructions"] = None


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

    Each Phase declares the schema its output should conform to. A phase can
    either call the LLM using a prompt_builder or use a deterministic Python
    processor. The evaluation orchestrator in BaseMetric.evaluate() calls
    Phase.process() and stores the validated result as a PhaseOutput which is
    passed forward to subsequent phases via PhaseInput.accumulated.

    Attributes:
        name: Unique identifier for this phase within the pipeline.
        output_schema: Pydantic model class the LLM response is validated against.
        fan_out: If True, the phase runs once per question in the quiz.
        processor: Optional deterministic Python processor. When present, this
            is used instead of an LLM call.
    """

    name: str
    output_schema: Type[BaseModel]
    fan_out: bool = False
    processor: Optional[Callable[[PhaseInput], Dict[str, Any]]] = None

    def process(self, phase_input: PhaseInput, llm_client: Any) -> Dict[str, Any]:
        """Run the phase and validate the result against output_schema."""
        if self.processor is not None:
            result = self.processor(phase_input)
        else:
            if phase_input.prompt_builder is None:
                raise ValueError(f"Phase '{self.name}' requires a prompt_builder")
            prompt = phase_input.prompt_builder(phase_input)
            result = llm_client.generate_structured(prompt=prompt, schema=self.output_schema)

        validated = self.output_schema.model_validate(result)
        return validated.model_dump()
