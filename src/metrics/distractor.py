import json
from typing import Callable, List, Optional

from pydantic import BaseModel

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput, PhaseOutput
from ..models.quiz import QuizQuestion, QuestionType


def _extract_distractors(question: QuizQuestion) -> tuple[set[str], list[str]]:
    """Extract correct answers and distractors from a question."""
    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        correct_answers = (
            set(question.correct_answer)
            if isinstance(question.correct_answer, list)
            else {question.correct_answer}
        )
    else:
        correct_answers = {str(question.correct_answer)}

    distractors = [opt for opt in (question.options or []) if opt not in correct_answers]
    return correct_answers, distractors


class DistractorQualityMetric(BaseMetric):
    """Evaluates the pedagogical effectiveness and plausibility of incorrect options (distractors).

    Two-phase pipeline:
      Phase 1 (analyze): Dimensional analysis across plausibility, misconception targeting,
                         discriminatory power, collective quality, and audience calibration.
      Phase 2 (score):   Calibrated scoring derived strictly from phase 1 output, with
                         explicit deduction triggers to reduce score variance across runs.
    """

    class AnalysisResponse(BaseModel):
        """Phase 1: dimensional analysis without a score."""

        plausibility_analysis: str
        misconception_analysis: str
        discrimination_analysis: str
        collective_analysis: str
        difficulty_calibration: str

    class ScoringResponse(BaseModel):
        """Phase 2: score derived strictly from the phase 1 analysis."""

        plausibility_analysis: str
        misconception_analysis: str
        discrimination_analysis: str
        collective_analysis: str
        difficulty_calibration: str
        deduction_explanation: str
        score: float

    @property
    def name(self) -> str:
        return "distractor_quality"

    @property
    def version(self) -> str:
        return "1.2"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("analyze", self.AnalysisResponse),
            Phase("score", self.ScoringResponse),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {
            "analyze": self._build_analyze_prompt,
            "score": self._build_score_prompt,
        }
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_analyze_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("distractor_quality analyze phase requires a question")

        if inp.source_text is None:
            raise ValueError(
                "distractor_quality analyze phase requires source_text (source material is essential for evaluating distractor quality)"
            )

        question = inp.question

        if question.question_type not in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
            raise ValueError(
                f"Distractor quality cannot be evaluated for {question.question_type.value} questions. "
                "Only single_choice and multiple_choice are supported."
            )

        correct_answers, distractors = _extract_distractors(question)
        correct_display = ", ".join(sorted(correct_answers))
        distractors_text = "\n".join(f"{i}. {d}" for i, d in enumerate(distractors, 1))

        return f"""You are a pedagogical assessment expert. Analyze the distractors in this quiz question WITHOUT assigning a score yet.

Source Material:
{inp.source_text}

Question: {question.question_text}
Correct Answer(s): {correct_display}
Distractors:
{distractors_text or "(none provided)"}

Analyze the distractors across these five dimensions:

1. PLAUSIBILITY & SOURCE ALIGNMENT
   - Does each distractor use specific vocabulary, values, or concepts from the source material?
   - Would a student who skimmed the material find it attractive?
   - Are any distractors generic (not grounded in the source) or transparently wrong?

2. MISCONCEPTION TARGETING
   - What specific cognitive error or knowledge gap does each distractor exploit?
   - Are these real, predictable student mistakes — or arbitrary wrong answers?
   - Could a teacher use a student's wrong selection to diagnose exactly what they misunderstood?

3. DISCRIMINATORY POWER
   - Can any distractor be eliminated by common sense alone (no domain knowledge required)?
   - Does eliminating it require genuine mastery, or just surface familiarity?
   - Is it a trap for students who partially understand the concept?

4. COLLECTIVE QUALITY
   - Do the distractors cover distinct misconceptions, or do multiple distractors exploit the same error?
   - Does the distractor set as a whole discriminate better or worse than individual distractors alone?
   - Does any distractor inadvertently hint at or narrow down the correct answer?

5. AUDIENCE CALIBRATION
   - Are distractors appropriately difficult for the expected student level implied by the source material?
   - Would an expert find them trivially eliminable? Would a total novice find them indistinguishable from the correct answer?

Respond with ONLY a JSON object matching this schema:
{{
  "plausibility_analysis": "<per-distractor analysis>",
  "misconception_analysis": "<per-distractor analysis>",
  "discrimination_analysis": "<per-distractor analysis>",
  "collective_analysis": "<analysis of the distractor set as a whole>",
  "difficulty_calibration": "<audience-level fit analysis>"
}}"""

    @staticmethod
    def _build_score_prompt(inp: PhaseInput) -> str:
        analyze_output = inp.accumulated.get("analyze")
        if analyze_output is None:
            raise ValueError(
                "distractor_quality score phase requires 'analyze' phase output in accumulated"
            )

        analysis = analyze_output.data

        return f"""You are a strict pedagogical assessment examiner. Based solely on the analysis below, assign a final distractor quality score.

        ANALYSIS TO SCORE:
        Plausibility & source alignment: {analysis.get("plausibility_analysis")}
        Misconception targeting:         {analysis.get("misconception_analysis")}
        Discriminatory power:            {analysis.get("discrimination_analysis")}
        Collective quality:              {analysis.get("collective_analysis")}
        Audience calibration:            {analysis.get("difficulty_calibration")}

        SCORING RUBRIC:
        0–20   Poor      — distractors are absurd, unrelated, or obviously wrong to any reader
        21–40  Weak      — easily eliminated by common sense; no domain knowledge needed
        41–60  Fair      — plausible but generic; not grounded in source material or real misconceptions
        61–80  Good      — grounded in source material, requires real knowledge to eliminate
        81–100 Excellent — highly plausible, exploits specific student errors, covers distinct misconceptions,
                           calibrated to audience, set is collectively strong with no cannibalization

        DEDUCTION TRIGGERS (apply additively from a starting score of 100):
        - Any distractor eliminable by common sense alone:                  −10 to −20
        - Any distractor not tied to the source material (generic):         −5  to −15
        - Two or more distractors exploit the same misconception:           −5  to −10
        - Any distractor inadvertently hints at the correct answer:         −10 to −15
        - Distractor set poorly calibrated for the expected audience:       −5  to −10
        - A predictable, obvious student error is missing as a distractor:  −5

        A score of 90+ should be genuinely rare. Be calibrated and strict.

        Keep your analysis extremely punchy and concise. Limit the text for EACH JSON field, focus only on the most critical insights.

        Respond with ONLY a JSON object matching this schema:
        {{
            "plausibility_analysis": "<reasoning>",
            "misconception_analysis": "<reasoning>",
            "discrimination_analysis": "<reasoning>",
            "collective_analysis": "<reasoning>",
            "difficulty_calibration": "<reasoning>",
            "deduction_explanation": "<list each deduction applied and its point value, or 'No deductions.'>",
            "score": <float 0-100>
        }}
    """

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract the final score from the phase 2 (score) output."""
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
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            score = data.get("score")
            if score is None:
                return None

            lines = [
                f"\n🎯 [Q: {quiz_id}] Distractor Quality: {score}/100",
                f"   Deductions: {data.get('deduction_explanation')}",
                f"   • Plausibility:   {data.get('plausibility_analysis')}",
                f"   • Misconceptions: {data.get('misconception_analysis')}",
                f"   • Discrimination: {data.get('discrimination_analysis')}",
                f"   • Collective:     {data.get('collective_analysis')}",
                f"   • Calibration:    {data.get('difficulty_calibration')}",
                "-" * 65,
            ]
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse distractor quality insights: {str(e)}"
