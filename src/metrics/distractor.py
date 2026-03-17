import json
from typing import Callable, List, Optional
from pydantic import BaseModel

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput, PhaseOutput
from ..models.quiz import QuestionType


class DistractorQualityMetric(BaseMetric):
    """Evaluates the pedagogical effectiveness and plausibility of incorrect options (distractors)."""

    class DistractorQualityResponse(BaseModel):
        """Structured reasoning and scoring for distractor quality."""

        plausibility: str
        misconceptions: str
        discriminatory_power: str
        deduction_explanation: str
        score: float

    @property
    def name(self) -> str:
        return "distractor_quality"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [Phase("score", self.DistractorQualityResponse)]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"score": self._build_score_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_score_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("distractor_quality score phase requires a question")

        question = inp.question

        # Discard True/False questions
        if question.question_type not in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
            raise ValueError(
                f"Distractor quality cannot be evaluated for {question.question_type.value} questions. "
                "Only single_choice and multiple_choice are supported."
            )

        options_text = "\n".join(
            f"{i}. {option}" for i, option in enumerate(question.options or [], 1)
        )

        source_context = f"Source Material: {inp.source_text}"

        return f"""Evaluate the pedagogical quality of the incorrect options (distractors) in the following quiz question.
Assume all options have already been fact-checked. Your sole job is to evaluate how effective the incorrect options are at distracting an unprepared student.

{source_context}

**Question Details**:
Text: {question.question_text}
Options: 
{options_text if options_text else "(No options provided)"}
Correct Answer: {question.correct_answer if hasattr(question, 'correct_answer') else "(Not specified)"}

**Evaluation Criteria**:
1. Plausibility & Source Alignment: Distractors should seem highly plausible to a student who has not mastered the material. They should utilize familiar terms, concepts, or related ideas from the **Source Material** (if provided), making them attractive to someone who only skimmed the text.
2. Common Misconceptions: The best distractors are rooted in predictable student errors, faulty reasoning, or typical conceptual misunderstandings. If a student selects it, a teacher should understand *why* they made that mistake.
3. Discriminatory Power: Good distractors require true comprehension to eliminate. They shouldn't be obvious throwaways or joke answers that anyone could guess are wrong.

**Scoring Guide**:
- 0-20: Poor (distractors are absurd, obvious throwaways, or entirely unrelated to the topic)
- 21-40: Weak (easily eliminated by basic common sense; highly unlikely to fool a guessing student)
- 41-60: Fair (plausible, but generic rather than cleverly pulling from the source material or specific misconceptions)
- 61-80: Good (highly plausible, requires real knowledge to eliminate, uses some lecture context)
- 81-100: Excellent (highly plausible, cleverly uses familiar terms from the source material to test true comprehension, targets specific student errors)

Respond with ONLY a JSON object matching this schema:
{{
  "plausibility": "<reasoning>",
  "misconceptions": "<reasoning>",
  "discriminatory_power": "<reasoning>",
  "deduction_explanation": "<If score < 100, explain exactly what flaws caused the point loss. If score is 100, output 'No deductions.'>",
  "score": <float 0-100>
}}"""

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract the final score from the structured output."""
        try:
            score = float(final_output.data["score"])
        except KeyError:
            raise ValueError(
                f"Distractor Quality parsing failed. Got keys: {list(final_output.data.keys())}"
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
                f"\n[Question ID: {quiz_id}] Distractor Quality Analysis:",
                "-" * 60,
                f"Score:                  {score}/100",
                f"Deductions:             {data.get('deduction_explanation')}",
                f"Plausibility:           {data.get('plausibility')}",
                f"Common Misconceptions:  {data.get('misconceptions')}",
                f"Discriminatory Power:   {data.get('discriminatory_power')}",
                "-" * 60,
            ]
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse distractor quality insights: {str(e)}"
