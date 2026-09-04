"""Redundancy and cross-item cueing metric (quiz-level).

Answers one question per quiz: do items duplicate each other, or does one item
reveal another's answer? Both are defects of the set. An item that is flawless
read on its own becomes a bad item when the quiz already asked the same thing
three questions earlier, or when its stem states the fact that another item's
key turns on.

Distinct from `absence_of_cueing`, which asks whether an item's OWN options
give its key away. The cue here travels between items, so no per-item metric
can see it.

The verdict carries named item pairs, mirroring the human instrument: a rater
who scores a quiz at the lower two levels has to say which items are involved.
Agreeing that a quiz is redundant is weaker evidence than agreeing about which
pair makes it so, and the pairs are what make that second comparison possible.
"""

import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput
from .quiz_level import MIN_QUIZ_ITEMS, NOT_APPLICABLE_SCORE, render_items, verdict_scores

# Best to worst. "mild_overlap" is topical overlap where each item still tests
# something of its own; "clear_overlap" is a duplicate pair or an item that
# narrows another's options; "substantial" is an item that plainly gives another
# away.
REDUNDANCY_SCORES = verdict_scores(("none", "mild_overlap", "clear_overlap", "substantial"))

# The two levels at which the human instrument requires the pairs to be named.
LEVELS_REQUIRING_PAIRS = ("clear_overlap", "substantial")

RedundancyLevel = Literal["none", "mild_overlap", "clear_overlap", "substantial", "not_applicable"]


class ItemPair(BaseModel):
    """Two items of the quiz that duplicate each other, or where one gives the other away."""

    model_config = ConfigDict(extra="forbid")

    question_ids: list[str] = Field(min_length=2, max_length=2)
    kind: Literal["redundancy", "cueing"]
    explanation: str


class CrossItemRedundancyJudgeResponse(BaseModel):
    """The judge's verdict and its evidence. Deliberately carries no score.

    The pairs come before the verdict: the level follows from what was found
    between which items, and a level chosen first invites the pairs to be
    back-filled to match it.
    """

    model_config = ConfigDict(extra="forbid")

    pairs: list[ItemPair] = Field(default_factory=list)
    rationale: str
    redundancy_level: Literal["none", "mild_overlap", "clear_overlap", "substantial"]


class CrossItemRedundancyResponse(CrossItemRedundancyJudgeResponse):
    """Final output: the judge's level, the surviving pairs, and the score."""

    redundancy_level: RedundancyLevel  # type: ignore[assignment]
    applicable: bool
    num_questions: int
    pairs_dropped: int = 0
    score: float = Field(ge=0, le=100)


class CrossItemRedundancyMetric(BaseMetric):
    """Evaluates whether a quiz's items duplicate each other or give each other away.

    Two phases: an LLM judge over the whole quiz, then a deterministic pass that
    derives the score from the judge's level and overrides the verdict for
    quizzes too short to have cross-item problems. The deterministic pass runs
    last because only the final phase's data reaches ``raw_response``.
    """

    @property
    def name(self) -> str:
        return "cross_item_redundancy"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def phases(self) -> list[Phase]:
        return [
            Phase("judge", CrossItemRedundancyJudgeResponse),
            Phase("finalize", CrossItemRedundancyResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.quiz is None:
            raise ValueError("cross_item_redundancy judge phase requires a quiz")

        if inp.quiz.num_questions < MIN_QUIZ_ITEMS:
            # Too few items for a cross-item problem to be worth judging. The
            # verdict is settled deterministically in _finalize and this answer
            # is discarded, so keep the call cheap.
            return f"""This quiz holds fewer than {MIN_QUIZ_ITEMS} items, so it has no cross-item redundancy to judge.

Respond with ONLY this JSON object, exactly as written:
{{
  "pairs": [],
  "rationale": "Too few items to have cross-item redundancy.",
  "redundancy_level": "none"
}}"""

        return f"""Judge whether the items of the quiz below duplicate each other or give each other away.

**Quiz Items** ({inp.quiz.num_questions} in total):
{render_items(inp.quiz)}

**How to decide**:
- Compare the items against each other, not against a standard. Every defect here is a relation between two items; an item read alone cannot show it.
- Look for two things:
  - REDUNDANCY: two items test the same knowledge, so answering one correctly all but guarantees the other. Testing the same TOPIC from a different angle is not redundancy.
  - CROSS-ITEM CUEING: one item's stem, options, or marked answer reveals or narrows another item's answer. The direction matters -- say which item gives which away.
- First name the pairs you find, with the kind and a short explanation each. Choose the level afterwards, from what you found.
- If you find nothing, return an empty list of pairs and the level "none". Do not manufacture a pair to justify a level.
- Items that share a topic because the quiz is about that topic are not thereby redundant.

**Levels**:
- "none": no redundancy; no item helps answer another.
- "mild_overlap": mild overlap in topic, but each item still tests something of its own.
- "clear_overlap": a clear duplicate pair, or one item that narrows another's options.
- "substantial": substantial redundancy, or an item that plainly gives away another's answer.

For "clear_overlap" and "substantial" you MUST name at least one pair.

Respond with ONLY a JSON object matching this schema:
{{
  "pairs": [
    {{
      "question_ids": ["<id of the first item>", "<id of the second item>"],
      "kind": "redundancy" | "cueing",
      "explanation": "<what is duplicated, or which item gives which away and how>"
    }}
  ],
  "rationale": "<reasoning>",
  "redundancy_level": "none" | "mild_overlap" | "clear_overlap" | "substantial"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> dict[str, Any]:
        """Derive the score from the judge's level, or mark the quiz not applicable."""
        if inp.quiz is None:
            raise ValueError("cross_item_redundancy finalize phase requires a quiz")

        num_questions = inp.quiz.num_questions
        if num_questions < MIN_QUIZ_ITEMS:
            return {
                "redundancy_level": "not_applicable",
                "applicable": False,
                "num_questions": num_questions,
                "pairs": [],
                "pairs_dropped": 0,
                "rationale": (
                    f"A quiz of {num_questions} item(s) has no cross-item redundancy to judge; "
                    f"{MIN_QUIZ_ITEMS} are required."
                ),
                "score": NOT_APPLICABLE_SCORE,
            }

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        level = judged["redundancy_level"]

        # A pair naming an item this quiz does not contain, or naming one item
        # twice, is not evidence of anything. Drop it and record that it was
        # dropped: a judge that reaches "substantial" and then cannot name a
        # real pair is a finding, not a detail to smooth over.
        known_ids = {question.question_id for question in inp.quiz.questions}
        pairs = []
        dropped = 0
        for pair in judged.get("pairs", []):
            question_ids = pair.get("question_ids", [])
            if len(set(question_ids)) == 2 and set(question_ids) <= known_ids:
                pairs.append(
                    {
                        "question_ids": list(question_ids),
                        "kind": pair.get("kind", "redundancy"),
                        "explanation": pair.get("explanation", ""),
                    }
                )
            else:
                dropped += 1

        return {
            "redundancy_level": level,
            "applicable": True,
            "num_questions": num_questions,
            "pairs": pairs,
            "pairs_dropped": dropped,
            "rationale": judged.get("rationale", ""),
            "score": REDUNDANCY_SCORES[level],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> str | None:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            level = data.get("redundancy_level")
            if level is None:
                return None

            lines = [
                f"\n[Quiz ID: {quiz_id}] Redundancy and Cross-Item Cueing:",
                "-" * 50,
            ]

            if not data.get("applicable", True):
                lines.append(
                    f"Not applicable: fewer than {MIN_QUIZ_ITEMS} items "
                    f"({data.get('num_questions')})."
                )
                lines.append("-" * 50)
                return "\n".join(lines)

            lines.extend(
                [
                    f"Redundancy: {level}",
                    f"Score:      {data.get('score')}/100",
                ]
            )

            pairs = data.get("pairs", [])
            lines.append("Pairs:" if pairs else "Pairs:      None")
            for pair in pairs:
                question_ids = pair.get("question_ids", [])
                lines.append(
                    f"  - {' + '.join(question_ids)} [{pair.get('kind')}]: "
                    f"{pair.get('explanation')}"
                )

            dropped = data.get("pairs_dropped", 0)
            if dropped:
                lines.append(f"Dropped:    {dropped} pair(s) naming items not in this quiz")

            lines.append(f"Rationale:  {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse cross-item redundancy insights: {e!s}"
