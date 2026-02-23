"""Coverage metric implementation."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from .base import BaseMetric, MetricParameter, MetricScope
from .phase import Phase, PhaseInput, PhaseOutput


class SubScores(BaseModel):
    breadth: float = Field(ge=0, le=100)
    depth: float = Field(ge=0, le=100)
    balance: float = Field(ge=0, le=100)
    critical: float = Field(ge=0, le=100)


class CoverageMetric(BaseMetric):
    """Evaluates how well the quiz covers the source material.

    Uses a 3-stage pipeline:
    1. TopicExtractionPhase: extract high-level topics from the source material.
    2. PerQuestionTopicMappingPhase: map each question to known source topics (fan-out).
    3. CoverageScoringPhase: score breadth, depth, balance, and critical coverage.
    """

    class SourceTopicsResponse(BaseModel):
        topics: List[str] = Field(default_factory=list)

    class QuestionSummaryResponse(BaseModel):
        topics: List[str] = Field(default_factory=list)
        cognitive_level: str
        reasoning: str

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

    class TopicExtractionPhase(Phase):
        """Stage 1: Extract high-level topics from the source material.

        Produces a shared topic list that the per-question mapping phase
        uses to anchor question analysis to known source topics.

        Requires:
            phase_input.source_text: Raw source material.

        Produces:
            SourceTopicsResponse: {"topics": ["topic1", "topic2", ...]}
        """

        def build_prompt(self, phase_input: PhaseInput) -> str:
            if not phase_input.source_text:
                raise ValueError("TopicExtractionPhase requires source_text")

            return f"""Analyze the source material and identify its main topics.

**Source Material**:
{phase_input.source_text}

List 5-15 HIGH-LEVEL topics. Group related concepts together.

Respond with ONLY a JSON object."""

    class PerQuestionTopicMappingPhase(Phase):
        """Stage 2: Map each question to topics from the source material.

        Fan-out phase — one LLM call per question. Uses the topic list
        produced by TopicExtractionPhase to ground the analysis.

        Requires:
            phase_input.question: The question being analysed.
            phase_input.accumulated["topic_extraction"]: Output from stage 1.

        Produces:
            QuestionSummaryResponse per question:
            {"topics": [...], "cognitive_level": "...", "reasoning": "..."}
        """

        def build_prompt(self, phase_input: PhaseInput) -> str:
            if phase_input.question is None:
                raise ValueError("PerQuestionTopicMappingPhase requires a question")

            topic_extraction = phase_input.accumulated.get("topic_extraction")
            source_topics = topic_extraction.data.get("topics", []) if topic_extraction else []
            topics_hint = (
                f"\n**Known topics in source**: {', '.join(source_topics)}\n"
                "Map this question to topics from this list where possible."
                if source_topics
                else ""
            )

            q = phase_input.question
            return f"""Analyze what topics this quiz question tests.
{topics_hint}

**Question #{q.question_id}**:
Type: {q.question_type.value}
Text: {q.question_text}
Options: {q.options if q.options else 'N/A'}
Correct Answer: {q.correct_answer}

**Task**: Identify the specific topics/concepts this question tests.

Respond with ONLY a JSON object:
{{
    "topics": ["topic1", "topic2", ...],
    "cognitive_level": "recall|understanding|application",
    "reasoning": "Brief explanation of what the question tests"
}}"""

    class CoverageScoringPhase(Phase):
        """Stage 3: Score the quiz's overall coverage of the source material.

        Combines the per-question topic summaries from stage 2 with the full
        source material to produce four sub-scores (breadth, depth, balance,
        critical coverage) whose weights are controlled by the granularity param.

        Requires:
            phase_input.quiz: The full quiz.
            phase_input.source_text: Raw source material.
            phase_input.accumulated["per_question_mapping"]: Fan-out results from stage 2.

        Produces:
            OverallCoverageResponse with sub_scores and final_score.
        """

        def __init__(self, granularity: str = "balanced", **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.granularity = granularity

        def _get_weights(self) -> Dict[str, int]:
            if self.granularity == "broad":
                return {"breadth": 40, "depth": 20, "balance": 20, "critical": 20}
            elif self.granularity == "detailed":
                return {"breadth": 20, "depth": 40, "balance": 20, "critical": 20}
            else:  # balanced
                return {"breadth": 30, "depth": 30, "balance": 20, "critical": 20}

        def build_prompt(self, phase_input: PhaseInput) -> str:
            if phase_input.quiz is None:
                raise ValueError("CoverageScoringPhase requires a quiz")
            if not phase_input.source_text:
                raise ValueError("CoverageScoringPhase requires source_text")

            per_question_output = phase_input.accumulated.get("per_question_mapping")
            per_question_results = (
                per_question_output.data.get("results", []) if per_question_output else []
            )
            if not per_question_results:
                raise ValueError("CoverageScoringPhase requires per_question_mapping results")

            weights = self._get_weights()
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
{phase_input.source_text}

**Quiz Overview**:
Title: {phase_input.quiz.title}
Total Questions: {phase_input.quiz.num_questions}

**Topics Tested by Each Question**:
{summaries_text}

**Scoring Framework (Granularity: {self.granularity})**:

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

    @property
    def name(self) -> str:
        return "coverage"

    @property
    def version(self) -> str:
        return "1.3"

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

    @property
    def phases(self) -> List[Phase]:
        """Three-stage coverage evaluation pipeline.

        Returns:
            [TopicExtractionPhase, PerQuestionTopicMappingPhase, CoverageScoringPhase]
        """
        granularity = self.get_param_value("granularity")
        return [
            self.TopicExtractionPhase(
                name="topic_extraction",
                output_schema=self.SourceTopicsResponse,
            ),
            self.PerQuestionTopicMappingPhase(
                name="per_question_mapping",
                output_schema=self.QuestionSummaryResponse,
                fan_out=True,
            ),
            self.CoverageScoringPhase(
                name="coverage_scoring",
                output_schema=self.OverallCoverageResponse,
                granularity=granularity,
            ),
        ]

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract final_score from the coverage scoring phase output.

        Args:
            final_output: PhaseOutput from CoverageScoringPhase.

        Returns:
            Rounded float score between 0 and 100.

        Raises:
            ValueError: If final_score is missing or out of range.
        """
        try:
            score = float(final_output.data["final_score"])
        except KeyError:
            raise ValueError(
                f"Coverage parsing failed. Expected 'final_score', "
                f"but got keys: {list(final_output.data.keys())}"
            )
        except (ValueError, TypeError):
            raise ValueError(
                f"Could not convert final_score to float. Got: {final_output.data.get('final_score')}"
            )

        if not 0 <= score <= 100:
            raise ValueError(f"Coverage score must be between 0 and 100, got {score}")

        return round(score, 1)
