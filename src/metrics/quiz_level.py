"""Shared pieces for the quiz-level criteria.

Three metrics -- ``objective_balance``, ``difficulty_spread`` and
``cross_item_redundancy`` -- judge a property of a quiz that is invisible when
its items are read one at a time. They share a shape: the whole quiz goes into
one judge prompt, the judge returns evidence and a four-level verdict, and a
deterministic pass turns that verdict into a score.

The four score levels live here rather than in each metric because the analysis
side reads them back as an ordinal 1-4 rating and compares them against a human
rater's. A metric that emitted 75.0 instead of 66.7 would land between two
levels and be silently rounded into the wrong one.
"""

from ..models.quiz import Quiz

# Four evenly spaced levels, best to worst, with no midpoint -- the same scale
# the human raters use. "Somewhere in the middle" is not a useful verdict about
# a quiz, and offering it as an option is an invitation to pick it.
ORDINAL_LEVEL_SCORES = (100.0, 66.7, 33.3, 0.0)

# A quiz-level property that cannot be judged is excluded rather than penalized.
# Scoring it 100 keeps it from dragging an unfiltered average down; `applicable`
# is the field that matters, and any analysis must filter on it before
# aggregating (see `_METRICS_WITH_APPLICABLE` in src/analysis/aggregator.py).
NOT_APPLICABLE_SCORE = 100.0

# Difficulty spread and cross-item redundancy have nothing to measure on a
# one- or two-item quiz: there is no spread in a pair and barely a pair to be
# redundant. Three is the floor the human study uses too, but as a SELECTION
# rule -- quizzes below it never reach a rater, and the rating form offers no
# abstention. So this is not a symmetric abstention: it is the judge declining
# to score a unit no rater would ever have been shown.
MIN_QUIZ_ITEMS = 3


def verdict_scores(best_to_worst: tuple[str, str, str, str]) -> dict[str, float]:
    """Map a metric's four verdicts, best first, onto the shared score levels."""
    return dict(zip(best_to_worst, ORDINAL_LEVEL_SCORES, strict=True))


def render_items(quiz: Quiz) -> str:
    """Render every item of the quiz for a judge prompt.

    Item ids are included because two of the three criteria have to point back
    at individual items -- naming a redundant pair, naming the hardest item --
    and a judge that never sees an id can only answer by position.
    """
    blocks = []
    for position, question in enumerate(quiz.questions, 1):
        options = "\n".join(f"  {i}. {option}" for i, option in enumerate(question.options, 1))
        blocks.append(
            f"Item {position} (id: {question.question_id}, "
            f"type: {question.question_type.value})\n"
            f"Stem: {question.question_text}\n"
            f"Options:\n{options}\n"
            f"Marked correct answer: {question.correct_answer}"
        )
    return "\n\n".join(blocks)


def declared_objectives(quiz: Quiz) -> list[str]:
    """Return the objectives the quiz declares for itself, or an empty list.

    Note the singular/plural split: ``quiz.metadata["learning_objectives"]`` is
    the set the quiz claims to cover, while ``question.metadata["learning_objective"]``
    is one item's reference value and belongs to `objective_alignment`.
    """
    raw = quiz.metadata.get("learning_objectives") or []
    if isinstance(raw, str):
        raw = [raw]
    return [text for text in (str(item).strip() for item in raw) if text]
