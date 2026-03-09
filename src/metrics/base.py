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
from ..models.instruction import QuizInstructions


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


class ScoreResponse(BaseModel):
    """Default structured response schema for score-only metrics."""

    score: float = Field(ge=0, le=100)


class CustomPromptContext(BaseModel):
    """Structured output from interpreting instructions.custom_prompt."""

    interpreted_instruction: str = Field(
        description=(
            "A clear, concise restatement of the user's intent, "
            "suitable for injecting into a scoring prompt."
        )
    )


class CustomPromptAdjustment(BaseModel):
    """Structured output from the custom_prompt adjustment call."""

    relevant: bool = Field(
        description="Whether the custom_prompt instruction is relevant to this metric."
    )
    reasoning: str = Field(
        description="Explanation of why the score was adjusted, increased, or left unchanged."
    )
    adjustment: float = Field(
        description=(
            "Score adjustment to apply. "
            "Positive (+5 to +20) rewards exceptional compliance or hitting specific requested features. "
            "Negative (-5 to -50) penalizes partial or total non-compliance. "
            "0 if the instruction is irrelevant or just meets baseline expectations without standing out."
        )
    )


class BaseMetric(ABC):
    """Abstract base class for all metrics.

    Orchestrates the evaluation pipeline by iterating over a metric's
    declared phases in order. Each phase receives a PhaseInput containing
    the source text, quiz, accumulated outputs from all prior phases, and
    the phase's prompt builder. The phase is the sole point of LLM contact.

    When instructions.custom_prompt is set, evaluate() runs two additional
    LLM calls automatically:
      1. interpret_custom_prompt() — once, before any phase runs. Interprets
         the free-text prompt into a clear directive stored in
         accumulated["custom_prompt_context"].
      2. adjust_score_for_custom_prompt() — once, after all phases complete.
         The LLM decides whether the instruction is relevant to this specific
         metric and what adjustment (positive, negative, or zero) to apply.
         The adjustment is applied in Python and clamped to [0, 100].

    Subclasses define their pipeline by implementing the `phases` property
    and `get_prompt_builder()`. They do not need to handle custom_prompt at all.
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
        pass

    @abstractmethod
    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        pass

    def interpret_custom_prompt(
        self,
        custom_prompt: str,
        llm_client: Any,
    ) -> Dict[str, Any]:
        """Interpret free-text custom_prompt into a single clear directive.

        Called once at the start of evaluate() when instructions.custom_prompt
        is set. The result is stored in accumulated["custom_prompt_context"]
        and is available to all subsequent phases via PhaseInput.accumulated.

        Args:
            custom_prompt: Free-text constraint from QuizInstructions.
            llm_client: LLM provider used for interpretation.

        Returns:
            Dict with key: interpreted_instruction.
        """
        prompt = (
            "You are analysing the intent behind a quiz generation instruction.\n\n"
            f'Instruction: "{custom_prompt}"\n\n'
            "Restate the instruction as a single clear, concise directive "
            "suitable for injecting into a quiz scoring prompt. "
            "Do not add assumptions — only reflect what is explicitly stated.\n\n"
            "Return a JSON object with a single key: 'interpreted_instruction'."
        )

        result: Dict[str, Any] = llm_client.generate_structured(
            prompt=prompt,
            schema=CustomPromptContext,
        )

        return result

    def adjust_score_for_custom_prompt(
        self,
        raw_score: float,
        interpreted_instruction: str,
        quiz: Optional[Quiz],
        source_text: Optional[str],
        llm_client: Any,
    ) -> float:
        """Apply a custom_prompt compliance adjustment to the raw metric score.

        Called once after all phases complete, only when instructions.custom_prompt
        is set. The LLM decides:
          - Whether the instruction is even relevant to this metric.
          - If relevant, what adjustment to apply (positive, negative, or zero).

        The adjustment is applied in Python and clamped to [0, 100], so the LLM
        only controls the delta — not the final value directly.

        Args:
            raw_score: Score produced by the metric's phases.
            interpreted_instruction: Output of interpret_custom_prompt().
            quiz: The quiz being evaluated.
            source_text: The source material text.
            llm_client: LLM provider for the adjustment call.

        Returns:
            Adjusted score clamped to [0, 100].
        """
        quiz_summary = ""
        if quiz:
            question_lines = "\n".join(
                f"- [{q.question_type.value}] {q.question_text[:120]}" for q in quiz.questions
            )
            quiz_summary = f"**Quiz title**: {quiz.title}\n**Questions**:\n{question_lines}"

        prompt = f"""You are reviewing whether a quiz respects a user instruction, 
in the context of the metric: '{self.name}'.

**User instruction**:
{interpreted_instruction}

**Source material (excerpt)**:
{(source_text or '')[:500]}

{quiz_summary}

**Raw score from '{self.name}' metric**: {raw_score}/100

Your task:
1. Decide whether this instruction is relevant to the '{self.name}' metric.
   - If NOT relevant (e.g. the instruction is about topics but this metric measures grammar),
     set relevant=false and adjustment=0.
2. If relevant, assess how well the quiz complies with the instruction:
   - Exceptional compliance (hits the requested target perfectly) → positive adjustment (+5 to +20).
   - Baseline compliance (technically follows the rule but nothing special) → adjustment=0.
   - Partial compliance → moderate negative adjustment (-10 to -20).
   - Total non-compliance → large negative adjustment (-30 to -50).
3. Reason carefully about magnitude. The adjustment should be proportional to the
   degree of violation or success.

Respond with ONLY this JSON object:
{{
  "relevant": true/false,
  "reasoning": "explanation of compliance assessment and adjustment rationale",
  "adjustment": <float>
}}"""

        result = llm_client.generate_structured(
            prompt=prompt,
            schema=CustomPromptAdjustment,
        )

        adjustment = float(result.get("adjustment", 0.0))
        reasoning = result.get("reasoning", "No reasoning provided.")
        relevant = result.get("relevant", False)

        print("\n" + "⚠️" * 25)
        print(f"🎯 CUSTOM PROMPT PENALTY TRIGGERED ({self.name.upper()})")
        print(f"   Raw Score Before:  {raw_score}")
        print(f"   Relevant to rule?: {relevant}")
        print(f"   Adjustment Appld:  {adjustment} points")
        print(f"   LLM Reasoning:     {reasoning}")
        print("⚠️" * 25 + "\n")

        adjusted = raw_score + adjustment
        return round(max(0.0, min(100.0, adjusted)), 1)

    def evaluate(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        llm_client: Optional[Any] = None,
        instructions: Optional[QuizInstructions] = None,
        **params: Any,
    ) -> EvaluationResult:
        """Evaluate and return a score by executing all declared phases in order.

        When instructions.custom_prompt is set:
          - interpret_custom_prompt() runs before any phase and stores its output
            in accumulated["custom_prompt_context"].
          - adjust_score_for_custom_prompt() runs after all phases and applies a
            compliance adjustment to the raw score in Python.

        Args:
            question: Question to evaluate (for question-level metrics).
            quiz: Quiz to evaluate (for quiz-level metrics).
            source_text: Source material text.
            llm_client: LLM provider for generating responses.
            instructions: Optional quiz instructions — drives intent-aware scoring.
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

        self.validate_params(**params)

        accumulated: Dict[str, PhaseOutput] = {}

        # Step 1: Interpret custom_prompt once before any phase runs
        if instructions and instructions.custom_prompt:
            context = self.interpret_custom_prompt(instructions.custom_prompt, llm_client)
            accumulated["custom_prompt_context"] = PhaseOutput(
                phase_name="custom_prompt_context",
                data=context,
            )

        # Step 2: Run all declared phases in order
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
                        params=params,
                        accumulated=accumulated,
                        instructions=instructions,
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
                    params=params,
                    accumulated=accumulated,
                    instructions=instructions,
                )
                result_data = phase.process(inp, llm_client)
                accumulated[phase.name] = PhaseOutput(phase_name=phase.name, data=result_data)

        # Step 3: Parse raw score from final phase
        final_phase_output = accumulated[self.phases[-1].name]
        raw_score = self.parse_score(final_phase_output)

        # Step 4: Apply custom_prompt adjustment in Python
        final_score = raw_score
        if instructions and instructions.custom_prompt:
            context_data = accumulated.get("custom_prompt_context")
            interpreted = (
                context_data.data.get("interpreted_instruction", "") if context_data else ""
            )
            if interpreted:
                final_score = self.adjust_score_for_custom_prompt(
                    raw_score=raw_score,
                    interpreted_instruction=interpreted,
                    quiz=quiz,
                    source_text=source_text,
                    llm_client=llm_client,
                )

                if final_score != raw_score:
                    final_phase_output.data["final_score"] = final_score
                    final_phase_output.data["penalty_applied"] = round(final_score - raw_score, 1)

        return EvaluationResult(
            score=final_score,
            raw_response=json.dumps(final_phase_output.data, ensure_ascii=True),
            metadata={
                "phases": {name: output.data for name, output in accumulated.items()},
                "instructions": instructions.model_dump() if instructions else None,
                "raw_score_before_adjustment": raw_score if final_score != raw_score else None,
            },
        )

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract the final score from the last phase's output."""
        score = float(final_output.data["score"])
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")
        return score

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        """Extract qualitative insights from a metric's raw response for display."""
        return None

    def validate_params(self, **params: Any) -> None:
        """Validate provided parameters against metric's parameter definitions."""
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
        """Get parameter value with fallback to default."""
        param_def = next((p for p in self.parameters if p.name == param_name), None)

        if param_def is None:
            raise ValueError(f"Parameter '{param_name}' not defined for metric '{self.name}'")

        return params.get(param_name, param_def.default)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"
