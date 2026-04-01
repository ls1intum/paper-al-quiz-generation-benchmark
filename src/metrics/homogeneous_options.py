"""Homogeneous options metric implementation."""

from statistics import median
from typing import Callable, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput, PhaseOutput


class OptionAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_text: str
    grammatical_form: str
    content_type: str
    is_complete_sentence: bool
    contains_code: bool
    contains_numeric_expression: bool
    length_bucket: str
    reasoning: str


class AnalyzeOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    applicable: bool
    exclusion_reason: Optional[str] = None
    option_analyses: List[OptionAnalysis] = Field(default_factory=list)
    dominant_grammatical_pattern: str = ""
    dominant_content_type: str = ""
    structural_outliers: List[str] = Field(default_factory=list)


class QuestionHomogeneityScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    applicable: bool
    grammatical_parallelism_score: float = Field(ge=0, le=100)
    content_type_homogeneity_score: float = Field(ge=0, le=100)
    format_consistency_score: float = Field(ge=0, le=100)
    question_score: float = Field(ge=0, le=100)
    severity: str
    issues: List[str] = Field(default_factory=list)
    rationale: str


class IssueCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue: str
    count: int = Field(ge=1)


class QuestionScoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    applicable: bool
    score: float = Field(ge=0, le=100)
    severity: str


class AggregateHomogeneityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    num_questions_total: int = Field(ge=0)
    num_questions_applicable: int = Field(ge=0)
    num_excluded: int = Field(ge=0)
    mean_question_score: float = Field(ge=0, le=100)
    median_question_score: float = Field(ge=0, le=100)
    major_violation_rate: float = Field(ge=0, le=1)
    perfect_homogeneity_rate: float = Field(ge=0, le=1)
    issue_distribution: List[IssueCount] = Field(default_factory=list)
    question_scores: List[QuestionScoreSummary] = Field(default_factory=list)
    aggregation_reasoning: str
    score: float = Field(ge=0, le=100)


class HomogeneousOptionsMetric(BaseMetric):
    """Evaluates whether answer choices are parallel and homogeneous."""

    @property
    def name(self) -> str:
        return "homogeneous_options"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def phases(self) -> List[Phase]:
        return [
            Phase("analyze_options", AnalyzeOptionsResponse, fan_out=True),
            Phase("score_question", QuestionHomogeneityScoreResponse, fan_out=True),
            Phase("aggregate", AggregateHomogeneityResponse, processor=self._aggregate_results),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {
            "analyze_options": self._build_analyze_options_prompt,
            "score_question": self._build_score_question_prompt,
        }
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    def _build_analyze_options_prompt(self, inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("analyze_options phase requires a question")

        question = inp.question
        options_text = "\n".join(f"{i}. {option}" for i, option in enumerate(question.options, 1))

        return f"""Analyze whether this question's answer options are homogeneous.

Question ID: {question.question_id}
Question Type: {question.question_type.value}
Question: {question.question_text}

Options:
{options_text}

Task:
1. Decide whether this question is applicable for homogeneous-options evaluation.
2. For each option, classify its grammatical form and content type.
3. Identify the dominant grammatical pattern and dominant content type.
4. Identify any structural outliers.
5. Do NOT score the question yet.

Applicability guidance:
- Mark true/false questions as not applicable.
- Mark malformed option sets as not applicable only if the options are too incomplete to classify.
- Otherwise, analyze the options even if they are heterogeneous.

Grammatical form examples: noun_phrase, verb_phrase, full_sentence, clause, code_fragment,
numeric_expression, list_item.
Content type examples: concept_term, definition, explanation, example, code_snippet,
code_output, numeric_value, boolean_statement, procedure_step.
Length bucket examples: very_short, short, medium, long.

Respond with ONLY a JSON object in this format:
{{
  "question_id": "{question.question_id}",
  "applicable": true,
  "exclusion_reason": null,
  "option_analyses": [
    {{
      "option_text": "option text",
      "grammatical_form": "noun_phrase",
      "content_type": "concept_term",
      "is_complete_sentence": false,
      "contains_code": false,
      "contains_numeric_expression": false,
      "length_bucket": "short",
      "reasoning": "brief explanation"
    }}
  ],
  "dominant_grammatical_pattern": "noun_phrase",
  "dominant_content_type": "concept_term",
  "structural_outliers": ["option 3 is a full sentence while others are noun phrases"]
}}"""

    def _build_score_question_prompt(self, inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("score_question phase requires a question")

        analysis = self._get_question_result(
            inp.accumulated.get("analyze_options"), inp.question.question_id
        )
        if analysis is None:
            raise ValueError("score_question phase requires output from analyze_options phase")

        return f"""Score the homogeneity of this question's answer options using the structured analysis.

Question ID: {inp.question.question_id}
Question Type: {inp.question.question_type.value}
Question: {inp.question.question_text}

Structured Analysis:
{analysis}

Scoring rubric:
- grammatical_parallelism_score: Are all options parallel in grammatical form?
- content_type_homogeneity_score: Are all options the same kind of thing?
- format_consistency_score: Are there avoidable formatting, punctuation, or length inconsistencies?

Weighting:
question_score = 0.45 * grammatical_parallelism_score
               + 0.45 * content_type_homogeneity_score
               + 0.10 * format_consistency_score

Severity:
- none: question_score >= 85
- minor: 60 <= question_score < 85
- major: question_score < 60

Issue labels should be short machine-readable strings such as:
mixed_sentence_and_phrase, mixed_code_and_prose, mixed_definition_and_example,
mixed_numeric_and_textual, length_outlier, punctuation_outlier, not_applicable.

If the question is not applicable, return applicable=false, set all sub-scores and question_score to 100,
severity to "none", and include "not_applicable" in issues.

Respond with ONLY a JSON object in this format:
{{
  "question_id": "{inp.question.question_id}",
  "applicable": true,
  "grammatical_parallelism_score": 90,
  "content_type_homogeneity_score": 85,
  "format_consistency_score": 95,
  "question_score": 89.0,
  "severity": "none",
  "issues": ["length_outlier"],
  "rationale": "brief explanation"
}}"""

    def _aggregate_results(self, inp: PhaseInput) -> dict[str, object]:
        if inp.quiz is None:
            raise ValueError("aggregate phase requires a quiz")

        scoring_output = inp.accumulated.get("score_question")
        if scoring_output is None:
            raise ValueError("aggregate phase requires output from score_question phase")

        results = scoring_output.data.get("results", [])
        if not results:
            raise ValueError("aggregate phase requires output from score_question phase")

        total_questions = inp.quiz.num_questions
        applicable_results = [r for r in results if r.get("applicable")]
        applicable_scores = [float(r["question_score"]) for r in applicable_results]

        num_applicable = len(applicable_results)
        num_excluded = total_questions - num_applicable
        mean_question_score = (
            sum(applicable_scores) / num_applicable if applicable_scores else 100.0
        )
        median_question_score = median(applicable_scores) if applicable_scores else 100.0
        major_violation_rate = (
            sum(1 for r in applicable_results if r.get("severity") == "major") / num_applicable
            if applicable_results
            else 0.0
        )
        perfect_homogeneity_rate = (
            sum(1 for r in applicable_results if float(r.get("question_score", 0)) >= 95)
            / num_applicable
            if applicable_results
            else 0.0
        )
        issue_distribution: dict[str, int] = {}
        for result in applicable_results:
            for issue in result.get("issues", []):
                issue_distribution[issue] = issue_distribution.get(issue, 0) + 1

        question_scores = [
            QuestionScoreSummary(
                question_id=r.get("question_id"),
                applicable=bool(r.get("applicable")),
                score=float(r.get("question_score", 100)),
                severity=str(r.get("severity")),
            ).model_dump()
            for r in results
        ]
        issue_distribution_items = [
            IssueCount(issue=issue, count=count).model_dump()
            for issue, count in sorted(issue_distribution.items())
        ]

        penalty = min(15.0, 20.0 * major_violation_rate)
        computed_score = max(0.0, min(100.0, mean_question_score - penalty))

        aggregation_reasoning = (
            f"Aggregated {num_applicable} applicable questions out of {total_questions}; "
            f"mean question score {mean_question_score:.2f}, "
            f"major violation rate {major_violation_rate:.2%}, "
            f"penalty {penalty:.2f}."
        )

        return {
            "num_questions_total": total_questions,
            "num_questions_applicable": num_applicable,
            "num_excluded": num_excluded,
            "mean_question_score": round(mean_question_score, 2),
            "median_question_score": round(median_question_score, 2),
            "major_violation_rate": round(major_violation_rate, 4),
            "perfect_homogeneity_rate": round(perfect_homogeneity_rate, 4),
            "issue_distribution": issue_distribution_items,
            "question_scores": question_scores,
            "aggregation_reasoning": aggregation_reasoning,
            "score": round(computed_score, 2),
        }

    @staticmethod
    def _get_question_result(
        phase_output: Optional[PhaseOutput], question_id: str
    ) -> Optional[dict[str, object]]:
        if phase_output is None:
            return None

        for result in phase_output.data.get("results", []):
            if isinstance(result, dict) and result.get("question_id") == question_id:
                return dict(result)

        return None
