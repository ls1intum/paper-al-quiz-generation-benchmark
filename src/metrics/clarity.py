"""Clarity metric implementation."""

from typing import List
from .base import BaseMetric, MetricScope, ScoreResponse
from .phase import Phase, PhaseInput


class ClarityMetric(BaseMetric):
    """Evaluates the clarity of quiz questions and answer options.

    Uses a single-stage pipeline:
    1. ClarityScorePhase: scores how clear, unambiguous, and well-written
       the question and its options are.
    """

    class ClarityScorePhase(Phase):
        """Stage 1: Score the clarity of a single question.

        Requires:
            phase_input.question: The question being evaluated.

        Produces:
            ScoreResponse: {"score": <0-100>}
        """

        def build_prompt(self, phase_input: PhaseInput) -> str:
            if phase_input.question is None:
                raise ValueError("ClarityScorePhase requires a question")

            question = phase_input.question

            prompt = f"""Evaluate the clarity of the following quiz question.

Question Type: {question.question_type.value}
Question: {question.question_text}

Options:
"""
            for i, option in enumerate(question.options, 1):
                prompt += f"{i}. {option}\n"

            prompt += """
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
{{"score": <number between 0 and 100>}}
"""
            return prompt

    @property
    def name(self) -> str:
        return "clarity"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        """Single-stage clarity evaluation pipeline.

        Returns:
            [ClarityScorePhase]
        """
        return [
            self.ClarityScorePhase(
                name="clarity_scoring",
                output_schema=ScoreResponse,
            ),
        ]
