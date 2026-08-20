"""Grammatical Correctness metric implementation."""

import json
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricParameter, MetricScope
from .phase import Phase, PhaseInput

# The four severity levels, best to worst, evenly spaced. No midpoint: an item
# either reads cleanly or it does not, and "somewhere in between" is not a
# useful verdict about prose.
SEVERITY_SCORES = {
    "none": 100.0,
    "minor": 66.7,
    "major": 33.3,
    "critical": 0.0,
}


class GrammarJudgeResponse(BaseModel):
    """The judge's severity verdict and the issues behind it. Carries no score."""

    model_config = ConfigDict(extra="forbid")

    severity: Literal["none", "minor", "major", "critical"]
    grammar_issues: List[str] = Field(default_factory=list)
    spelling_issues: List[str] = Field(default_factory=list)
    punctuation_issues: List[str] = Field(default_factory=list)
    rationale: str


class GrammaticalCorrectnessResponse(GrammarJudgeResponse):
    """Final output: the judge's severity plus the score derived from it."""

    score: float = Field(ge=0, le=100)


class GrammaticalCorrectnessMetric(BaseMetric):
    """Evaluates the grammatical correctness of a single quiz item.

    Scores the stem and every option together: one broken option makes the item
    worse regardless of how clean the rest reads. The judge picks a severity and
    the score follows from it, so a verdict and its number cannot disagree.

    Grammar is always assessed in the language the item is actually written in.
    A well-written German item scores well even if English was requested --
    language mismatch is an instruction-compliance question, handled separately,
    and folding it in here would conflate two different failures.
    """

    @property
    def name(self) -> str:
        return "grammatical_correctness"

    @property
    def version(self) -> str:
        return "2.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def parameters(self) -> List[MetricParameter]:
        return [
            MetricParameter(
                name="language",
                param_type=str,
                default="English",
                description="Language for grammatical evaluation",
            ),
        ]

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("judge", GrammarJudgeResponse),
            Phase("finalize", GrammaticalCorrectnessResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    def _build_judge_prompt(self, inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("grammatical_correctness judge phase requires a question")

        question = inp.question
        language = self.get_param_value("language", **inp.params)
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        return f"""You are evaluating the grammatical correctness of a single quiz item.

Language: {language}

**Item**:
Question Type: {question.question_type.value}
Stem: {question.question_text}
Options:
{options_text}
Marked Correct Answer: {question.correct_answer}

**What to evaluate** -- the stem AND every option, not just the stem:
1. Grammar: subject-verb agreement, tense, article usage (a/an/the), pronoun agreement, sentence structure.
2. Spelling: misspellings, typos, character errors. Technical terms must be spelled correctly.
3. Punctuation: commas, periods, question marks, apostrophes, quotation marks, punctuation in lists.
4. Capitalization: sentence case, proper nouns, consistency across options.
5. Sentence structure: complete sentences, no fragments or run-ons, parallel construction in lists.
6. Technical writing: consistent formatting, professional tone, appropriate terminology.
7. Terminology consistency, where an inconsistency affects grammar or readability.

**Guidelines**:
- Apply the standard grammar rules of {language}. Judge the item in the language it is actually written in, even if that is not {language} -- do not deduct for the language itself being different.
- An error in any option counts, not only errors in the stem.
- Judge the writing, not the content: a factually wrong but well-written item has no grammar problem.

**Severity**:
- "none": no errors; professional quality throughout.
- "minor": small issues only -- a typo, a missing comma, inconsistent capitalization.
- "major": clear grammatical errors that disrupt reading flow.
- "critical": errors that obscure the meaning or make the item hard to understand.

List the specific issues you found in the matching category. Leave a list empty when that category is clean.

Respond with ONLY a JSON object matching this schema:
{{
  "severity": "none" | "minor" | "major" | "critical",
  "grammar_issues": ["specific issue", ...],
  "spelling_issues": ["specific issue", ...],
  "punctuation_issues": ["specific issue", ...],
  "rationale": "<reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> Dict[str, Any]:
        """Derive the score from the judge's severity level."""
        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        severity = judged["severity"]

        return {
            "severity": severity,
            "grammar_issues": judged.get("grammar_issues", []),
            "spelling_issues": judged.get("spelling_issues", []),
            "punctuation_issues": judged.get("punctuation_issues", []),
            "rationale": judged.get("rationale", ""),
            "score": SEVERITY_SCORES[severity],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            severity = data.get("severity")
            if severity is None:
                return None

            lines = [
                f"\n[Question ID: {quiz_id}] Grammatical Correctness:",
                "-" * 50,
                f"Severity: {severity}",
                f"Score:    {data.get('score')}/100",
            ]

            for label, key in (
                ("Grammar", "grammar_issues"),
                ("Spelling", "spelling_issues"),
                ("Punctuation", "punctuation_issues"),
            ):
                issues = data.get(key, [])
                if issues:
                    lines.append(f"{label}:")
                    for issue in issues:
                        lines.append(f"  - {issue}")
                else:
                    lines.append(f"{label}: None")

            lines.append(f"Rationale: {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse grammatical correctness insights: {str(e)}"
