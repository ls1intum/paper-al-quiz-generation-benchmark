"""Grammatical Correctness metric implementation."""

import re
from typing import Any, List, Optional, Dict

from . import MetricParameter
from ..models.quiz import Quiz, QuizQuestion
from .base import BaseMetric, MetricScope


class GrammaticalCorrectnessMetric(BaseMetric):
    """Evaluates the grammatical correctness of a quiz.

    This metric assesses grammar, spelling, punctuation, and sentence structure
    to ensure professional, error-free quiz content.
    """

    @property
    def name(self) -> str:
        return "grammatical_correctness"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUIZ_LEVEL

    @property
    def parameters(self) -> List[MetricParameter]:
        return [
            MetricParameter(
                name="error_weights",
                param_type=Dict[str, float],
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

    import json

    def _format_quiz_for_prompt(self, quiz: Quiz) -> str:
        # 1. Document Header
        formatted = "--- CONTENT TO REVIEW START ---\n"
        formatted += f"CONTEXT: Quiz Title: {quiz.title}\n"

        # Quiz Metadata
        if hasattr(quiz, "metadata") and quiz.metadata:
            audience = quiz.metadata.get("target_audience", "General")
            formatted += f"CONTEXT: Target Audience: {audience}\n"
            if "learning_objectives" in quiz.metadata:
                objs = quiz.metadata["learning_objectives"]
                formatted += f"CONTEXT: Learning Objectives: {', '.join(objs)}\n"

        formatted += "\n" + "=" * 40 + "\n\n"

        for idx, question in enumerate(quiz.questions, 1):
            # 2. Visual Separation for each item
            formatted += f"### ITEM {idx} (ID: {question.question_id})\n"

            # Label the text explicitly so the LLM knows this is the "Subject"
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

            # 3. Handle Source Reference cleanly
            if hasattr(question, "source_reference") and question.source_reference:
                formatted += f"**Reference:** {question.source_reference}\n"

            # 4. formatting metadata as lines, not JSON blob
            if hasattr(question, "metadata") and question.metadata:
                formatted += "**Metadata Tags:** "
                # Join values to create a readable string, avoiding JSON syntax
                tags = [f"{k}={v}" for k, v in question.metadata.items()]
                formatted += ", ".join(tags) + "\n"

            formatted += "_" * 40 + "\n\n"

        formatted += "--- CONTENT TO REVIEW END ---"
        return formatted

    def get_prompt(
        self,
        question: Optional[QuizQuestion] = None,
        quiz: Optional[Quiz] = None,
        source_text: Optional[str] = None,
        **params: Any,
    ) -> str:
        """Generate grammatical correctness evaluation prompt.

        Args:
            question: Question to evaluate
            quiz: Not used (question-level metric)
            source_text: Not used
            **params: No parameters for this metric

        Returns:
            Formatted prompt

        Raises:
            ValueError: If question is None
        """

        if quiz is None:
            raise ValueError("GrammaticMetric requires a quiz")

        self.validate_params(**params)
        error_weights = self.get_param_value("error_weights", **params)
        language = self.get_param_value("language", **params)

        quiz_content = self._format_quiz_for_prompt(quiz)

        prompt = f"""You are evaluating the grammatical correctness of quiz content.
    
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
        {"score": <number between 0 and 100>}
        """

        return prompt

    def parse_response(self, llm_response: str) -> float:
        """Parse grammatical correctness score from LLM response.

        Args:
            llm_response: Raw LLM response

        Returns:
            Score between 0 and 100

        Raises:
            ValueError: If score cannot be extracted
        """
        print(f"DEBUG - Raw LLM Response: '{llm_response}'")
        print(f"DEBUG - Response length: {len(llm_response)}")
        print(f"DEBUG - Response type: {type(llm_response)}")

        response = llm_response.strip()

        # Try to find a number
        match = re.search(r"\b(\d+(?:\.\d+)?)\b", response)
        if match:
            score = float(match.group(1))
            if 0 <= score <= 100:
                return score

        raise ValueError(
            f"Could not parse grammatical correctness score from response: {llm_response}"
        )
