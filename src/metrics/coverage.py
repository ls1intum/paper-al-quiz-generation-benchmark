"""Coverage metric implementation - IMPROVED V1.1 (Deterministic)."""

import json
import re
from typing import Any, Dict, List, Optional
from ..models.quiz import Quiz, QuizQuestion
from .base import BaseMetric, MetricParameter, MetricScope


class CoverageMetric(BaseMetric):
    """Evaluates how well the quiz covers the source material.

    This metric assesses breadth and depth of content coverage using
    structured JSON output and deterministic sampling.
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
            MetricParameter(
                name="use_example",
                param_type=bool,
                default=True,
                description="Include an example in the prompt",
            ),
        ]

    def _sample_source_text(self, source_text: str, total_chars: int = 3500) -> str:
        """
        Extract a representative sample from the source text DETERMINISTICALLY:
        - If text length ≤ total_chars, return whole text.
        - Otherwise, take the first 1200 chars, middle 1200 chars, and last 1100 chars.

        NOTE: Uses deterministic middle selection (not random) for consistent scores.
        """
        if len(source_text) <= total_chars:
            return source_text

        # Fixed intro (first 1200 chars)
        intro = source_text[:1200]

        # Deterministic middle (always from center)
        mid_start = (len(source_text) - 1200) // 2  # Center point
        mid = source_text[mid_start : mid_start + 1200]

        # Fixed outro (last 1100 chars)
        outro = source_text[-1100:]

        sample = (
            f"[BEGINNING OF SOURCE]\n{intro}\n\n"
            f"[MIDDLE SECTION]\n{mid}\n\n"
            f"[END OF SOURCE]\n{outro}"
        )
        return sample

    def _get_weights(self, granularity: str) -> Dict[str, int]:
        """Return weight distribution for the four sub-scores."""
        if granularity == "broad":
            return {"breadth": 40, "depth": 20, "balance": 20, "critical": 20}
        elif granularity == "detailed":
            return {"breadth": 20, "depth": 40, "balance": 20, "critical": 20}
        else:  # balanced
            return {"breadth": 30, "depth": 30, "balance": 20, "critical": 20}

    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        **params: Any,
    ) -> str:
        """Generate a coverage evaluation prompt with structured JSON output."""
        if quiz is None:
            raise ValueError("CoverageMetric requires a quiz")
        if source_text is None:
            raise ValueError("CoverageMetric requires source_text")

        self.validate_params(**params)
        granularity = self.get_param_value("granularity", **params)
        use_example = self.get_param_value("use_example", **params)

        # 1. Get a representative sample of the source text (DETERMINISTIC)
        source_sample = self._sample_source_text(source_text)

        # 2. Build a detailed quiz summary
        quiz_summary_lines = [f"Title: {quiz.title}", f"Total Questions: {quiz.num_questions}", ""]
        for i, q in enumerate(quiz.questions, 1):
            # Include first 150 chars of question text to keep prompt manageable
            q_text = q.question_text[:150] + ("..." if len(q.question_text) > 150 else "")
            quiz_summary_lines.append(f"{i}. [{q.question_type.value}] {q_text}")
        quiz_summary = "\n".join(quiz_summary_lines)

        # 3. Get weights for this granularity
        weights = self._get_weights(granularity)

        # 4. Few-shot example (optional)
        example_block = ""
        if use_example:
            example_block = """
--- EXAMPLE ---
**Source (excerpt)**:
"Photosynthesis occurs in chloroplasts and has two main stages: light-dependent reactions (in thylakoid membranes) and the Calvin cycle (in stroma). Light reactions use chlorophyll to capture light energy and produce ATP and NADPH. The Calvin cycle uses these products to fix CO2 into glucose. Key factors affecting photosynthesis rate include light intensity, CO2 concentration, temperature, and water availability. Major pigments are chlorophyll a, chlorophyll b, and carotenoids."

**Quiz (5 questions)**:
1. [MCQ] Where does the Calvin cycle occur?
2. [MCQ] What are the products of light reactions?
3. [True/False] Chlorophyll is the only pigment in photosynthesis.
4. [Short Answer] Name two factors that affect photosynthesis rate.
5. [MCQ] What is the main function of the Calvin cycle?

**Expected JSON Output**:
```json
{
  "topics_source": [
    "chloroplast structure",
    "light-dependent reactions (location, products, mechanism)",
    "Calvin cycle (location, function)",
    "photosynthetic pigments (types)",
    "limiting factors (light, CO2, temperature, water)"
  ],
  "topics_covered": [
    "Calvin cycle location and function",
    "light reactions products",
    "photosynthetic pigments",
    "limiting factors"
  ],
  "reasoning": "Source has 5 major topics. Quiz covers 4/5 (80% breadth). Depth is mixed: Q1,Q2,Q5 test recall; Q3 tests understanding (misconception); Q4 tests recall. Average depth ≈ 1.3/3. Balance is good - important topics get multiple questions. Critical coverage: Calvin cycle and light reactions both tested (core concepts present).",
  "sub_scores": {
    "breadth": 24,
    "depth": 13,
    "balance": 16,
    "critical": 17
  },
  "final_score": 70
}
```
--- END EXAMPLE ---
"""

        # 5. Build the full prompt
        prompt = f"""You are an expert quiz evaluator. Assess how well this quiz covers the source material.

**CRITICAL: Your response must be ONLY a JSON object. No other text.**

**Calibration Guidelines**:
- Most good quizzes score 55-75 (this is NORMAL and EXPECTED)
- 75-85 = very good coverage
- 85-100 = exceptional, comprehensive coverage (rare)
- 40-55 = adequate but with gaps
- Below 40 = significant problems

**Source Material Sample**:
{source_sample}

**Quiz to Evaluate**:
{quiz_summary}

**Scoring Framework (Granularity: {granularity})**:

1. **Breadth** (max {weights['breadth']} pts):
   - List ALL distinct topics in the source
   - Count how many are tested by ≥1 question
   - Score = (topics_covered / topics_total) × {weights['breadth']}

2. **Depth** (max {weights['depth']} pts):
   - Rate each covered topic: 1=recall, 2=understanding, 3=application
   - Average these ratings
   - Score = (avg_rating / 3.0) × {weights['depth']}

3. **Balance** (max {weights['balance']} pts):
   - Are important topics given appropriate question weight?
   - Are minor details over-represented?
   - Score subjectively 0-{weights['balance']}

4. **Critical Coverage** (max {weights['critical']} pts):
   - Identify 3-5 essential "must-know" concepts
   - Count how many are tested
   - Score = (critical_covered / critical_total) × {weights['critical']}

{example_block}

**Required JSON Format**:
```json
{{
  "topics_source": ["topic1", "topic2", ...],
  "topics_covered": ["topic1", ...],
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

        return prompt

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
            # Find the first '{' and the last '}'
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
            # JSON parsing failed, continue to fallbacks
            pass

        # ----- FALLBACK 1: explicit score patterns -----
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

        # ----- FALLBACK 2: look for "X/100" pattern -----
        frac_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*100", response)
        if frac_match:
            score = float(frac_match.group(1))
            if 0 <= score <= 100:
                return round(score, 1)

        # ----- FALLBACK 3: any number 0-100 that appears last -----
        numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", response)
        for num in reversed(numbers):
            score = float(num)
            if 0 <= score <= 100:
                return round(score, 1)

        raise ValueError(
            f"Could not parse coverage score from response.\n"
            f"Response preview: {response[:500]}..."
        )
