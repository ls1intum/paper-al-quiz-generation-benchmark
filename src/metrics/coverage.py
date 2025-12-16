"""Coverage metric implementation."""

import re
from typing import Any, List, Optional

from ..models.quiz import Quiz, QuizQuestion
from .base import BaseMetric, MetricParameter, MetricScope


class CoverageMetric(BaseMetric):
    """Evaluates how well the quiz covers the source material.

    This metric assesses breadth and depth of content coverage.
    """

    @property
    def name(self) -> str:
        return "coverage"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def parameters(self) -> List[MetricParameter]:
        return [
            MetricParameter(
                name="granularity",
                param_type=str,
                default="balanced",
                description="Coverage granularity (detailed, balanced, broad)",
            ),
        ]

    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        **params: Any,
    ) -> str:
        """Generate coverage evaluation prompt.

        Args:
            question: Not used (quiz-level metric)
            quiz: Quiz to evaluate
            source_text: Source material text
            **params: granularity parameter

        Returns:
            Formatted prompt

        Raises:
            ValueError: If quiz or source_text is None
        """
        if quiz is None:
            raise ValueError("CoverageMetric requires a quiz")
        if source_text is None:
            raise ValueError("CoverageMetric requires source_text")

        self.validate_params(**params)
        granularity = self.get_param_value("granularity", **params)

        # Build question summary
        question_summary = f"Quiz: {quiz.title}\nTotal Questions: {quiz.num_questions}\n\n"
        for i, q in enumerate(quiz.questions, 1):
            question_summary += f"Q{i} ({q.question_type.value}): {q.question_text}\n"

        # Granularity instructions
        if granularity == "detailed":
            coverage_instruction = """
Evaluate coverage at a detailed level:
- Are specific concepts, facts, and details covered?
- Are edge cases and nuances addressed?
- Is depth of coverage appropriate for each topic?
"""
        elif granularity == "broad":
            coverage_instruction = """
Evaluate coverage at a broad level:
- Are major themes and topics included?
- Is there representation across different sections?
- Are key learning objectives addressed?
"""
        else:  # balanced
            coverage_instruction = """
Evaluate coverage with a balanced approach:
- Are main concepts covered adequately?
- Is there reasonable breadth across topics?
- Is depth sufficient for important concepts?
"""

        prompt = f"""Evaluate how well this quiz covers the source material.

SOURCE MATERIAL:
{source_text[:2000]}...  # Truncate if too long

{question_summary}

{coverage_instruction}

Provide a coverage score from 0 to 100, where:
- 0-20: Very Poor Coverage (major gaps, important topics missing)
- 21-40: Poor Coverage (significant gaps in breadth or depth)
- 41-60: Moderate Coverage (covers main points, some gaps)
- 61-80: Good Coverage (comprehensive, minor gaps)
- 81-100: Excellent Coverage (thorough, well-distributed)

Consider:
1. Breadth: Are different topics/sections represented?
2. Depth: Is coverage sufficient for key concepts?
3. Balance: Is coverage distributed appropriately?
4. Completeness: Are critical learning points included?

Respond with ONLY a number between 0 and 100.
"""

        return prompt

    def parse_response(self, llm_response: str) -> float:
        """Parse coverage score from LLM response.

        Args:
            llm_response: Raw LLM response

        Returns:
            Score between 0 and 100

        Raises:
            ValueError: If score cannot be extracted
        """
        response = llm_response.strip()

        # Try to find a number
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', response)
        if match:
            score = float(match.group(1))
            if 0 <= score <= 100:
                return score

        raise ValueError(
            f"Could not parse coverage score from response: {llm_response}"
        )
