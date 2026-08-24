"""Answer-key correctness metric.

Answers one question per item: is the marked answer key correct and
unambiguous? A key is either sound or it is not -- there is no useful middle
ground between "this item has a defensible key" and "this item does not" -- so
the score is binary (100 or 0) rather than an ordinal, and the mean over a quiz
reads directly as the share of items with a sound key. When the key fails, one
or more issue flags say why.
"""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput

# The complete set of ways a key can fail. A judge flag outside this set is dropped,
# so the reported flags stay a fixed vocabulary that is safe to aggregate over.
ISSUE_FLAGS = (
    "multiple_defensible",
    "keyed_answer_wrong",
    "no_correct_option",
    "catch_all_present",
)

# ponytail: the option must OPEN with one of these phrases and have little left
# after it. Both guards earn their keep against real distractors: anchoring
# rejects "a list of all listed items", and the tail bound rejects "all answers
# are stored in a hash map" while still accepting "all of the above answers are
# correct". The corpus is mixed English/German with no reliable per-question
# language signal, so both lists are matched unconditionally. Known ceiling: a
# catch-all buried mid-option ("I think none of the above") is missed; extend
# the phrase list or raise the bound if a real item slips through.
CATCH_ALL_MAX_TAIL_WORDS = 4
CATCH_ALL_PHRASES = (
    "all of the above",
    "none of the above",
    "all answers",
    "none of these",
    "all listed",
    "no answer is correct",
    "alle genannten",
    "alle antworten",
    "keine der genannten",
    "keine antwort",
    "nichts davon",
    "alle oben genannten",
)


def detect_catch_all_options(options: list[str]) -> list[str]:
    """Return the options whose normalized text opens with a catch-all phrase."""
    found = []
    for option in options:
        normalized = " ".join(str(option).lower().split()).lstrip(
            "([-\u2013\u2014.,:;'\"\u201c\u201e "
        )
        for phrase in CATCH_ALL_PHRASES:
            if not normalized.startswith(phrase):
                continue
            if len(normalized[len(phrase) :].split()) <= CATCH_ALL_MAX_TAIL_WORDS:
                found.append(option)
            break
    return found


class AnswerKeyJudgeResponse(BaseModel):
    """The judge's verdict and its diagnostics. Deliberately carries no score.

    The judge decides only whether the key is sound; the number is derived from
    that verdict in ``_finalize``, so a model cannot smuggle in a middle ground.
    """

    model_config = ConfigDict(extra="forbid")

    key_correct: bool
    defensible_correct_options: list[str] = Field(default_factory=list)
    misclassified_options: list[str] = Field(default_factory=list)
    issue_flags: list[str] = Field(default_factory=list)
    rationale: str


class AnswerKeyCorrectnessResponse(AnswerKeyJudgeResponse):
    """Final output: the judge verdict after the deterministic rules are applied."""

    catch_all_options: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=100)


class AnswerKeyCorrectnessMetric(BaseMetric):
    """Evaluates whether the marked answer key is correct and unambiguous.

    Two phases: an LLM judge, then a deterministic pass enforcing the two rules
    a judge is prone to miss -- a catch-all option ("all of the above") and an
    empty key both fail outright, however plausible the item looks otherwise.
    The deterministic pass runs last because only the final phase's data reaches
    ``raw_response``, and because a rule that a model can talk itself out of is
    not a rule.
    """

    @property
    def name(self) -> str:
        return "answer_key_correctness"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> list[Phase]:
        return [
            Phase("judge", AnswerKeyJudgeResponse),
            Phase("finalize", AnswerKeyCorrectnessResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("answer_key_correctness judge phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        source_context = (
            f"Source Material:\n{inp.source_text}"
            if inp.source_text
            else "No source material is available. Judge using general expert knowledge "
            "and the item wording alone."
        )

        context_lines = [
            f"{label}: {question.metadata[key]}"
            for key, label in (("domain", "Domain"), ("learning_objective", "Learning Objective"))
            if question.metadata.get(key)
        ]
        item_context = "\n".join(context_lines) if context_lines else "No additional context."

        return f"""Answer this question about the quiz item below: is the marked answer key correct and unambiguous?

{source_context}

**Item Context**:
{item_context}

**Item**:
Question Type: {question.question_type.value}
Stem: {question.question_text}
Options:
{options_text}
Marked Correct Answer (key): {question.correct_answer}

**How to decide**:
- First identify the FULL set of options that are defensibly correct, before looking at whether the marked key matches it.
- single_choice / true_false: exactly one option is unambiguously correct, and it is the keyed one.
- multiple_choice: the keyed SET must equal the unambiguously-correct SET. Compare sets, not individual labels: every keyed option must be correct AND no unkeyed option may also be defensible.

**Issue flags** (use these exact names; leave the list empty when the key is correct):
- "keyed_answer_wrong": a keyed option is actually incorrect.
- "multiple_defensible": an unkeyed option is also defensible, i.e. the key omits a correct option.
- "no_correct_option": none of the options is correct.
- "catch_all_present": an "all of the above" / "none of the above" style option appears.

A catch-all option violates this criterion even when it is technically the correct answer.

Record which option(s) are misclassified in "misclassified_options", and explain why in "rationale".

There is no "unsure" verdict. Commit to true or false for "key_correct".

Respond with ONLY a JSON object matching this schema:
{{
  "key_correct": <true or false>,
  "defensible_correct_options": ["option text", ...],
  "misclassified_options": ["option text", ...],
  "issue_flags": ["keyed_answer_wrong", ...],
  "rationale": "<reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> dict[str, Any]:
        """Apply the deterministic rules on top of the judge's verdict."""
        if inp.question is None:
            raise ValueError("answer_key_correctness finalize phase requires a question")

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        flags = {f for f in judged.get("issue_flags", []) if f in ISSUE_FLAGS}
        key_correct = bool(judged["key_correct"])

        # Both of these are objective properties of the item, not judgement
        # calls, so either one firing fails the key whatever the judge said.
        catch_all_options = detect_catch_all_options(inp.question.options)
        if catch_all_options:
            flags.add("catch_all_present")
            key_correct = False

        answer = inp.question.correct_answer
        keyed = answer if isinstance(answer, list) else [answer]
        if not [a for a in keyed if str(a).strip()]:
            flags.add("no_correct_option")
            key_correct = False

        return {
            "key_correct": key_correct,
            "defensible_correct_options": judged.get("defensible_correct_options", []),
            "misclassified_options": judged.get("misclassified_options", []),
            "issue_flags": [f for f in ISSUE_FLAGS if f in flags],
            "rationale": judged.get("rationale", ""),
            "catch_all_options": catch_all_options,
            "score": 100.0 if key_correct else 0.0,
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> str | None:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            key_correct = data.get("key_correct")
            if key_correct is None:
                return None

            lines = [
                f"\n[Question ID: {quiz_id}] Answer-Key Correctness:",
                "-" * 50,
                f"Key correct & unambiguous: {'Yes' if key_correct else 'No'}",
                f"Score:                     {data.get('score')}/100",
                f"Defensibly correct:        {data.get('defensible_correct_options') or 'None listed'}",
                f"Misclassified options:     {data.get('misclassified_options') or 'None'}",
                f"Catch-all options:         {data.get('catch_all_options') or 'None'}",
            ]

            flags = data.get("issue_flags", [])
            if flags:
                lines.append("Issue flags:")
                for flag in flags:
                    lines.append(f"  - {flag}")
            else:
                lines.append("Issue flags:               None")

            lines.append(f"Rationale:                 {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse answer-key correctness insights: {e!s}"
