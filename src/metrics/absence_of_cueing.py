"""Absence-of-cueing metric.

Answers one question per item: can a respondent pick the key from clues in the
item's construction, without knowing the subject? That is a detection question,
not a matter of degree -- either the item gives the answer away or it does not --
so the score is binary. Severity rides along as a descriptive field for anyone
who later wants to separate a nudge from a giveaway.

Factual correctness is out of scope here. An item can be perfectly accurate and
still hand over its key.
"""

import json
from collections.abc import Callable
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models.quiz import QuestionType, QuizQuestion
from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput

# The complete cue vocabulary. A judge label outside this set is dropped, so the
# reported types stay a fixed vocabulary that is safe to aggregate over.
CUE_TYPES = ("grammatical", "semantic", "length", "convergence", "other")

# ponytail: a deliberately blunt length heuristic, and advisory only -- it is fed
# to the judge as one signal among several and never decides the verdict itself.
# A key can be legitimately longer than its distractors without giving anything
# away, which is exactly the call a model is better placed to make than a ratio.
LENGTH_OUTLIER_RATIO = 1.5
LENGTH_OUTLIER_MIN_DELTA = 20


def analyze_length_signal(question: QuizQuestion) -> dict[str, Any]:
    """Flag the keyed option as a length outlier against its distractors.

    Conservative on purpose: the key must be both proportionally and absolutely
    longer than the typical distractor before this reports anything. Returns a
    structured signal for the prompt rather than a verdict.
    """
    signal: dict[str, Any] = {
        "keyed_option_is_outlier": False,
        "keyed_lengths": [],
        "median_distractor_length": None,
        "note": "",
    }

    # True/false items have fixed options, so option length carries no signal.
    if question.question_type == QuestionType.TRUE_FALSE:
        signal["note"] = "Not applicable to true/false items."
        return signal

    answer = question.correct_answer
    keyed = {str(a) for a in (answer if isinstance(answer, list) else [answer])}
    keyed_options = [o for o in question.options if str(o) in keyed]
    distractors = [o for o in question.options if str(o) not in keyed]

    if not keyed_options or not distractors:
        signal["note"] = "Not enough options to compare."
        return signal

    keyed_lengths = [len(str(o)) for o in keyed_options]
    distractor_median = median(len(str(o)) for o in distractors)
    longest_key = max(keyed_lengths)

    signal["keyed_lengths"] = keyed_lengths
    signal["median_distractor_length"] = distractor_median
    signal["keyed_option_is_outlier"] = (
        distractor_median > 0
        and longest_key >= LENGTH_OUTLIER_RATIO * distractor_median
        and longest_key - distractor_median >= LENGTH_OUTLIER_MIN_DELTA
    )
    signal["note"] = (
        f"Longest keyed option is {longest_key} characters against a median distractor "
        f"length of {distractor_median}."
    )
    return signal


class CueingJudgeResponse(BaseModel):
    """The judge's detection verdict and its evidence. Deliberately carries no score."""

    model_config = ConfigDict(extra="forbid")

    cue_present: bool
    severity: Literal["none", "minor", "strong"]
    cue_types: list[str] = Field(default_factory=list)
    key_revealed_by: list[str] = Field(default_factory=list)
    rationale: str


class CueingResponse(CueingJudgeResponse):
    """Final output: the verdict, the deterministic length signal, and the score."""

    length_signal: dict[str, Any] = Field(default_factory=dict)
    score: float = Field(ge=0, le=100)


class AbsenceOfCueingMetric(BaseMetric):
    """Evaluates whether an item avoids clues that reveal its key.

    Two phases: an LLM judge, then a deterministic pass that derives the score
    and reconciles severity with the verdict. High scores mean fewer cues.
    """

    @property
    def name(self) -> str:
        return "absence_of_cueing"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> list[Phase]:
        return [
            Phase("judge", CueingJudgeResponse),
            Phase("finalize", CueingResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("absence_of_cueing judge phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))
        length_signal = analyze_length_signal(question)

        return f"""Judge whether the quiz item below gives its answer away through clues in how it is written.

**Item**:
Question Type: {question.question_type.value}
Stem: {question.question_text}
Options:
{options_text}
Marked Correct Answer (key): {question.correct_answer}

**Deterministic length measurement** (one signal among several -- weigh it, do not defer to it):
{json.dumps(length_signal, ensure_ascii=True)}

**What to judge**:
Ignore factual correctness entirely. A perfectly accurate item can still hand over its key. The only question is whether someone who does not know the subject could pick the key from how the item is constructed.

Check all three directions:
- Stem to key: does stem wording, grammar, or a distinctive term point at the key alone?
- Key to distractors: does the key stand out from the other options in a way that singles it out?
- Across the option set: do the options overlap or converge such that one is logically implied?

**Cue types** (use these exact names; leave the list empty when there is no cue):
- "grammatical": article, number, or tense agreement with the stem fits only the key.
- "semantic": stem wording or a distinctive term is echoed only in the key.
- "length": the key is conspicuously longer, shorter, or more qualified than the distractors.
- "convergence": the key combines elements repeated across distractors, or option overlap logically implies it.
- "other": any other construction clue -- for example the key being uniquely detailed, hedged, or technically precise, or distractors weakened by absolute terms. Say which in the rationale.

**Boundary with option homogeneity**: an item whose options are not parallel is not automatically cueing. A homogeneity break that does not point at the key is not a cue here. Report a cue only when something singles the key out. Grammatical cues are necessarily also homogeneity breaks -- still report them, since they do point at the key.

**Severity**: "none" when there is no cue, "minor" when a cue may help but does not make the key obvious, "strong" when a cue likely reveals it.

Respond with ONLY a JSON object matching this schema:
{{
  "cue_present": <true or false>,
  "severity": "none" | "minor" | "strong",
  "cue_types": ["grammatical", ...],
  "key_revealed_by": ["the specific wording or feature that gives it away", ...],
  "rationale": "<reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> dict[str, Any]:
        """Derive the score and reconcile severity with the detection verdict."""
        if inp.question is None:
            raise ValueError("absence_of_cueing finalize phase requires a question")

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        cue_present = bool(judged["cue_present"])
        severity = judged["severity"]

        # "a cue is present" and "severity is none" cannot both be true. The
        # detection verdict is the primary unit, so severity yields to it.
        if cue_present and severity == "none":
            severity = "minor"
        elif not cue_present:
            severity = "none"

        cue_types = [t for t in CUE_TYPES if t in set(judged.get("cue_types", []))]

        return {
            "cue_present": cue_present,
            "severity": severity,
            "cue_types": cue_types if cue_present else [],
            "key_revealed_by": judged.get("key_revealed_by", []) if cue_present else [],
            "rationale": judged.get("rationale", ""),
            "length_signal": analyze_length_signal(inp.question),
            "score": 0.0 if cue_present else 100.0,
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> str | None:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            cue_present = data.get("cue_present")
            if cue_present is None:
                return None

            lines = [
                f"\n[Question ID: {quiz_id}] Absence of Cueing:",
                "-" * 50,
                f"Cue present: {'Yes' if cue_present else 'No'}",
                f"Score:       {data.get('score')}/100",
                f"Severity:    {data.get('severity')}",
                f"Cue types:   {', '.join(data.get('cue_types', [])) or 'None'}",
            ]

            revealed_by = data.get("key_revealed_by", [])
            if revealed_by:
                lines.append("Key revealed by:")
                for item in revealed_by:
                    lines.append(f"  - {item}")

            lines.append(f"Rationale:   {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse absence of cueing insights: {e!s}"
