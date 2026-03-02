"""Clarity metric implementation."""

from typing import Callable, List
from .base import BaseMetric, MetricScope, ScoreResponse
from .phase import Phase, PhaseInput


class ClarityMetric(BaseMetric):
    """Evaluates the clarity of quiz questions and answer options.

    Uses a single-stage pipeline:
    1. score: scores how clear, unambiguous, and well-written the question
       and its options are.
    """

    @property
    def name(self) -> str:
        return "clarity"

    @property
    def version(self) -> str:
        return "1.1"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [Phase("score", ScoreResponse)]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {
            "score": self._build_score_prompt,
        }
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    def _build_score_prompt(self, inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("clarity score phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        return f"""Evaluate the clarity of the following quiz question.

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
