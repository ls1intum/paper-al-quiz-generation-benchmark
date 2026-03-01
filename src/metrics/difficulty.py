"""Difficulty metric implementation."""

from typing import Callable, List
from .base import BaseMetric, MetricParameter, MetricScope, ScoreResponse
from .phase import Phase, PhaseInput


class DifficultyMetric(BaseMetric):
    """Evaluates the difficulty level of quiz questions.

    Uses a single-stage pipeline:
    1. score: scores cognitive complexity for the target audience.
    """

    @property
    def name(self) -> str:
        return "difficulty"

    @property
    def version(self) -> str:
        return "1.1"

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
            raise ValueError("difficulty score phase requires a question")

        rubric = self.get_param_value("rubric")
        target_audience = self.get_param_value("target_audience")
        question = inp.question

        if rubric == "bloom_taxonomy":
            rubric_description = """Bloom's Taxonomy Levels:
1. Remember (0-20): Recall facts, terms, basic concepts
2. Understand (21-40): Explain ideas, construct meaning
3. Apply (41-60): Use information in new situations
4. Analyze (61-75): Draw connections, distinguish between parts
5. Evaluate (76-90): Justify decisions, critique
6. Create (91-100): Produce new work, design solutions"""
        elif rubric == "webb_dok":
            rubric_description = """Webb's Depth of Knowledge:
1. Recall (0-25): Recall facts, definitions, simple procedures
2. Skill/Concept (26-50): Use information, make decisions
3. Strategic Thinking (51-75): Reasoning, planning, evidence
4. Extended Thinking (76-100): Complex reasoning, multiple steps"""
        else:
            rubric_description = "Evaluate difficulty on a scale from 0-100."

        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        return f"""Evaluate the difficulty of the following quiz question for a {target_audience} audience.

{rubric_description}

Question Type: {question.question_type.value}
Question: {question.question_text}

Options:
{options_text}

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
{{"score": <number between 0 and 100>}}"""
