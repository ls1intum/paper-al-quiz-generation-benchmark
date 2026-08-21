import json
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput
from ..models.quiz import QuizQuestion, QuestionType

QUALITY_SCORES = {
    "excellent": 100.0,
    "good": 66.7,
    "fair": 33.3,
    "poor": 0.0,
}


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

    Three-phase pipeline:
      Phase 1 (analyze): Dimensional analysis across plausibility, misconception targeting,
                         discriminatory power, collective quality, and audience calibration.
      Phase 2 (judge):   LLM reads the analysis and picks a categorical verdict.
      Phase 3 (finalize): Deterministic mapping from verdict to score.
    """

    class AnalysisResponse(BaseModel):
        """Phase 1: dimensional analysis without a score."""

        plausibility_analysis: str
        misconception_analysis: str
        discrimination_analysis: str
        collective_analysis: str
        difficulty_calibration: str
        source_grounded: bool = True

    class DistractorJudgeResponse(BaseModel):
        """Phase 2: categorical verdict derived from the analysis."""

        model_config = ConfigDict(extra="forbid")

        quality_level: Literal["excellent", "good", "fair", "poor"]
        deduction_summary: str
        rationale: str

    class DistractorFinalResponse(DistractorJudgeResponse):
        """Phase 3: adds the deterministic score."""

        score: float = Field(ge=0, le=100)

    @property
    def name(self) -> str:
        return "distractor_quality"

    @property
    def version(self) -> str:
        return "2.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("analyze", self.AnalysisResponse),
            Phase("judge", self.DistractorJudgeResponse),
            Phase("finalize", self.DistractorFinalResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {
            "analyze": self._build_analyze_prompt,
            "judge": self._build_judge_prompt,
        }
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_analyze_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("distractor_quality analyze phase requires a question")

        question = inp.question

        if question.question_type not in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
            raise ValueError(
                f"Distractor quality cannot be evaluated for {question.question_type.value} questions. "
                "Only single_choice and multiple_choice are supported."
            )

        correct_answers, distractors = _extract_distractors(question)
        correct_display = ", ".join(sorted(correct_answers))
        distractors_text = "\n".join(f"{i}. {d}" for i, d in enumerate(distractors, 1))

        has_source = inp.source_text is not None
        source_section = (
            f"Source Material:\n{inp.source_text}"
            if has_source
            else "No source material is available. Evaluate distractors using expert knowledge."
        )
        plausibility_label = (
            "PLAUSIBILITY & SOURCE ALIGNMENT"
            if has_source
            else "PLAUSIBILITY & KNOWLEDGE ALIGNMENT"
        )
        plausibility_detail = (
            "- Does each distractor use specific vocabulary, values, or concepts from the source material?\n"
            "   - Would a student who skimmed the material find it attractive?\n"
            "   - Are any distractors generic (not grounded in the source) or transparently wrong?"
            if has_source
            else "- Is each distractor plausible to a student with partial knowledge of the topic?\n"
            "   - Would a student who partially understands the concept find it attractive?\n"
            "   - Are any distractors transparently wrong or clearly unrelated?"
        )

        return f"""You are a pedagogical assessment expert. Analyze the distractors in this quiz question WITHOUT assigning a score yet.

{source_section}

Question: {question.question_text}
Correct Answer(s): {correct_display}
Distractors:
{distractors_text or "(none provided)"}

Analyze the distractors across these five dimensions:

1. {plausibility_label}
   {plausibility_detail}

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
  "difficulty_calibration": "<audience-level fit analysis>",
  "source_grounded": {str(has_source).lower()}
}}"""

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        analyze_output = inp.accumulated.get("analyze")
        if analyze_output is None:
            raise ValueError(
                "distractor_quality judge phase requires 'analyze' phase output in accumulated"
            )

        analysis = analyze_output.data
        source_grounded = analysis.get("source_grounded", True)

        alignment_label = "source alignment" if source_grounded else "knowledge alignment"

        return f"""You are a strict pedagogical assessment examiner. Based solely on the analysis below, assign a categorical quality verdict.

ANALYSIS TO JUDGE:
Plausibility & {alignment_label}: {analysis.get("plausibility_analysis")}
Misconception targeting:         {analysis.get("misconception_analysis")}
Discriminatory power:            {analysis.get("discrimination_analysis")}
Collective quality:              {analysis.get("collective_analysis")}
Audience calibration:            {analysis.get("difficulty_calibration")}

VERDICT DEFINITIONS:
- "excellent": Highly plausible, exploits specific student errors, covers distinct misconceptions,
               calibrated to audience, set is collectively strong with no cannibalization.
               Should be genuinely rare.
- "good":      Grounded in {'source material' if source_grounded else 'domain knowledge'}, requires real knowledge to eliminate.
               Minor weaknesses in one or two dimensions.
- "fair":      Plausible but generic; not strongly grounded in {'source material' if source_grounded else 'domain knowledge'}
               or real misconceptions. Multiple dimensions weak.
- "poor":      Distractors are absurd, unrelated, easily eliminated by common sense,
               or obviously wrong to any reader.

DEDUCTION TRIGGERS (use these to guide your verdict):
- Any distractor eliminable by common sense alone → lowers verdict
- Any distractor not tied to {'the source material' if source_grounded else 'domain concepts'} (generic) → lowers verdict
- Two or more distractors exploit the same misconception → lowers verdict
- Any distractor inadvertently hints at the correct answer → lowers verdict
- Distractor set poorly calibrated for the expected audience → lowers verdict
- A predictable, obvious student error is missing as a distractor → lowers verdict

Keep your analysis extremely punchy and concise.

Respond with ONLY a JSON object matching this schema:
{{
    "quality_level": "excellent" | "good" | "fair" | "poor",
    "deduction_summary": "<list each issue found, or 'No issues.'>",
    "rationale": "<brief reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> Dict[str, Any]:
        """Derive the score from the judge's quality level."""
        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        level = judged["quality_level"]

        return {
            "quality_level": level,
            "deduction_summary": judged.get("deduction_summary", ""),
            "rationale": judged.get("rationale", ""),
            "score": QUALITY_SCORES[level],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            level = data.get("quality_level")
            score = data.get("score")
            if level is None:
                return None

            lines = [
                f"\n[Q: {quiz_id}] Distractor Quality: {level} ({score}/100)",
                f"   Deductions: {data.get('deduction_summary')}",
                f"   Rationale:  {data.get('rationale')}",
                "-" * 65,
            ]
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse distractor quality insights: {str(e)}"
