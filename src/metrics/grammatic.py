"""Grammatical Correctness metric implementation."""

from typing import Callable, Dict, List
from ..models.quiz import Quiz
from .base import BaseMetric, MetricParameter, MetricScope, ScoreResponse
from .phase import Phase, PhaseInput


class GrammaticalCorrectnessMetric(BaseMetric):
    """Evaluates the grammatical correctness of a quiz.

    Uses a single-stage pipeline:
    1. score: scores grammar, spelling, punctuation, and sentence structure
       across all questions in the quiz.
    """

    @property
    def name(self) -> str:
        return "grammatical_correctness"

    @property
    def version(self) -> str:
        return "1.1"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def parameters(self) -> List[MetricParameter]:
        return [
            MetricParameter(
                name="error_weights",
                param_type=dict,
                default={"critical": 1.0, "major": 0.5, "minor": 0.2},
                description="Weights for different error severity levels",
            ),
            MetricParameter(
                name="language",
                param_type=str,
                default="en",
                description="Language for grammatical evaluation (affects error types checked)",
            ),
        ]

    @property
    def phases(self) -> List[Phase]:
        return [Phase("score", ScoreResponse)]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {
            "score": self._build_score_prompt,
        }
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    def _build_score_prompt(self, inp: PhaseInput) -> str:
        if inp.quiz is None:
            raise ValueError("grammatical_correctness score phase requires a quiz")

        error_weights: Dict = self.get_param_value("error_weights")
        language: str = self.get_param_value("language")
        quiz_content = self._format_quiz_for_prompt(inp.quiz)

        return f"""You are evaluating the grammatical correctness of quiz content.

Language: {language}

Error Severity Levels (for your reference):
- Critical (weight {error_weights['critical']}): Errors that make the text incomprehensible or change meaning
- Major (weight {error_weights['major']}): Clear grammatical errors that disrupt reading flow
- Minor (weight {error_weights['minor']}): Small issues like minor punctuation or capitalization

{quiz_content}

Provide a grammatical correctness score from 0 to 100, where:
- 0-20: Severe Issues (multiple major grammar errors, incomprehensible)
- 21-40: Significant Issues (several errors affecting clarity)
- 41-60: Moderate Issues (noticeable errors but understandable)
- 61-80: Minor Issues (few small errors, typos, or punctuation)
- 81-100: Excellent (no grammatical errors, professional quality)

Evaluate these aspects:

1. Grammar:
   - Subject-verb agreement
   - Proper tense usage
   - Correct article usage (a/an/the)
   - Pronoun agreement and clarity
   - Proper sentence structure

2. Spelling:
   - Correct spelling of all words
   - Proper capitalization
   - No typos or character errors

3. Punctuation:
   - Correct use of commas, periods, question marks
   - Proper use of apostrophes and quotation marks
   - Appropriate punctuation for lists

4. Sentence Structure:
   - Complete sentences (no fragments or run-ons)
   - Clear and logical structure
   - Parallel construction in lists

5. Technical Writing Standards:
   - Consistent formatting
   - Professional tone maintained
   - Appropriate technical terminology

Guidelines:
- Evaluate ALL parts: question text AND all answer options
- A single error in any option affects the score
- Technical terms should be spelled correctly
- Consider standard grammar rules
- Deduct points proportionally to severity and frequency

Respond with ONLY a JSON object in this format:
{{"score": <number between 0 and 100>}}"""

    @staticmethod
    def _format_quiz_for_prompt(quiz: Quiz) -> str:
        """Format quiz content into a structured string for the LLM prompt."""
        formatted = "--- CONTENT TO REVIEW START ---\n"
        formatted += f"CONTEXT: Quiz Title: {quiz.title}\n"

        if hasattr(quiz, "metadata") and quiz.metadata:
            audience = quiz.metadata.get("target_audience", "General")
            formatted += f"CONTEXT: Target Audience: {audience}\n"
            if "learning_objectives" in quiz.metadata:
                objs = quiz.metadata["learning_objectives"]
                formatted += f"CONTEXT: Learning Objectives: {', '.join(objs)}\n"

        formatted += "\n" + "=" * 40 + "\n\n"

        for idx, question in enumerate(quiz.questions, 1):
            formatted += f"### ITEM {idx} (ID: {question.question_id})\n"
            formatted += f"**Question Text:**\n{question.question_text}\n\n"
            formatted += "**Options:**\n"
            for opt_idx, option in enumerate(question.options, 1):
                formatted += f"  {opt_idx}. {option}\n"

            formatted += "\n**Correct Answer(s):** "
            if isinstance(question.correct_answer, list):
                formatted += ", ".join(question.correct_answer)
            else:
                formatted += str(question.correct_answer)
            formatted += "\n"

            if hasattr(question, "source_reference") and question.source_reference:
                formatted += f"**Reference:** {question.source_reference}\n"

            if hasattr(question, "metadata") and question.metadata:
                formatted += "**Metadata Tags:** "
                tags = [f"{k}={v}" for k, v in question.metadata.items()]
                formatted += ", ".join(tags) + "\n"

            formatted += "_" * 40 + "\n\n"

        formatted += "--- CONTENT TO REVIEW END ---"
        return formatted
