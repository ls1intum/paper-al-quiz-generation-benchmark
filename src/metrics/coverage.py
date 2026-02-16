"""Coverage metric implementation."""

import json
import re
from typing import Any, Dict, List, Optional
from ..models.quiz import Quiz, QuizQuestion
from .base import BaseMetric, MetricParameter, MetricScope, EvaluationResult


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
        return "1.1"  # Fixed determinism issue

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

    def _get_weights(self, granularity: str) -> Dict[str, int]:
        """Return weight distribution for the four sub-scores."""
        if granularity == "broad":
            return {"breadth": 40, "depth": 20, "balance": 20, "critical": 20}
        elif granularity == "detailed":
            return {"breadth": 20, "depth": 40, "balance": 20, "critical": 20}
        else:  # balanced
            return {"breadth": 30, "depth": 30, "balance": 20, "critical": 20}

    def _get_question_topic_prompt(self, question: QuizQuestion, source_text: str) -> str:
        """Generate prompt for stage 1: extract topics from a single question."""
        return f"""Analyze what topics this quiz question tests from the source material.

    **Source Material**:
    {source_text}
    
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

    def _get_overall_coverage_prompt(
        self,
        source_text: str,
        quiz: Quiz,
        question_summaries: List[Dict[str, Any]],
        granularity: str,
    ) -> str:
        """Generate prompt for stage 2: analyze overall coverage."""
        weights = self._get_weights(granularity)

        # Build summary of all questions and their topics
        summaries_text = []
        for i, summary in enumerate(question_summaries, 1):
            topics = ", ".join(summary.get("topics", []))
            level = summary.get("cognitive_level", "unknown")
            summaries_text.append(f"Q{i} [{level}]: {topics}")

        summaries_block = "\n".join(summaries_text)

        return f"""You are an expert quiz evaluator. Assess how well this quiz covers the source material.

    **CRITICAL: Your response must be ONLY a JSON object. No other text.**

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
    {summaries_block}

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

    **Required JSON Format**:
    ```json
    {{
      "topics_in_source": ["topic1", "topic2", ...],
      "topics_covered": ["topic1", ...],
      "critical_concepts": ["concept1", ...],
      "critical_covered": ["concept1", ...],
      "reasoning": "Step-by-step explanation of scores",
      "sub_scores": {{
        "breadth": <0-{weights['breadth']}>,
        "depth": <0-{weights['depth']}>,
        "balance": <0-{weights['balance']}>,
        "critical": <0-{weights['critical']}>
      }},
      "final_score": <sum of sub_scores>
    }}
    ```

    Respond with ONLY the JSON object, no other text.
    """

    def evaluate(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        llm_client: Optional[Any] = None,
        **params: Any,
    ) -> EvaluationResult:
        """Two-stage evaluation with response tracking."""
        if quiz is None:
            raise ValueError("CoverageMetric requires a quiz")
        if source_text is None:
            raise ValueError("CoverageMetric requires source_text")
        if llm_client is None:
            raise ValueError("CoverageMetric requires an llm_client")

        self.validate_params(**params)
        granularity = self.get_param_value("granularity", **params)

        # STAGE 1: Extract topics from each question
        question_summaries = []
        stage1_responses = []

        for q in quiz.questions:
            prompt = self._get_question_topic_prompt(q, source_text)
            response = llm_client.generate(prompt)
            stage1_responses.append({"question_id": q.question_id, "response": response})

            try:
                summary = self._parse_question_summary(response)
                question_summaries.append(summary)
            except Exception:
                question_summaries.append(
                    {"topics": [], "cognitive_level": "unknown", "reasoning": "Failed to parse"}
                )

        # STAGE 2: Analyze overall coverage
        overall_prompt = self._get_overall_coverage_prompt(
            source_text, quiz, question_summaries, granularity
        )
        overall_response = llm_client.generate(overall_prompt)

        score = self.parse_response(overall_response)

        return EvaluationResult(
            score=score,
            raw_response=overall_response,
            metadata={
                "stage1_responses": stage1_responses,
                "question_summaries": question_summaries,
                "granularity": granularity,
            },
        )

    def _parse_question_summary(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from question topic extraction."""
        response = response.strip()
        response = re.sub(r"^```json?\s*\n", "", response, flags=re.MULTILINE)
        response = re.sub(r"\n```\s*$", "", response, flags=re.MULTILINE)

        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response[start:end])

        raise ValueError("Could not parse question summary JSON")

    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        **params: Any,
    ) -> str:
        """
        Not applicable for two-stage coverage evaluation.

        Coverage metric uses a custom evaluate() method that orchestrates
        multiple LLM calls. Use evaluate() directly instead.

        Raises:
            NotImplementedError: This metric uses custom evaluation logic
        """
        raise NotImplementedError(
            f"{self.name} uses a two-stage evaluation approach and does not "
            "support get_prompt(). Use evaluate() directly."
        )

    def parse_response(self, llm_response: str) -> float:
        """
        Parse the final coverage score from the LLM's JSON response.
        Falls back to regex-based extraction if JSON is malformed.
        """
        response = llm_response.strip()

        # Remove Markdown code fences if present
        response = re.sub(r"^```json?\s*\n", "", response, flags=re.MULTILINE)
        response = re.sub(r"\n```\s*$", "", response, flags=re.MULTILINE)

        # ----- PRIMARY: JSON extraction -----
        try:
            start = response.find("{")
            end = response.rfind("}") + 1

            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                # Extract final_score
                if "final_score" in data:
                    score = float(data["final_score"])
                    if 0 <= score <= 100:
                        return round(score, 1)

                # If final_score missing but sub_scores present, sum them
                if "sub_scores" in data:
                    subs = data["sub_scores"]
                    total = sum(
                        float(subs.get(k, 0)) for k in ("breadth", "depth", "balance", "critical")
                    )
                    if 0 <= total <= 100:
                        return round(total, 1)
        except (ValueError, KeyError, json.JSONDecodeError):
            pass

        # ----- FALLBACK: explicit score patterns -----
        patterns = [
            r'"final_score"\s*:\s*(\d+(?:\.\d+)?)',
            r"TOTAL\s+COVERAGE\s+SCORE\s*:?\s*(\d+(?:\.\d+)?)",
            r"FINAL\s+SCORE\s*:?\s*(\d+(?:\.\d+)?)",
        ]
        for pat in patterns:
            match = re.search(pat, response, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if 0 <= score <= 100:
                    return round(score, 1)

        raise ValueError(
            f"Could not parse coverage score from response.\n"
            f"Response preview: {response[:500]}..."
        )
