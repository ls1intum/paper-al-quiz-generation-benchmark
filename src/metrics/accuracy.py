import json
from collections.abc import Callable

from pydantic import BaseModel

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput, PhaseOutput


class FactualAccuracyMetric(BaseMetric):
    """Evaluates the factual accuracy of what a quiz item asserts to be true.

    Scope is the stem and its premises, plus any option the key marks correct. A
    distractor is SUPPOSED to be false, so its falseness is not an error here; judged
    otherwise, a well-built item is penalised for having working distractors. Whether the
    key itself is right belongs to `answer_key_correctness`, so that a keying defect is
    reported by exactly one metric.

    v1.2 narrowed this scope; v1.1 asked whether "all statements" were correct, which reads
    as requiring every option to be true. The version is recorded on each result row, so
    output from the two remains distinguishable.

    Verifies that:
    1. The stem states nothing false and takes no false premise for granted
    2. Claims are based on evidence rather than opinion, theory, or interpretation
    3. Content is factually correct and aligns with established knowledge
    """

    class FactualAccuracyResponse(BaseModel):
        """Structured reasoning and scoring for factual accuracy."""

        factual_correctness: str
        evidence_based: str
        bias_and_distortion: str
        source_alignment: str
        objectivity: str
        major_errors_found: list[str]
        score: float

    @property
    def name(self) -> str:
        return "accuracy"

    @property
    def version(self) -> str:
        return "1.2"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> list[Phase]:
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
            f"Source Material:\n{inp.source_text}"
            if inp.source_text
            else "No source material is available. Evaluate factual accuracy using expert knowledge."
        )

        return f"""Evaluate the factual accuracy of the following quiz question and its answers.

{source_context}

**Question Details**:
Text: {question.question_text}
Options: 
{options_text}
Correct Answer: {question.correct_answer if hasattr(question, 'correct_answer') else "(Not specified)"}

**What is in scope**:
Judge only what the item ASSERTS AS TRUE: the claims in the stem, including any premise it takes for granted, and the content of the options marked correct.

A distractor being false is NOT an error. Distractors are supposed to be false -- that is their function -- so do not report an unkeyed option as a major error merely because it states something untrue. If you believe the marked correct answer is wrong, or that an unkeyed option is also defensible, that is a defect of the answer key and is judged elsewhere; do not report it here.

**Evaluation Criteria**:
1. Factual Correctness: Does the stem state anything false, or assume a false premise? Are there outdated facts or clear errors in what the item asserts?
2. Evidence-Based Content: Is what the item asserts verifiable fact rather than opinion or theory?
3. Bias and Distortion: Is the item free from political, cultural, or personal bias?
4. Source Alignment: Does it align with the provided source material (if any)? Does it contradict it?
5. Objectivity: Would reasonable experts agree with the factual claims the item makes?

**Scoring Guide**:
- 0-20: Highly Inaccurate (major errors, built on false premises)
- 21-40: Inaccurate (notable errors, partially opinion)
- 41-60: Moderately Accurate (mostly factual but minor inaccuracies)
- 61-80: Accurate (factually correct and evidence-based)
- 81-100: Highly Accurate (objective, perfectly grounded in evidence)

An item whose only "errors" are false distractors is Highly Accurate, not inaccurate.

Provide your evaluation and score based strictly on these criteria.

Respond with ONLY a JSON object matching this schema:
{{
  "factual_correctness": "<reasoning>",
  "evidence_based": "<reasoning>",
  "bias_and_distortion": "<reasoning>",
  "source_alignment": "<reasoning>",
  "objectivity": "<reasoning>",
  "major_errors_found": ["a definite factual error in what the item asserts", ...],
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

    def format_insights(self, raw_response: str, quiz_id: str) -> str | None:
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
            return f"Could not parse factual accuracy insights: {e!s}"
