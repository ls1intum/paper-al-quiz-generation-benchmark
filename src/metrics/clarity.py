"""Clarity metric implementation."""

import json
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput

CLARITY_SCORES = {
    "excellent": 100.0,
    "good": 66.7,
    "fair": 33.3,
    "poor": 0.0,
}


class ClarityJudgeResponse(BaseModel):
    """The judge's verdict on clarity. Carries no score."""

    model_config = ConfigDict(extra="forbid")

    clarity_level: Literal["excellent", "good", "fair", "poor"]
    question_clarity_issues: List[str] = Field(default_factory=list)
    option_clarity_issues: List[str] = Field(default_factory=list)
    contains_negation: bool
    rationale: str


class ClarityResponse(ClarityJudgeResponse):
    """Final output: the judge's level plus the score derived from it."""

    score: float = Field(ge=0, le=100)


class ClarityMetric(BaseMetric):
    """Evaluates the clarity of quiz questions and answer options.

    Two-phase pipeline:
      Phase 1 (judge): LLM picks a categorical verdict and flags negation.
      Phase 2 (finalize): Deterministic mapping from verdict to score.

    Instructions integration:
    - question_types: if instructions.question_types is set and the current
      question's type is not in the list, a note is injected into the prompt
      so the LLM can factor in the type mismatch when scoring clarity.
    - custom_prompt: handled entirely in BaseMetric.evaluate().
    """

    @property
    def name(self) -> str:
        return "clarity"

    @property
    def version(self) -> str:
        return "2.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("judge", ClarityJudgeResponse),
            Phase("finalize", ClarityResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("clarity judge phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        # Inject question type compliance note if instructions specify types
        type_note = ""
        if inp.instructions and inp.instructions.question_types:
            requested_types = inp.instructions.question_types
            actual_type = question.question_type.value
            if actual_type not in requested_types:
                type_note = (
                    f"\n**Instructions note**: The requested question types were "
                    f"{requested_types}, but this question is of type '{actual_type}'. "
                    f"A question of an unexpected type may cause confusion for students "
                    f"who prepared for a specific format — factor this into your clarity verdict."
                )
            else:
                type_note = (
                    f"\n**Instructions note**: This question type ('{actual_type}') "
                    f"matches the requested types {requested_types}."
                )

        return f"""Evaluate the clarity of the following quiz question.
{type_note}
Question Type: {question.question_type.value}
Question: {question.question_text}

Options:
{options_text}

**Verdict definitions**:
- "excellent": Precise, unambiguous, professionally written. Students clearly understand
  what is being asked. Options are clearly distinct with no overlap.
- "good": Well-written with minimal ambiguity. Minor clarity issues that would not
  confuse most students.
- "fair": Understandable but could improve. Some vague wording, partial overlap between
  options, or confusing structure.
- "poor": Ambiguous, confusing, or poorly written. Students would struggle to understand
  what is being asked.

**Evaluate these aspects**:

1. Question Clarity:
   - Is the question easy to understand?
   - Is the wording precise and unambiguous?
   - Is it free from grammatical errors?

2. Answer Options:
   - Are options clearly distinct?
   - Is there no overlap or ambiguity between options?
   - Are options of similar length and complexity?
   - Are there no "trick" wordings?

3. Negative Phrasing:
   - Does the question or any option use negation (e.g., "not", "except", "which of the
     following is NOT")? Negative phrasing increases cognitive load and can confuse
     students. Flag it even if the question is otherwise clear.

4. Overall Quality:
   - Is the question professionally written?
   - Would a student clearly understand what is being asked?
   - Is there a single, clearly correct answer?

Respond with ONLY a JSON object matching this schema:
{{
  "clarity_level": "excellent" | "good" | "fair" | "poor",
  "question_clarity_issues": ["specific issue", ...],
  "option_clarity_issues": ["specific issue", ...],
  "contains_negation": true/false,
  "rationale": "<reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> Dict[str, Any]:
        """Derive the score from the judge's clarity level."""
        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        level = judged["clarity_level"]

        return {
            "clarity_level": level,
            "question_clarity_issues": judged.get("question_clarity_issues", []),
            "option_clarity_issues": judged.get("option_clarity_issues", []),
            "contains_negation": judged.get("contains_negation", False),
            "rationale": judged.get("rationale", ""),
            "score": CLARITY_SCORES[level],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            level = data.get("clarity_level")
            if level is None:
                return None

            lines = [
                f"\n[Question ID: {quiz_id}] Clarity:",
                "-" * 50,
                f"Level:     {level}",
                f"Score:     {data.get('score')}/100",
                f"Negation:  {'yes' if data.get('contains_negation') else 'no'}",
            ]

            for label, key in (
                ("Question issues", "question_clarity_issues"),
                ("Option issues", "option_clarity_issues"),
            ):
                issues = data.get(key, [])
                if issues:
                    lines.append(f"{label}:")
                    for issue in issues:
                        lines.append(f"  - {issue}")
                else:
                    lines.append(f"{label}: None")

            lines.append(f"Rationale: {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse clarity insights: {str(e)}"
