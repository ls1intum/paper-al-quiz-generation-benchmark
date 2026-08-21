"""Cognitive-level alignment metric (C4).

Answers one question per item: does the item assess the Bloom taxonomy level
that the item metadata says it should? The intended level is the reference
value — an item can be well written and on-topic and still fail here, because
the only thing being measured is whether it tests at *this* cognitive level.

The judge assigns a Bloom level without seeing the intended level (to avoid
anchoring). The deterministic finalize phase compares the two. Items with no
stated intended level are reported as not applicable.
"""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.quiz import QuizQuestion
from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput

BLOOM_LEVELS = ("REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE")
BLOOM_RANK = {level: i for i, level in enumerate(BLOOM_LEVELS)}

MATCH_SCORES = {
    "below": 0.0,
    "matches": 100.0,
    "above": 66.7,
}

NOT_APPLICABLE_SCORE = 100.0


def get_bloom_intended(question: QuizQuestion) -> Optional[str]:
    """Return the item's stated intended Bloom level, or None when absent.

    An absent key, an explicit null, and a whitespace-only string all mean the
    same thing here. The value is normalized to upper case and validated against
    the six Bloom levels.
    """
    raw = question.metadata.get("bloom_intended")
    if raw is None:
        return None
    val = str(raw).strip().upper()
    if not val or val not in BLOOM_RANK:
        return None
    return val


class CognitiveLevelJudgeResponse(BaseModel):
    """The judge's Bloom-level assignment. Carries no score."""

    model_config = ConfigDict(extra="forbid")

    assigned_level: str
    rationale: str


class CognitiveLevelResponse(CognitiveLevelJudgeResponse):
    """Final output: assigned level, comparison with intended, and score."""

    bloom_intended: Optional[str] = None
    match: str
    applicable: bool
    score: float = Field(ge=0, le=100)


class CognitiveLevelMetric(BaseMetric):
    """Evaluates whether an item tests at the intended Bloom taxonomy level.

    Two phases: an LLM judge that assigns a level blind, then a deterministic
    pass that compares with the item's intended level and derives the score.
    """

    @property
    def name(self) -> str:
        return "cognitive_level"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("judge", CognitiveLevelJudgeResponse),
            Phase("finalize", CognitiveLevelResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("cognitive_level judge phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        return f"""Assign a Bloom's Taxonomy cognitive level to this quiz item.

**Item**:
Question Type: {question.question_type.value}
Stem: {question.question_text}
Options:
{options_text}
Marked Correct Answer: {question.correct_answer}

**Bloom's Taxonomy Levels** (pick exactly one):
- REMEMBER: Recall facts, terms, basic concepts, or definitions.
- UNDERSTAND: Explain ideas, interpret meaning, summarize, or classify.
- APPLY: Use information, methods, or concepts in a new situation.
- ANALYZE: Draw connections, compare, contrast, distinguish between parts.
- EVALUATE: Justify a decision, critique, assess, or judge value.
- CREATE: Produce new work, design solutions, synthesize, or construct.

**Guidelines**:
- Focus on what cognitive operation a student must perform to arrive at the
  correct answer, not on the surface difficulty of the vocabulary.
- If multiple levels apply, pick the highest level that is genuinely required
  (not merely helpful) to answer correctly.

Respond with ONLY a JSON object matching this schema:
{{
  "assigned_level": "REMEMBER" | "UNDERSTAND" | "APPLY" | "ANALYZE" | "EVALUATE" | "CREATE",
  "rationale": "<reasoning>"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> Dict[str, Any]:
        """Compare the judge's level with the intended level, or mark not applicable."""
        if inp.question is None:
            raise ValueError("cognitive_level finalize phase requires a question")

        intended = get_bloom_intended(inp.question)
        if intended is None:
            return {
                "assigned_level": "not_applicable",
                "bloom_intended": None,
                "match": "not_applicable",
                "applicable": False,
                "rationale": "No intended Bloom level is stated for this item.",
                "score": NOT_APPLICABLE_SCORE,
            }

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        assigned_raw = str(judged["assigned_level"]).strip().upper()
        # Fallback if LLM returns something unexpected
        assigned = assigned_raw if assigned_raw in BLOOM_RANK else "REMEMBER"

        assigned_rank = BLOOM_RANK[assigned]
        intended_rank = BLOOM_RANK[intended]

        if assigned_rank == intended_rank:
            match = "matches"
        elif assigned_rank < intended_rank:
            match = "below"
        else:
            match = "above"

        return {
            "assigned_level": assigned,
            "bloom_intended": intended,
            "match": match,
            "applicable": True,
            "rationale": judged.get("rationale", ""),
            "score": MATCH_SCORES[match],
        }
