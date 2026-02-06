"""Difficulty metric implementation."""

import re
from typing import Any, List, Optional

from ..models.quiz import Quiz, QuizQuestion
from .base import BaseMetric, MetricParameter, MetricScope


class DifficultyMetric(BaseMetric):
    """Evaluates the difficulty level of quiz questions.

    This metric assesses cognitive complexity and expected difficulty
    for the target audience.
    """

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

    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        **params: Any,
    ) -> str:
        """Generate difficulty evaluation prompt.

        Args:
            question: Question to evaluate
            quiz: Not used (question-level metric)
            source_text: Optional source material for context
            **params: rubric and target_audience parameters

        Returns:
            Formatted prompt

        Raises:
            ValueError: If question is None
        """
        if question is None:
            raise ValueError("DifficultyMetric requires a question")

        self.validate_params(**params)
        rubric = self.get_param_value("rubric", **params)
        target_audience = self.get_param_value("target_audience", **params)

        # Build the prompt based on rubric
        if rubric == "bloom_taxonomy":
            rubric_description = """
Bloom's Taxonomy Levels:
1. Remember (0-20): Recall facts, terms, basic concepts
2. Understand (21-40): Explain ideas, construct meaning
3. Apply (41-60): Use information in new situations
4. Analyze (61-75): Draw connections, distinguish between parts
5. Evaluate (76-90): Justify decisions, critique
6. Create (91-100): Produce new work, design solutions
"""
        elif rubric == "webb_dok":
            rubric_description = """
Webb's Depth of Knowledge:
1. Recall (0-25): Recall facts, definitions, simple procedures
2. Skill/Concept (26-50): Use information, make decisions
3. Strategic Thinking (51-75): Reasoning, planning, evidence
4. Extended Thinking (76-100): Complex reasoning, multiple steps
"""
        else:
            rubric_description = "Evaluate difficulty on a scale from 0-100."

        prompt = f"""Evaluate the difficulty of the following quiz question for a {target_audience} audience.

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

Respond with ONLY a number between 0 and 100.
"""

        return prompt

    def parse_response(self, llm_response: str) -> float:
        """Parse difficulty score from LLM response.

        Args:
            llm_response: Raw LLM response

        Returns:
            Score between 0 and 100

        Raises:
            ValueError: If score cannot be extracted
        """
        # Try to extract a number from the response
        # Look for standalone numbers or numbers at the start of the response
        response = llm_response.strip()

        # Try to find a number (integer or float)
        match = re.search(r"\b(\d+(?:\.\d+)?)\b", response)
        if match:
            score = float(match.group(1))
            if 0 <= score <= 100:
                return score

        raise ValueError(f"Could not parse difficulty score from response: {llm_response}")
