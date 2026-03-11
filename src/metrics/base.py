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
    """Structured output from the instruction compliance adjustment call."""

    relevant: bool = Field(
        description="Whether any of the instructions are relevant to this metric."
    )
    reasoning: str = Field(
        description="Explanation of the compliance assessment and what adjustment was applied."
    )
    adjustment: float = Field(
        description=(
            "Score adjustment to apply. Positive increases the score, negative decreases it. "
            "0 if no instructions are relevant or the quiz fully complies."
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

    @staticmethod
    def interpret_custom_prompt(
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

    def _has_adjustable_instructions(self, instructions: "QuizInstructions") -> bool:
        """Return True if any instruction field is relevant to this metric.

        Structured fields are coupled to specific metrics:
          language       → grammatical_correctness
          difficulty     → difficulty
          question_types → clarity
          custom_prompt  → coverage only (topic/content focus is not relevant
                           to grammar, difficulty, or clarity metrics)
        """
        if instructions.custom_prompt and self.name == "coverage":
            return True
        if instructions.language and self.name == "grammatical_correctness":
            return True
        if instructions.question_types and self.name == "clarity":
            return True
        return False

    def adjust_difficulty_for_instructions(
        self,
        raw_score: float,
        requested_difficulty: str,
    ) -> float:
        """Adjust a difficulty score based on how far it falls outside the requested band.

        Rather than penalising a low score further (which distorts the meaning of the
        metric), this computes the distance from the target band and applies a penalty
        proportional to that distance. A score already inside the band is unchanged.

        Bands:
          easy:   0–40
          medium: 35–65
          hard:   60–100
        """
        bands = {
            "easy": (0.0, 40.0),
            "medium": (35.0, 65.0),
            "hard": (60.0, 100.0),
        }
        low, high = bands.get(requested_difficulty, (0.0, 100.0))

        if low <= raw_score <= high:
            # Already in band — no adjustment needed
            print(
                f"\n[Difficulty Band Check — {self.name}]\n"
                f"  Requested: {requested_difficulty} ({low}–{high})\n"
                f"  Raw score: {raw_score} — within band, no adjustment."
            )
            return raw_score

        # Distance outside the band as a fraction of the full 0-100 scale
        distance = max(raw_score - high, low - raw_score)
        penalty = round(min(distance * 0.5, 20.0), 1)  # cap penalty at 20pts
        adjusted = round(max(0.0, min(100.0, raw_score - penalty)), 1)

        print(
            f"\n[Difficulty Band Check — {self.name}]\n"
            f"  Requested: {requested_difficulty} ({low}–{high})\n"
            f"  Raw score: {raw_score} — outside band by {distance:.1f} pts\n"
            f"  Penalty:   -{penalty} → {adjusted}"
        )
        return adjusted

    def adjust_score_for_custom_prompt(
        self,
        raw_score: float,
        interpreted_instruction: str,
        quiz: Optional[Quiz],
        source_text: Optional[str],
        llm_client: Any,
        instructions: Optional["QuizInstructions"] = None,
    ) -> float:
        """Apply an instruction compliance adjustment to the raw metric score.

        Called once after all phases complete when any structured instruction
        field is present. All instruction fields are presented together so the
        LLM can reason holistically about compliance.

        Crucially, grammar is scored on the actual language of the quiz — not
        the requested language. A perfectly written German quiz receives a high
        grammar score even if English was requested. The language mismatch is
        captured here as a compliance adjustment, keeping the two concerns separate.

        The adjustment is applied in Python and clamped to [0, 100].

        Args:
            raw_score: Score produced by the metric's phases.
            interpreted_instruction: Interpreted custom_prompt (empty string if none).
            quiz: The quiz being evaluated.
            source_text: The source material text.
            llm_client: LLM provider for the adjustment call.
            instructions: Full QuizInstructions object for structured fields.

        Returns:
            Adjusted score clamped to [0, 100].
        """
        quiz_summary = ""
        if quiz:
            question_lines = "\n".join(
                f"- [{q.question_type.value}] {q.question_text[:120]}" for q in quiz.questions
            )
            quiz_summary = f"**Quiz title**: {quiz.title}\n**Questions**:\n{question_lines}"

        # Each instruction field is only passed to the metric it is semantically
        # coupled with. This prevents e.g. a language mismatch from penalising
        # coverage, or a difficulty mismatch from penalising grammar.
        #
        # Mapping:
        #   language       → grammatical_correctness only
        #   difficulty     → difficulty only
        #   question_types → clarity only
        #   custom_prompt  → all metrics (open-ended, metric decides relevance)
        field_metric_map = {
            "language": "grammatical_correctness",
            "difficulty": "difficulty",
            "question_types": "clarity",
        }

        # custom_prompt is only meaningful for metrics that evaluate content/topic
        # relevance. Difficulty, clarity, and grammatical_correctness have their
        # own structured fields — injecting a topic-focused custom_prompt into them
        # causes the LLM to conflate topic compliance with metric-specific compliance.
        custom_prompt_metrics = {"coverage"}

        instruction_lines = []
        if interpreted_instruction and self.name in custom_prompt_metrics:
            instruction_lines.append(f"- Custom intent: {interpreted_instruction}")
        if instructions:
            if instructions.language and field_metric_map["language"] == self.name:
                instruction_lines.append(
                    f"- Language: the quiz must be written in {instructions.language}. "
                    f"First determine whether the quiz is actually written in {instructions.language}. "
                    f"If it is NOT, a deduction is mandatory — your job is only to decide the magnitude. "
                    f"Do not set adjustment=0 if the language does not match."
                )
            if instructions.difficulty and field_metric_map["difficulty"] == self.name:
                instruction_lines.append(
                    f"- Difficulty: questions should be {instructions.difficulty}"
                )
            if instructions.question_types and field_metric_map["question_types"] == self.name:
                instruction_lines.append(
                    f"- Question types: only {instructions.question_types} are permitted"
                )

        instructions_block = "\n".join(instruction_lines) if instruction_lines else "None"

        prompt = f"""You are reviewing whether a quiz respects a set of instructions,
in the context of the metric: '{self.name}'.

**Instructions**:
{instructions_block}

**Source material (excerpt)**:
{(source_text or '')[:500]}

{quiz_summary}

**Raw score from '{self.name}' metric**: {raw_score}/100

Your task:
1. Decide whether any of these instructions are relevant to the '{self.name}' metric.
   - If NONE are relevant, set relevant=false and adjustment=0.
2. If relevant, assess compliance for each applicable instruction using this scale:
   - A quiz that does exactly what was asked and does it well deserves a score in the excellent range.
   - Full compliance but mediocre raw score → small or no adjustment. Compliance does not compensate for poor quality.
   - Partial compliance → moderate negative adjustment proportional to the degree of violation.
   - No compliance at all → large negative adjustment.
3. For language: only adjust if the quiz is actually written in a different language
   than requested. Do not penalise grammar quality — only the language mismatch itself.
4. Reason carefully about magnitude. Think about what final score the quiz deserves
   given both its quality AND its compliance with the instructions.

Respond with ONLY this JSON object:
{{
  "relevant": true/false,
  "reasoning": "explanation of which instructions apply, compliance assessment, and adjustment rationale",
  "adjustment": <float>
}}"""

        result = llm_client.generate_structured(
            prompt=prompt,
            schema=CustomPromptAdjustment,
        )

        adjustment = float(result.get("adjustment", 0.0))
        reasoning = result.get("reasoning", "")
        relevant = result.get("relevant", False)
        adjusted = raw_score + adjustment
        final = round(max(0.0, min(100.0, adjusted)), 1)

        print(
            f"\n[Instruction Adjustment — {self.name}]\n"
            f"  Relevant:   {relevant}\n"
            f"  Adjustment: {adjustment:+.2f} ({raw_score:.1f} → {final:.1f})\n"
            f"  Reasoning:  {reasoning}"
        )

        return final

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

        # ── Step 1: Interpret custom_prompt once before any phase runs ── #
        if instructions and instructions.custom_prompt:
            context = self.interpret_custom_prompt(instructions.custom_prompt, llm_client)
            accumulated["custom_prompt_context"] = PhaseOutput(
                phase_name="custom_prompt_context",
                data=context,
            )

        # ── Step 2: Run all declared phases in order ──────────────────── #
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

        # ── Step 3: Parse raw score from final phase ──────────────────── #
        final_phase_output = accumulated[self.phases[-1].name]
        raw_score = self.parse_score(final_phase_output)

        # ── Step 4: Apply instruction compliance adjustment in Python ─── #
        # Fires when any structured instruction field is present, not just custom_prompt.
        # All fields are passed together in one LLM call so the model can reason
        # holistically about compliance across all instructions.
        final_score = raw_score
        if instructions and self._has_adjustable_instructions(instructions):
            context_data = accumulated.get("custom_prompt_context")
            interpreted_custom = (
                context_data.data.get("interpreted_instruction", "") if context_data else ""
            )
            final_score = self.adjust_score_for_custom_prompt(
                raw_score=raw_score,
                interpreted_instruction=interpreted_custom,
                quiz=quiz,
                source_text=source_text,
                llm_client=llm_client,
                instructions=instructions,
            )

        # Patch final_score back into the phase data so format_insights
        # (which reads from raw_response) displays the adjusted score, not the raw one.
        if final_score != raw_score and "final_score" in final_phase_output.data:
            final_phase_output.data["final_score"] = final_score

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
