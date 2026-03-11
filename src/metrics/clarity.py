"""Clarity metric implementation."""

from typing import Callable, List
from .base import BaseMetric, MetricScope, ScoreResponse
from .phase import Phase, PhaseInput


class ClarityMetric(BaseMetric):
    """Evaluates the clarity of quiz questions and answer options.

    Uses a single-stage pipeline:
    1. score: scores how clear, unambiguous, and well-written the question
       and its options are.

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
        return "1.2"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [Phase("score", ScoreResponse)]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"score": self._build_score_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_score_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("clarity score phase requires a question")

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
                    f"who prepared for a specific format — factor this into your clarity score."
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

Provide a clarity score from 0 to 100, where:
- 0-20: Very Unclear (ambiguous, confusing, poorly written)
- 21-40: Unclear (some confusion, vague wording)
- 41-60: Moderately Clear (understandable but could improve)
- 61-80: Clear (well-written, minimal ambiguity)
- 81-100: Very Clear (precise, unambiguous, excellent)

Consider:
1. Question Clarity:
   - Is the question easy to understand?
   - Is the wording precise and unambiguous?
   - Is it free from grammatical errors?

2. Answer Options:
   - Are options clearly distinct?
   - Is there no overlap or ambiguity between options?
   - Are options of similar length and complexity?
   - Are there no "trick" wordings?

3. Overall Quality:
   - Is the question professionally written?
   - Would a student clearly understand what's being asked?
   - Is there a single, clearly correct answer?

Respond with ONLY a JSON object in this format:
{{"score": <number between 0 and 100>}}"""
