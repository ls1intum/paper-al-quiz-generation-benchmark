"""Difficulty metric implementation."""

from typing import Any, List, Optional, Dict

from pydantic import BaseModel, Field

from ..models.quiz import Quiz, QuizQuestion
from .base import BaseMetric, MetricParameter, MetricScope, ScoreResponse
from .phase import Phase, PhaseInput


class DifficultyMetric(BaseMetric):
    """Evaluates the difficulty level of quiz questions.

    Uses a single-stage pipeline:
    1. DifficultyScorePhase: scores cognitive complexity for the target audience.
    """

    class DifficultyScorePhase(Phase):
        """Stage 1: Score the cognitive difficulty of a single question.

        Requires:
            phase_input.question: The question being evaluated.

        Produces:
            ScoreResponse: {"score": <0-100>}
        """

        def __init__(
            self,
            rubric: str = "bloom_taxonomy",
            target_audience: str = "undergraduate",
            **kwargs: Any,
        ) -> None:
            super().__init__(**kwargs)
            self.rubric = rubric
            self.target_audience = target_audience

        def build_prompt(self, phase_input: PhaseInput) -> str:
            if phase_input.question is None:
                raise ValueError("DifficultyScorePhase requires a question")

            question = phase_input.question

            if self.rubric == "bloom_taxonomy":
                rubric_description = """
Bloom's Taxonomy Levels:
1. Remember (0-20): Recall facts, terms, basic concepts
2. Understand (21-40): Explain ideas, construct meaning
3. Apply (41-60): Use information in new situations
4. Analyze (61-75): Draw connections, distinguish between parts
5. Evaluate (76-90): Justify decisions, critique
6. Create (91-100): Produce new work, design solutions
"""
            elif self.rubric == "webb_dok":
                rubric_description = """
Webb's Depth of Knowledge:
1. Recall (0-25): Recall facts, definitions, simple procedures
2. Skill/Concept (26-50): Use information, make decisions
3. Strategic Thinking (51-75): Reasoning, planning, evidence
4. Extended Thinking (76-100): Complex reasoning, multiple steps
"""
            else:
                rubric_description = "Evaluate difficulty on a scale from 0-100."

            prompt = f"""Evaluate the difficulty of the following quiz question for a {self.target_audience} audience.

{rubric_description}

Question Type: {question.question_type.value}
Question: {question.question_text}

Options:
"""
            for i, option in enumerate(question.options, 1):
                prompt += f"{i}. {option}\n"

            prompt += f"""
Correct Answer: {question.correct_answer}

Provide a difficulty score from 0 to 100, where:
- 0-20: Very Easy
- 21-40: Easy
- 41-60: Moderate
- 61-80: Difficult
- 81-100: Very Difficult

Consider:
1. Cognitive level required (based on the rubric above)
2. Complexity of the concept
3. Number of steps needed to solve
4. Potential for confusion

Respond with ONLY a JSON object in this format:
{{"score": <number between 0 and 100>}}
"""
            return prompt

    @property
    def name(self) -> str:
        return "difficulty"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def parameters(self) -> List[MetricParameter]:
        return [
            MetricParameter(
                name="rubric",
                param_type=str,
                default="bloom_taxonomy",
                description="Difficulty rubric to use (bloom_taxonomy, webb_dok, custom)",
            ),
            MetricParameter(
                name="target_audience",
                param_type=str,
                default="undergraduate",
                description="Target audience level (high_school, undergraduate, graduate)",
            ),
        ]

    @property
    def phases(self) -> List[Phase]:
        """Single-stage difficulty evaluation pipeline.

        Returns:
            [DifficultyScorePhase]
        """
        rubric = self.get_param_value("rubric")
        target_audience = self.get_param_value("target_audience")
        return [
            self.DifficultyScorePhase(
                name="difficulty_scoring",
                output_schema=ScoreResponse,
                rubric=rubric,
                target_audience=target_audience,
            ),
        ]
