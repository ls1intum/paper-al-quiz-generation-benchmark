"""Coverage metric implementation."""

import json
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
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
    1. extract: Extract high-level topics AND critical concepts from the source.
    2. map: Map each question to source topics and assign a numeric cognitive level (fan-out).
    3. score: Score breadth, depth, balance, and critical coverage.

    Instructions integration:
    - num_questions: replaces the default ideal_questions calculation in the balance
      sub-score. If the user requested 10 questions and the quiz has 4, the shortfall
      is penalised proportionally.
    - custom_prompt: handled entirely in BaseMetric.evaluate() as a post-processing
      adjustment — coverage itself has no knowledge of it.

    Key design decisions:
    - Critical concepts are identified once from the source in stage 1, not re-invented
      per quiz in stage 3. This prevents the LLM from cherry-picking easy concepts.
    - Cognitive level is a numeric 1-3 in addition to a label, preventing clustering
      at "understanding" and spreading depth scores appropriately.
    - Balance scoring explicitly accounts for question count relative to topic count,
      so short quizzes are structurally penalised.
    """

    class SourceTopicsResponse(BaseModel):
        topics: List[str] = Field(default_factory=list)
        critical_concepts: List[str] = Field(default_factory=list)

    class QuestionSummaryResponse(BaseModel):
        topics: List[str] = Field(default_factory=list)
        cognitive_level_label: str  # recall | understanding | application
        cognitive_level_score: int = Field(ge=1, le=3)
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
        instructions_reasoning: str = ""
        sub_scores: SubScores
        final_score: float = Field(ge=0, le=100)

        @field_validator("final_score")
        @classmethod
        def final_score_matches_sub_scores(cls, v: float, info: Any) -> float:
            sub = info.data.get("sub_scores")
            if sub is not None:
                expected = sub.breadth + sub.depth + sub.balance + sub.critical
                if abs(v - expected) > 0.5:
                    raise ValueError(f"final_score {v} does not match sum of sub_scores {expected}")
            return v

    @property
    def name(self) -> str:
        return "coverage"

    @property
    def version(self) -> str:
        return "1.6"

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
        """Three-stage coverage evaluation pipeline."""
        return [
            Phase("extract", self.SourceTopicsResponse),
            Phase("map", self.QuestionSummaryResponse, fan_out=True),
            Phase("score", self.OverallCoverageResponse),
        ]

    @staticmethod
    def _get_weights(granularity: str) -> Dict[str, float]:
        if granularity == "broad":
            return {"breadth": 40.0, "depth": 20.0, "balance": 20.0, "critical": 20.0}
        elif granularity == "detailed":
            return {"breadth": 20.0, "depth": 40.0, "balance": 20.0, "critical": 20.0}
        return {"breadth": 30.0, "depth": 30.0, "balance": 20.0, "critical": 20.0}

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {
            "extract": CoverageMetric._build_extract_prompt,
            "map": CoverageMetric._build_map_prompt,
            "score": self._build_score_prompt,
        }
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_extract_prompt(inp: PhaseInput) -> str:
        if not inp.source_text:
            raise ValueError("extract phase requires source_text")
        return f"""Analyze the source material and identify its main topics and critical concepts.

**Source Material**:
{inp.source_text}

**Task**:
1. List 5-15 HIGH-LEVEL topics that the source covers. Group related concepts together.
2. From those topics, identify the 4-6 most critical "must-know" concepts — the ones \
a student absolutely cannot leave without understanding.

These critical concepts will be used as fixed ground truth to evaluate any quiz drawn \
from this source, so base them solely on the source material, not on any specific quiz.

Respond with ONLY a JSON object:
{{
  "topics": ["topic1", "topic2", ...],
  "critical_concepts": ["concept1", "concept2", ...]
}}"""

    @staticmethod
    def _build_map_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("map phase requires a question")

        extraction_output = inp.accumulated.get("extract")
        source_topics = extraction_output.data.get("topics", []) if extraction_output else []
        topics_hint = (
            f"\n**Known topics in source**: {', '.join(source_topics)}\n"
            "Map this question to topics from this list where possible."
            if source_topics
            else ""
        )

        return f"""Analyze what topics and cognitive level this quiz question tests.
{topics_hint}

**Bloom's Taxonomy — assign cognitive_level_score strictly by these definitions**:
- 1 = Recall: remembering facts, terms, definitions (e.g. "what keyword does X?")
- 2 = Understanding: explaining concepts, classifying, interpreting meaning
- 3 = Application or higher: applying knowledge to new situations, tracing code \
execution, analyzing behaviour, evaluating trade-offs

**Question #{inp.question.question_id}**:
Type: {inp.question.question_type.value}
Text: {inp.question.question_text}
Options: {inp.question.options if inp.question.options else 'N/A'}
Correct Answer: {inp.question.correct_answer}

Be precise. A question asking to identify a definition is recall (1). A question \
asking which code snippet produces a specific output requires tracing execution — \
that is application (3). When in doubt between two levels, prefer the lower one.

Respond with ONLY a JSON object:
{{
    "topics": ["topic1", "topic2", ...],
    "cognitive_level_label": "recall|understanding|application",
    "cognitive_level_score": <1, 2, or 3>,
    "reasoning": "One sentence justifying the cognitive level"
}}"""

    def _build_score_prompt(self, inp: PhaseInput) -> str:
        extraction_output = inp.accumulated.get("extract")
        source_topics = extraction_output.data.get("topics", []) if extraction_output else []
        source_critical = (
            extraction_output.data.get("critical_concepts", []) if extraction_output else []
        )

        mapping_output = inp.accumulated.get("map")
        results = mapping_output.data.get("results", []) if mapping_output else []

        if inp.quiz is None:
            raise ValueError("score phase requires a quiz")
        if not source_topics or not results:
            raise ValueError("score phase requires outputs from extract and map phases")

        granularity = self.get_param_value("granularity", **inp.params)
        weights = self._get_weights(granularity)
        num_questions = inp.quiz.num_questions
        num_topics = len(source_topics)

        # Use requested num_questions from instructions as the ideal if provided,
        # otherwise fall back to the topic-based heuristic.
        if inp.instructions and inp.instructions.num_questions:
            ideal_questions = inp.instructions.num_questions
            ideal_note = "(requested by instructions)"
            instructions_note = (
                f"\n**Instructions note**: The user requested {ideal_questions} questions "
                f"but the quiz only has {num_questions}. "
                f"You MUST populate 'instructions_reasoning' with a non-null string "
                f"explaining exactly how this shortfall affected the balance sub-score "
                f"and what deduction was applied."
            )
        else:
            ideal_questions = round(num_topics * 1.5)
            ideal_note = "(estimated from topic count)"
            instructions_note = ""

        # Pre-compute deduction_a in Python so the LLM cannot recalculate it
        deduction_a = round(
            max(0.0, (ideal_questions - num_questions) / ideal_questions)
            * (weights["balance"] / 2),
            2,
        )

        summaries_text = "\n".join(
            f"Q{i} [level={r.get('cognitive_level_score', '?')} "
            f"({r.get('cognitive_level_label', 'unknown')})]: "
            f"{', '.join(r.get('topics', []))}"
            for i, r in enumerate(results, 1)
        )

        critical_hint = (
            f"**Critical concepts from source** (use these exactly — do not substitute or add):\n"
            f"{', '.join(source_critical)}"
            if source_critical
            else "**No critical concepts extracted — identify 4-6 from the source topics above.**"
        )

        # When custom_prompt narrows the topic scope, breadth should be scored
        # against only the relevant topics — not all source topics.
        focused_topics_block = ""
        context = inp.accumulated.get("custom_prompt_context")
        if context:
            interpreted = context.data.get("interpreted_instruction", "")
            if interpreted:
                focused_topics_block = (
                    f"\n**Focused Scope (from instructions)**: {interpreted}\n"
                    f"For breadth scoring, identify which of the source topics are relevant "
                    f"to this instruction. Use ONLY those as your denominator — not all {num_topics} topics. "
                    f"A quiz that covers all relevant topics scores full breadth even if it "
                    f"ignores topics outside the stated scope.\n"
                )

        return f"""You are an expert quiz evaluator. Score quiz coverage against the source material.
{instructions_note}{focused_topics_block}
**Source Topics** ({num_topics} total):
{", ".join(source_topics)}

{critical_hint}

**Quiz**: {inp.quiz.title}
Questions: {num_questions} | Source topics: {num_topics} | Ideal question count: ~{ideal_questions} {ideal_note}

**Per-Question Analysis**:
{summaries_text}

**Scoring Framework (Granularity: {granularity})**:

1. **Breadth** (max {weights['breadth']} pts):
   - If a focused scope is specified above, first identify which source topics fall within that scope (call this N_relevant).
   - Count how many of those N_relevant topics are tested by ≥1 question (topics_covered).
   - If no scope is specified, use all {num_topics} topics as the denominator.
   - Score = (topics_covered / N_relevant) × {weights['breadth']}

2. **Depth** (max {weights['depth']} pts):
   - Sum the cognitive_level_score values from all {num_questions} questions above
   - Average = sum / {num_questions}
   - Score = (average / 3.0) × {weights['depth']}

3. **Balance** (max {weights['balance']} pts):
   - Start at {weights['balance']} pts, then apply two deductions:
   a. Question count shortfall (pre-computed, use this exact value): deduction_a = {deduction_a}
   b. Topic imbalance: 0-{weights['balance'] / 2} pts deducted subjectively for over/under-represented topics
   - balance = {weights['balance']} - deduction_a - deduction_b  (floor at 0)

4. **Critical Coverage** (max {weights['critical']} pts):
   - Use ONLY the critical concepts listed above
   - Score = (concepts_covered / {len(source_critical) if source_critical else 5}) × {weights['critical']}

Sub-score ceilings: breadth≤{weights['breadth']}, depth≤{weights['depth']}, \
balance≤{weights['balance']}, critical≤{weights['critical']}.
final_score MUST equal breadth + depth + balance + critical exactly.

Respond with ONLY this JSON object:
{{
  "topics_in_source": ["topic1", ...],
  "topics_covered": ["topic1", ...],
  "critical_concepts": ["concept1", ...],
  "critical_covered": ["concept1", ...],
  "breadth_reasoning": "X of N_relevant in-scope topics covered → (X/N_relevant) × {weights['breadth']} = score",
  "depth_reasoning": "level sum / {num_questions} = avg → avg/3 × {weights['depth']} = score",
  "balance_reasoning": "deduction_a={deduction_a} (pre-computed), deduction_b=Y → {weights['balance']}-{deduction_a}-Y=score",
  "critical_reasoning": "X of Y critical concepts covered → score",
  "instructions_reasoning": "<if num_questions was specified in instructions, explain the shortfall and its impact on balance. Otherwise empty string.>",
  "sub_scores": {{
    "breadth": <0-{weights['breadth']}>,
    "depth": <0-{weights['depth']}>,
    "balance": <0-{weights['balance']}>,
    "critical": <0-{weights['critical']}>
  }},
  "final_score": <breadth + depth + balance + critical>
}}"""

    def parse_score(self, final_output: PhaseOutput) -> float:
        """Extract final_score from the coverage scoring phase output."""
        try:
            score = float(final_output.data["final_score"])
        except KeyError:
            raise ValueError(
                f"Coverage parsing failed. Expected 'final_score', "
                f"but got keys: {list(final_output.data.keys())}"
            )
        except (ValueError, TypeError):
            raise ValueError(
                f"Could not convert final_score to float. "
                f"Got: {final_output.data.get('final_score')}"
            )

        if not 0 <= score <= 100:
            raise ValueError(f"Coverage score must be between 0 and 100, got {score}")

        return round(score, 1)

    def format_insights(self, raw_response: str, quiz_id: str) -> Optional[str]:
        """Format coverage reasoning phases into a human-readable insight block."""
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            breadth_reasoning = data.get("breadth_reasoning")
            if not breadth_reasoning:
                return None

            lines = [
                f"\n[Quiz: {quiz_id}] Coverage Analysis:",
                "-" * 40,
                f"Score: {data.get('final_score')}",
                f"Breadth:  {breadth_reasoning}",
                f"Depth:    {data.get('depth_reasoning')}",
                f"Balance:  {data.get('balance_reasoning')}",
                f"Critical: {data.get('critical_reasoning')}",
            ]
            instr_r = data.get("instructions_reasoning", "").strip()
            if instr_r and instr_r.lower() not in ("null", "none", ""):
                lines.append(f"Instructions: {instr_r}")
            if data.get("sub_scores"):
                lines.append(f"Sub-scores: {data.get('sub_scores')}")
            lines.append("-" * 40)
            return "\n".join(lines)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
