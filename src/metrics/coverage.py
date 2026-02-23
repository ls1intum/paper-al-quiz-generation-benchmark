"""Coverage metric implementation."""

from typing import Any, Dict, List, Type, Optional

from pydantic import BaseModel, Field

from ..models.quiz import QuizQuestion, Quiz
from .base import BaseMetric, MetricParameter, MetricScope


class CoverageMetric(BaseMetric):
    """Evaluates how well the quiz covers the source material.

    This metric uses a two-stage approach:
    1. Extract topics from each question individually
    2. Analyze overall coverage based on all extracted topics
    """

    @property
    def name(self) -> str:
        return "coverage"

    @property
    def version(self) -> str:
        return "1.2"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def parameters(self) -> List[MetricParameter]:
        return [
            MetricParameter(
                name="granularity",
                param_type=str,
                default="balanced",
                description="Coverage granularity (detailed, balanced, broad)",
            ),
        ]

    @staticmethod
    def _get_weights(granularity: str) -> Dict[str, int]:
        """Return weight distribution for the four sub-scores."""
        if granularity == "broad":
            return {"breadth": 40, "depth": 20, "balance": 20, "critical": 20}
        elif granularity == "detailed":
            return {"breadth": 20, "depth": 40, "balance": 20, "critical": 20}
        else:  # balanced
            return {"breadth": 30, "depth": 30, "balance": 20, "critical": 20}

    class SourceTopicsResponse(BaseModel):
        topics: List[str] = Field(default_factory=list)

    def generate_context(self, source_text: Optional[str], llm_client: Any) -> Dict[str, Any]:
        """Stage 1: Extract topics before per-question fan-out."""
        if not source_text:
            return {}

        prompt = f"""Analyze the source material and identify its main topics.

    **Source Material**:
    {source_text}

    List 5-15 HIGH-LEVEL topics. Group related concepts together.

    Respond with ONLY a JSON object."""

        [source_topics] = self.run_stage([prompt], self.SourceTopicsResponse, llm_client)
        return {"source_topics": source_topics}

    def get_per_question_prompt(
        self,
        question: QuizQuestion,
        source_text: str,
        context: Dict[str, Any],
    ) -> str:
        """Generate prompt for stage 2: extract topics from a single question."""
        source_topics = context.get("source_topics", {})
        topics_hint = ""

        if source_topics and "topics" in source_topics:
            topics_hint = f"\n**Known topics in source**: {', '.join(source_topics['topics'])}\nMap this question to topics from this list where possible."
        return f"""Analyze what topics this quiz question tests.
    
    **Topics**:
    {topics_hint}
    
    **Question #{question.question_id}**:
    Type: {question.question_type.value}
    Text: {question.question_text}
    Options: {question.options if question.options else 'N/A'}
    Correct Answer: {question.correct_answer}
    
     **Task**: Identify the specific topics/concepts this question tests.
    
    **Required JSON Format**:
    ```json
    {{
        "topics": ["topic1", "topic2", ...],
        "cognitive_level": "recall|understanding|application",
        "reasoning": "Brief explanation of what the question tests"
    }}
    ```
    
    Respond with ONLY the JSON object."""

    class QuestionSummaryResponse(BaseModel):
        topics: List[str] = Field(default_factory=list)
        cognitive_level: str
        reasoning: str

    def get_per_question_schema(self) -> Type[BaseModel]:
        return self.QuestionSummaryResponse

    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        per_question_results: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        **params: Any,
    ) -> str:
        """Generate prompt for stage 3: final coverage scoring."""
        granularity = self.get_param_value("granularity", **params)
        weights = self._get_weights(granularity)

        if not per_question_results:
            raise ValueError("CoverageMetric requires per_question_results")

        if quiz is None:
            raise ValueError("CoverageMetric requires a quiz")

        summaries_text = "\n".join(
            f"Q{i} [{r.get('cognitive_level', 'unknown')}]: {', '.join(r.get('topics', []))}"
            for i, r in enumerate(per_question_results, 1)
        )

        return f"""You are an expert quiz evaluator. Assess how well this quiz covers the source material.

    **Calibration Guidelines**:
    - Most good quizzes score 55-75 (this is NORMAL and EXPECTED)
    - 75-85 = very good coverage
    - 85-100 = exceptional, comprehensive coverage (rare)
    - 40-55 = adequate but with gaps
    - Below 40 = significant problems

    **Source Material**:
    {source_text}

    **Quiz Overview**:
    Title: {quiz.title}
    Total Questions: {quiz.num_questions}

    **Topics Tested by Each Question**:
    {summaries_text}

    **Scoring Framework (Granularity: {granularity})**:

    1. **Breadth** (max {weights['breadth']} pts):
       - List ALL distinct topics in the source material
       - Count how many are tested by ≥1 question
       - Score = (topics_covered / topics_total) × {weights['breadth']}

    2. **Depth** (max {weights['depth']} pts):
       - For each covered topic, note its cognitive level (recall=1, understanding=2, application=3)
       - Calculate average cognitive level across all covered topics
       - Score = (avg_level / 3.0) × {weights['depth']}

    3. **Balance** (max {weights['balance']} pts):
       - Are important topics given appropriate question weight?
       - Are minor details over-represented?
       - Score subjectively 0-{weights['balance']}

    4. **Critical Coverage** (max {weights['critical']} pts):
       - Identify 3-5 essential "must-know" concepts from the source
       - Count how many are tested
       - Score = (critical_covered / critical_total) × {weights['critical']}
       
    **CRITICAL CONSTRAINT:** Keep all "reasoning" fields extremely concise (1-2 sentences maximum).

    Respond with ONLY this JSON object:
    {{
      "topics_in_source": ["topic1", "topic2", ...],
      "topics_covered": ["topic1", ...],
      "critical_concepts": ["concept1", ...],
      "critical_covered": ["concept1", ...],
      "breadth_reasoning": "step by step breadth calculation",
      "depth_reasoning": "step by step depth calculation",
      "balance_reasoning": "explanation of balance score",
      "critical_reasoning": "step by step critical coverage calculation",
      "sub_scores": {{
        "breadth": <0-{weights['breadth']}>,
        "depth": <0-{weights['depth']}>,
        "balance": <0-{weights['balance']}>,
        "critical": <0-{weights['critical']}>
      }},
      "final_score": <sum of sub_scores>
    }}"""

    def get_response_schema(self, **kwargs: Any) -> Type[BaseModel]:
        return OverallCoverageResponse

    def parse_structured_response(self, response: Dict[str, Any]) -> float:
        """Extract the final score specifically from the coverage payload."""
        try:
            # We explicitly ask for final_score, ignoring the sub_scores
            raw_score = response["final_score"]
            score = float(raw_score)
        except KeyError:
            raise ValueError(
                f"Coverage parsing failed. Expected 'final_score', "
                f"but got keys: {list(response.keys())}"
            )
        except (ValueError, TypeError):
            raise ValueError(
                f"Could not convert final_score to float. Got: {response.get('final_score')}"
            )

        if not 0 <= score <= 100:
            raise ValueError(f"Coverage score must be between 0 and 100, got {score}")

        return round(score, 1)


class SubScores(BaseModel):
    breadth: float = Field(ge=0, le=100)
    depth: float = Field(ge=0, le=100)
    balance: float = Field(ge=0, le=100)
    critical: float = Field(ge=0, le=100)


class OverallCoverageResponse(BaseModel):
    topics_in_source: List[str] = Field(default_factory=list)
    topics_covered: List[str] = Field(default_factory=list)
    critical_concepts: List[str] = Field(default_factory=list)
    critical_covered: List[str] = Field(default_factory=list)
    breadth_reasoning: str
    depth_reasoning: str
    balance_reasoning: str
    critical_reasoning: str
    sub_scores: SubScores
    final_score: float = Field(ge=0, le=100)
