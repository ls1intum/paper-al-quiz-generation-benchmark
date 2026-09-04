"""Learning-objective balance metric (quiz-level).

Answers one question per quiz: given the objectives the quiz declares for
itself, are they weighted sensibly across its items, or does the quiz over-invest
in one objective and barely touch another?

This is a question about *emphasis*, not about coverage. A quiz is not penalized
here for leaving an objective out, and the objectives themselves are not judged
-- a badly written objective that the items serve evenly scores at the top.
Coverage is a different construct with a different reference value, and mixing
the two would make one number mean two things.

Not to be confused with `objective_alignment`, which asks per item whether that
item assesses *its own* stated objective. An item can align perfectly while the
quiz around it is badly unbalanced, and a quiz can be perfectly balanced across
objectives its items assess only weakly.
"""

import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput
from .quiz_level import NOT_APPLICABLE_SCORE, declared_objectives, render_items, verdict_scores

# Best to worst. The wording of each level tracks the rater anchors: an even
# spread, a slight tilt, one objective dominating a thin one, and a quiz that
# effectively tests a single objective.
BALANCE_SCORES = verdict_scores(("balanced", "slightly_uneven", "unbalanced", "skewed"))

BalanceLevel = Literal["balanced", "slightly_uneven", "unbalanced", "skewed", "not_applicable"]


class ObjectiveItemCount(BaseModel):
    """Which of the quiz's items the judge attributes to one declared objective.

    The objective is identified by its 1-based position in the declared list,
    not by its text. Declared objectives in the real corpus are multi-sentence
    strings of 190-360 characters; asking a model to reproduce one verbatim so
    the attribution can be matched back is a request it will fail often and
    silently, and every near-miss would be discarded as unverifiable.
    """

    model_config = ConfigDict(extra="forbid")

    objective_index: int
    question_ids: list[str] = Field(default_factory=list)


class ResolvedObjectiveItemCount(ObjectiveItemCount):
    """An attribution after `_finalize` has resolved the index back to its text."""

    objective: str


class ObjectiveBalanceJudgeResponse(BaseModel):
    """The judge's verdict and its evidence. Deliberately carries no score.

    ``objective_item_counts`` comes before the verdict on purpose: the judge has
    to attribute items to objectives before it can say anything about balance,
    and a verdict reached before that attribution is a guess.
    """

    model_config = ConfigDict(extra="forbid")

    objective_item_counts: list[ObjectiveItemCount] = Field(default_factory=list)
    rationale: str
    balance_level: Literal["balanced", "slightly_uneven", "unbalanced", "skewed"]


class ObjectiveBalanceResponse(ObjectiveBalanceJudgeResponse):
    """Final output: the judge's level, the objectives it was judged against, and the score."""

    balance_level: BalanceLevel  # type: ignore[assignment]
    objective_item_counts: list[ResolvedObjectiveItemCount] = Field(  # type: ignore[assignment]
        default_factory=list
    )
    applicable: bool
    declared_objectives: list[str] = Field(default_factory=list)
    attributions_dropped: int = 0
    score: float = Field(ge=0, le=100)


class ObjectiveBalanceMetric(BaseMetric):
    """Evaluates how evenly a quiz spreads its items across its declared objectives.

    Two phases: an LLM judge over the whole quiz, then a deterministic pass that
    derives the score from the judge's level and overrides the verdict for
    quizzes that declare no objectives. The deterministic pass runs last because
    only the final phase's data reaches ``raw_response``.
    """

    @property
    def name(self) -> str:
        return "objective_balance"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def phases(self) -> list[Phase]:
        return [
            Phase("judge", ObjectiveBalanceJudgeResponse),
            Phase("finalize", ObjectiveBalanceResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.quiz is None:
            raise ValueError("objective_balance judge phase requires a quiz")

        objectives = declared_objectives(inp.quiz)
        if not objectives:
            # Nothing to balance against. The verdict is settled deterministically
            # in _finalize and this answer is discarded, so keep the call cheap.
            return """This quiz declares no learning objectives, so there is nothing to weigh its items against.

Respond with ONLY this JSON object, exactly as written:
{
  "objective_item_counts": [],
  "rationale": "The quiz declares no learning objectives.",
  "balance_level": "balanced"
}"""

        objectives_text = "\n".join(
            f"{i}. {objective}" for i, objective in enumerate(objectives, 1)
        )

        return f"""Judge how evenly the quiz below spreads its items across the objectives it declares.

**Declared Learning Objectives** (the reference set -- judge against these and nothing else):
{objectives_text}

**Quiz Items** ({inp.quiz.num_questions} in total):
{render_items(inp.quiz)}

**How to decide**:
- First attribute each item to the declared objective it mainly serves. An item may serve more than one; an item may serve none of them. Choose the level afterwards, from that attribution.
- Judge the BALANCE OF EMPHASIS: does every declared objective carry a fair share of the items, or does one dominate while another is represented by a single thin item?
- Do NOT judge coverage. An objective with no item is not what this criterion measures, and a quiz is not penalized here for leaving one out.
- Do NOT judge the objectives themselves. Whether they are well written, well chosen, or appropriately scoped is outside this criterion.
- Do NOT judge whether an item assesses its objective well. That is a separate criterion applied per item.
- Weigh the objectives as equally important unless the quiz says otherwise. Item count is the evidence; a longer or harder item is not thereby two items.

**Levels**:
- "balanced": emphasis is spread sensibly; every declared objective gets a fair share of the items.
- "slightly_uneven": one objective carries a little more or a little less weight than it warrants.
- "unbalanced": one objective clearly dominates while another is represented by a single thin item.
- "skewed": badly lopsided; the quiz effectively tests one objective and pays lip service to the rest.

Respond with ONLY a JSON object matching this schema:
{{
  "objective_item_counts": [
    {{"objective_index": <the objective's number above>, "question_ids": ["<id>", ...]}}
  ],
  "rationale": "<reasoning>",
  "balance_level": "balanced" | "slightly_uneven" | "unbalanced" | "skewed"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> dict[str, Any]:
        """Derive the score from the judge's level, or mark the quiz not applicable."""
        if inp.quiz is None:
            raise ValueError("objective_balance finalize phase requires a quiz")

        objectives = declared_objectives(inp.quiz)
        if not objectives:
            return {
                "balance_level": "not_applicable",
                "applicable": False,
                "declared_objectives": [],
                "objective_item_counts": [],
                "attributions_dropped": 0,
                "rationale": "The quiz declares no learning objectives.",
                "score": NOT_APPLICABLE_SCORE,
            }

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        level = judged["balance_level"]

        # Keep only attributions the judge could actually have made: an index
        # into the declared list, and ids of items that are in this quiz. A
        # hallucinated id would otherwise travel into the analysis as evidence.
        # Anything discarded is counted rather than absorbed -- an empty
        # attribution list must be distinguishable from one we threw away.
        known_ids = {question.question_id for question in inp.quiz.questions}
        counts = []
        dropped = 0
        for entry in judged.get("objective_item_counts", []):
            index = entry.get("objective_index")
            if not isinstance(index, int) or not 1 <= index <= len(objectives):
                dropped += 1
                continue
            counts.append(
                {
                    "objective_index": index,
                    "objective": objectives[index - 1],
                    "question_ids": [
                        qid for qid in entry.get("question_ids", []) if qid in known_ids
                    ],
                }
            )

        return {
            "balance_level": level,
            "applicable": True,
            "declared_objectives": objectives,
            "objective_item_counts": counts,
            "attributions_dropped": dropped,
            "rationale": judged.get("rationale", ""),
            "score": BALANCE_SCORES[level],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> str | None:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            level = data.get("balance_level")
            if level is None:
                return None

            lines = [
                f"\n[Quiz ID: {quiz_id}] Learning-Objective Balance:",
                "-" * 50,
            ]

            if not data.get("applicable", True):
                lines.append("Not applicable: the quiz declares no learning objectives.")
                lines.append("-" * 50)
                return "\n".join(lines)

            lines.extend(
                [
                    f"Balance:    {level}",
                    f"Score:      {data.get('score')}/100",
                    "Items per declared objective:",
                ]
            )

            for entry in data.get("objective_item_counts", []):
                question_ids = entry.get("question_ids", [])
                lines.append(
                    f"  - {entry.get('objective')}: {len(question_ids)} "
                    f"({', '.join(question_ids) if question_ids else 'none'})"
                )

            dropped = data.get("attributions_dropped", 0)
            if dropped:
                lines.append(f"Dropped:    {dropped} attribution(s) naming no declared objective")

            lines.append(f"Rationale:  {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse objective balance insights: {e!s}"
