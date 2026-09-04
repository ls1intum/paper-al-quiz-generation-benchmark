"""Difficulty spread metric (quiz-level).

Answers one question per quiz: does the quiz mix difficulty sensibly, or is it
uniformly trivial or uniformly hard? A quiz whose items all sit at one level
separates nobody -- every learner either clears all of it or none of it -- and
that is a property of the set, not of any item in it.

Two things this criterion deliberately does not measure. It does not judge the
ORDER items appear in: a quiz that opens with its hardest item is badly
arranged, not badly spread. And it is not a Bloom-level judgement; cognitive
level is assessed per item by `cognitive_level`, against a catalogue reference
value, while difficulty here is the effort the item demands of a learner who
has studied the material.

The verdict is holistic and reached in one call, which is what the human rater
does with the same quiz. Deriving it instead from per-item difficulty labels
would be more reproducible and would measure something else -- a computed
statistic over a scale that has no reference value -- and the two arms would no
longer be answering the same question.
"""

import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput
from .quiz_level import MIN_QUIZ_ITEMS, NOT_APPLICABLE_SCORE, render_items, verdict_scores

# Best to worst. "varied" is a genuine mix from straightforward to demanding;
# "uniform" is a quiz that discriminates nothing, whether because everything is
# trivial or because everything is hard.
SPREAD_SCORES = verdict_scores(("varied", "mostly_uniform", "nearly_uniform", "uniform"))

SpreadLevel = Literal["varied", "mostly_uniform", "nearly_uniform", "uniform", "not_applicable"]


class DifficultySpreadJudgeResponse(BaseModel):
    """The judge's verdict and its evidence. Deliberately carries no score.

    The two extremes come before the verdict: naming the easiest and hardest
    item is how the judge shows it located a range, and a spread verdict given
    without one is unevidenced.
    """

    model_config = ConfigDict(extra="forbid")

    easiest_question_id: str
    hardest_question_id: str
    rationale: str
    spread_level: Literal["varied", "mostly_uniform", "nearly_uniform", "uniform"]


class DifficultySpreadResponse(DifficultySpreadJudgeResponse):
    """Final output: the judge's level, its evidence, and the score."""

    easiest_question_id: str | None = None  # type: ignore[assignment]
    hardest_question_id: str | None = None  # type: ignore[assignment]
    spread_level: SpreadLevel  # type: ignore[assignment]
    applicable: bool
    num_questions: int
    score: float = Field(ge=0, le=100)


class DifficultySpreadMetric(BaseMetric):
    """Evaluates whether a quiz's items vary in difficulty rather than clustering at one level.

    Two phases: an LLM judge over the whole quiz, then a deterministic pass that
    derives the score from the judge's level and overrides the verdict for
    quizzes too short to have a spread. The deterministic pass runs last because
    only the final phase's data reaches ``raw_response``.
    """

    @property
    def name(self) -> str:
        return "difficulty_spread"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def phases(self) -> list[Phase]:
        return [
            Phase("judge", DifficultySpreadJudgeResponse),
            Phase("finalize", DifficultySpreadResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.quiz is None:
            raise ValueError("difficulty_spread judge phase requires a quiz")

        if inp.quiz.num_questions < MIN_QUIZ_ITEMS:
            # Too few items to have a spread. The verdict is settled
            # deterministically in _finalize and this answer is discarded, so
            # keep the call cheap.
            return f"""This quiz holds fewer than {MIN_QUIZ_ITEMS} items, so it has no difficulty spread to judge.

Respond with ONLY this JSON object, exactly as written:
{{
  "easiest_question_id": "",
  "hardest_question_id": "",
  "rationale": "Too few items to have a difficulty spread.",
  "spread_level": "varied"
}}"""

        return f"""Judge whether the quiz below mixes difficulty sensibly across its items.

**Quiz Items** ({inp.quiz.num_questions} in total):
{render_items(inp.quiz)}

**How to decide**:
- First locate the range: name the item that demands least of a learner who has studied the material, and the one that demands most. Choose the level afterwards, from that range and how the remaining items sit inside it.
- Difficulty is the effort the item demands of a prepared learner: how much has to be recalled, worked out, or ruled out before the key can be picked. Plausible distractors make an item harder; an obvious key makes it easier.
- Judge the SPREAD only. The order the items appear in is not being assessed -- a demanding item placed first is not a spread problem.
- This is NOT a judgement of cognitive level or Bloom taxonomy. Two items at the same Bloom level can differ sharply in difficulty, and a quiz spread across Bloom levels can still be uniformly easy.
- A quiz that is uniformly hard scores no better than one that is uniformly trivial. Both fail to separate a strong learner from a weak one.

**Levels**:
- "varied": a sensible mix, from straightforward to demanding.
- "mostly_uniform": mostly at one level, with some variation.
- "nearly_uniform": nearly all at one level; little to distinguish strong learners from weak ones.
- "uniform": entirely trivial or entirely hard; the quiz discriminates nothing.

Respond with ONLY a JSON object matching this schema:
{{
  "easiest_question_id": "<id of the least demanding item>",
  "hardest_question_id": "<id of the most demanding item>",
  "rationale": "<reasoning>",
  "spread_level": "varied" | "mostly_uniform" | "nearly_uniform" | "uniform"
}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> dict[str, Any]:
        """Derive the score from the judge's level, or mark the quiz not applicable."""
        if inp.quiz is None:
            raise ValueError("difficulty_spread finalize phase requires a quiz")

        num_questions = inp.quiz.num_questions
        if num_questions < MIN_QUIZ_ITEMS:
            return {
                "spread_level": "not_applicable",
                "applicable": False,
                "num_questions": num_questions,
                "easiest_question_id": None,
                "hardest_question_id": None,
                "rationale": (
                    f"A quiz of {num_questions} item(s) has no difficulty spread to judge; "
                    f"{MIN_QUIZ_ITEMS} are required."
                ),
                "score": NOT_APPLICABLE_SCORE,
            }

        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        level = judged["spread_level"]

        # An id the quiz does not contain is not evidence. Drop it rather than
        # letting a hallucinated item travel into the analysis as the extreme
        # the verdict was supposedly read off.
        known_ids = {question.question_id for question in inp.quiz.questions}

        def known(question_id: Any) -> str | None:
            return question_id if question_id in known_ids else None

        return {
            "spread_level": level,
            "applicable": True,
            "num_questions": num_questions,
            "easiest_question_id": known(judged.get("easiest_question_id")),
            "hardest_question_id": known(judged.get("hardest_question_id")),
            "rationale": judged.get("rationale", ""),
            "score": SPREAD_SCORES[level],
        }

    def format_insights(self, raw_response: str, quiz_id: str) -> str | None:
        """Extract qualitative insights from the metric's raw response for display."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            level = data.get("spread_level")
            if level is None:
                return None

            lines = [
                f"\n[Quiz ID: {quiz_id}] Difficulty Spread:",
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
                    f"Spread:     {level}",
                    f"Score:      {data.get('score')}/100",
                    f"Easiest:    {data.get('easiest_question_id')}",
                    f"Hardest:    {data.get('hardest_question_id')}",
                    f"Rationale:  {data.get('rationale')}",
                    "-" * 50,
                ]
            )
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"Could not parse difficulty spread insights: {e!s}"
