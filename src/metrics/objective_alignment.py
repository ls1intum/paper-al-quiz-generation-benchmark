"""Learning-objective alignment metric.

Answers one question per item: how directly does this item assess the learning
objective stated for it? The objective is the reference value -- an item can be
well written, factually sound, and on-topic for the course and still fail here,
because the only thing being measured is whether it assesses *this* objective.

The judge picks one of four levels and the score follows from that level, so a
judge cannot label an item "direct" and then score it 40. Items with no stated
objective are reported as not applicable rather than guessed at.
"""

import json
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.quiz import QuizQuestion
from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput

# The four levels, best to worst, evenly spaced. There is deliberately no
# midpoint: "somewhere in the middle" is not a useful verdict about whether an
# item assesses an objective, and offering one is an invitation to pick it.
ALIGNMENT_SCORES = {
    "direct": 100.0,
    "partial": 66.7,
    "weak": 33.3,
    "none": 0.0,
}

# An item with no stated objective cannot be aligned or misaligned, so it is
# excluded rather than penalized. Scoring it 100 keeps it from dragging an
# unfiltered average down; `applicable` is the field that actually matters, and
# any analysis must filter on it before aggregating.
NOT_APPLICABLE_SCORE = 100.0


def get_learning_objective(question: QuizQuestion) -> Optional[str]:
    """Return the item's stated learning objective, or None when it has none.

    An absent key, an explicit null, and a whitespace-only string all mean the
    same thing here. This is the single place that decides whether an item is
    ratable, so the prompt and the scoring cannot disagree about it.
    """
    objective = question.metadata.get("learning_objective")
    if objective is None:
        return None
    objective = str(objective).strip()
    return objective or None


class ObjectiveAlignmentJudgeResponse(BaseModel):
    """The judge's verdict and its evidence. Deliberately carries no score.

    ``not_applicable`` is absent from the level choices on purpose: whether an
    item has a stated objective is a fact about the item, not a judgement call,
    so it is settled in ``_finalize`` and never delegated to a model.
    """

    model_config = ConfigDict(extra="forbid")

    alignment_level: Literal["direct", "partial", "weak", "none"]
    matched_objective_aspects: List[str] = Field(default_factory=list)
    missing_or_misaligned_aspects: List[str] = Field(default_factory=list)
    rationale: str


class ObjectiveAlignmentResponse(ObjectiveAlignmentJudgeResponse):
    """Final output: the judge's level, the objective it was judged against, and the score."""

    alignment_level: Literal["direct", "partial", "weak", "none", "not_applicable"]
    applicable: bool
    learning_objective: Optional[str] = None
    score: float = Field(ge=0, le=100)


class ObjectiveAlignmentMetric(BaseMetric):
    """Evaluates how directly each item assesses its stated learning objective.

    Two phases: an LLM judge, then a deterministic pass that derives the score
    from the judge's level and overrides the whole verdict for items that have
    no stated objective. The deterministic pass runs last because only the
    final phase's data reaches ``raw_response``.
    """

    @property
    def name(self) -> str:
        return "objective_alignment"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("judge", ObjectiveAlignmentJudgeResponse),
            Phase("finalize", ObjectiveAlignmentResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("objective_alignment judge phase requires a question")

        question = inp.question
        objective = get_learning_objective(question)
        if objective is None:
            # Nothing to judge against. The verdict is settled deterministically
            # in _finalize and this answer is discarded, so keep the call cheap.
            return """This item has no stated learning objective, so there is nothing to align it against.

Respond with ONLY this JSON object, exactly as written:
{
  "alignment_level": "none",
  "matched_objective_aspects": [],
  "missing_or_misaligned_aspects": [],
  "rationale": "No stated learning objective."
}"""

        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        context_lines = [
            f"{label}: {question.metadata[key]}"
            for key, label in (("topic", "Topic"), ("domain", "Domain"))
            if question.metadata.get(key)
        ]
        item_context = "\n".join(context_lines) if context_lines else "No additional context."

        source_context = (
            f"\n**Supporting Source Material**:\n{inp.source_text}\n"
            if inp.source_text
            else ""
        )

        return f"""Judge how directly the quiz item below assesses its stated learning objective.

**Stated Learning Objective** (the reference value -- judge against this and nothing else):
{objective}

**Item Context**:
{item_context}
{source_context}
**Item**:
Question Type: {question.question_type.value}
Stem: {question.question_text}
Options:
{options_text}
Marked Correct Answer: {question.correct_answer}

**How to decide**:
- The stated objective is the denominator. The topic, the source material, and general relevance to the course are context only. An item can be well written and on-topic and still not assess THIS objective.
- First work out which aspects of the objective the item actually assesses, and which parts of it the item leaves untested or tests in a different direction. Choose the level afterwards, from that evidence.
- Separate direct assessment from loose topical relatedness. An item that tests a prerequisite, recognition of the vocabulary, or an adjacent concept is related to the objective but does not assess it.

**Levels**:
- "direct": assesses the stated objective head-on, at the concept or skill level the objective describes.
- "partial": assesses part of the objective, or assesses it at a shallower level than stated.
- "weak": related only through a prerequisite, surface vocabulary, or a tangential concept.
- "none": does not assess the stated objective at all.

Respond with ONLY a JSON object matching this schema:
{{
  "alignment_level": "direct" | "partial" | "weak" | "none",
  "matched_objective_aspects": ["aspect of the objective the item assesses", ...],
  "missing_or_misaligned_aspects": ["aspect left untested or tested in a different direction", ...],
  "rationale": "<reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> Dict[str, Any]:
        """Derive the score from the judge's level, or mark the item not applicable."""
        if inp.question is None:
            raise ValueError("objective_alignment finalize phase requires a question")

        objective = get_learning_objective(inp.question)
        if objective is None:
            return {
                "alignment_level": "not_applicable",
                "applicable": False,
                "learning_objective": None,
                "matched_objective_aspects": [],
                "missing_or_misaligned_aspects": [],
                "rationale": "No learning objective is stated for this item.",
                "score": NOT_APPLICABLE_SCORE,
            }

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        level = judged["alignment_level"]

        return {
            "alignment_level": level,
            "applicable": True,
            "learning_objective": objective,
            "matched_objective_aspects": judged.get("matched_objective_aspects", []),
            "missing_or_misaligned_aspects": judged.get("missing_or_misaligned_aspects", []),
            "rationale": judged.get("rationale", ""),
            "score": ALIGNMENT_SCORES[level],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            level = data.get("alignment_level")
            if level is None:
                return None

            lines = [
                f"\n[Question ID: {quiz_id}] Learning-Objective Alignment:",
                "-" * 50,
            ]

            if not data.get("applicable", True):
                lines.append("Not applicable: no learning objective is stated for this item.")
                lines.append("-" * 50)
                return "\n".join(lines)

            lines.extend(
                [
                    f"Alignment:  {level}",
                    f"Score:      {data.get('score')}/100",
                    f"Objective:  {data.get('learning_objective')}",
                ]
            )

            matched = data.get("matched_objective_aspects", [])
            lines.append("Assessed aspects:" if matched else "Assessed aspects:  None")
            for aspect in matched:
                lines.append(f"  - {aspect}")

            missing = data.get("missing_or_misaligned_aspects", [])
            lines.append("Missing / misaligned:" if missing else "Missing / misaligned:  None")
            for aspect in missing:
                lines.append(f"  - {aspect}")

            lines.append(f"Rationale:  {data.get('rationale')}")
            lines.append("-" * 50)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse objective alignment insights: {str(e)}"
