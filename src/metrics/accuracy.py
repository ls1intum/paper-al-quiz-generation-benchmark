import json
from typing import Callable, List, Optional
from pydantic import BaseModel, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput, PhaseOutput


class FactualAccuracyMetric(BaseMetric):
    """Evaluates the factual accuracy of quiz questions and answers.

    Verifies that:
    1. Questions and answers are free from errors, biases, or distortions
    2. Answers are based on evidence rather than opinions, theories, or interpretations
    3. Content is factually correct and aligns with established knowledge
    """

    class FactualAccuracyResponse(BaseModel):
        """Structured reasoning and scoring for factual accuracy."""

        factual_correctness: str = Field(
            description="Reasoning about factual correctness and errors."
        )
        evidence_based: str = Field(
            description="Reasoning about whether it is evidence-based vs opinion."
        )
        bias_and_distortion: str = Field(
            description="Reasoning about bias, loaded language, or distortion."
        )
        source_alignment: str = Field(
            description="Reasoning about alignment with provided source material."
        )
        objectivity: str = Field(
            description="Reasoning about objectivity vs subjective interpretation."
        )
        major_errors_found: List[str] = Field(
            default_factory=list, description="List of any specific factual errors found."
        )
        score: float = Field(ge=0, le=100, description="Overall factual accuracy score (0-100).")

    @property
    def name(self) -> str:
        return "accuracy"

    @property
    def version(self) -> str:
        return "1.1"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        # Using the new structured response instead of the default ScoreResponse
        return [Phase("score", self.FactualAccuracyResponse)]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"score": self._build_score_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_score_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("factual_accuracy score phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        source_context = (
            f"Source Material: {inp.source_text}"
            if inp.source_text
            else "(No source material provided)"
        )

        return f"""Evaluate the factual accuracy of the following quiz question and its answers.

{source_context}

**Question Details**:
Text: {question.question_text}
Options: 
{options_text}
Correct Answer: {question.correct_answer if hasattr(question, 'correct_answer') else "(Not specified)"}

**Evaluation Criteria**:
1. Factual Correctness: Are all statements correct? Are there outdated facts or clear errors?
2. Evidence-Based Content: Is the answer verifiable fact rather than opinion or theory?
3. Bias and Distortion: Is it free from political, cultural, or personal bias? Are all options presented fairly?
4. Source Alignment: Does it align with the provided source material (if any)? Does it contradict it?
5. Objectivity: Would reasonable experts agree with the factual claims?

**Scoring Guide**:
- 0-20: Highly Inaccurate (major errors, built on false premises)
- 21-40: Inaccurate (notable errors, partially opinion)
- 41-60: Moderately Accurate (mostly factual but minor inaccuracies)
- 61-80: Accurate (factually correct and evidence-based)
- 81-100: Highly Accurate (objective, perfectly grounded in evidence)

Provide your evaluation and score based strictly on these criteria.

Respond with ONLY a JSON object matching this schema:
{{
  "factual_correctness": "<reasoning>",
  "evidence_based": "<reasoning>",
  "bias_and_distortion": "<reasoning>",
  "source_alignment": "<reasoning>",
  "objectivity": "<reasoning>",
  "major_errors_found": ["error 1", "error 2"],
  "score": <float 0-100>
}}"""

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract the final score from the structured output."""
        try:
            score = float(final_output.data["score"])
        except KeyError:
            raise ValueError(
                f"Factual Accuracy parsing failed. Got keys: {list(final_output.data.keys())}"
            )

        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")
        return round(score, 1)

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            score = data.get("score")
            if score is None:
                return None

            lines = [
                f"\n[Question ID: {quiz_id}] Factual Accuracy Analysis:",
                "-" * 50,
                f"Score:               {score}/100",
                f"Factual Correctness: {data.get('factual_correctness')}",
                f"Evidence Based:      {data.get('evidence_based')}",
                f"Bias & Distortion:   {data.get('bias_and_distortion')}",
                f"Source Alignment:    {data.get('source_alignment')}",
                f"Objectivity:         {data.get('objectivity')}",
            ]

            errors = data.get("major_errors_found", [])
            if errors:
                lines.append("Major Errors Found:")
                for err in errors:
                    lines.append(f"  - {err}")
            else:
                lines.append("Major Errors Found:  None")

            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse factual accuracy insights: {str(e)}"
