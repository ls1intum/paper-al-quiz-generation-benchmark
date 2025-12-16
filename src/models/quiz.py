"""Quiz data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class QuestionType(str, Enum):
    """Types of quiz questions."""

    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TRUE_FALSE = "true_false"


@dataclass
class QuizQuestion:
    """Represents a single quiz question.

    Attributes:
        question_id: Unique identifier for the question
        question_type: Type of question (MC, SC, T/F)
        question_text: The question text
        options: List of answer options
        correct_answer: Correct answer(s) - string for SC/T/F, list for MC
        source_reference: Optional reference to source material section
        metadata: Additional metadata (e.g., topic, difficulty level)
    """

    question_id: str
    question_type: QuestionType
    question_text: str
    options: List[str]
    correct_answer: Union[str, List[str]]
    source_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate question data after initialization."""
        # Convert string to enum if needed
        if isinstance(self.question_type, str):
            self.question_type = QuestionType(self.question_type)

        # Validate correct_answer format
        if self.question_type == QuestionType.MULTIPLE_CHOICE:
            if not isinstance(self.correct_answer, list):
                raise ValueError("Multiple choice questions must have list of correct answers")
        else:
            if not isinstance(self.correct_answer, str):
                raise ValueError("Single choice and T/F questions must have string answer")

        # Validate true/false options
        if self.question_type == QuestionType.TRUE_FALSE:
            if self.options != ["True", "False"]:
                raise ValueError("True/False questions must have options ['True', 'False']")


@dataclass
class Quiz:
    """Represents a complete quiz.

    Attributes:
        quiz_id: Unique identifier for the quiz
        title: Quiz title
        source_material: Reference to source markdown file
        questions: List of quiz questions
        metadata: Additional metadata (e.g., target audience, learning objectives)
        created_at: When the quiz was created
    """

    quiz_id: str
    title: str
    source_material: str
    questions: List[QuizQuestion]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def get_question_by_id(self, question_id: str) -> Optional[QuizQuestion]:
        """Get a question by its ID.

        Args:
            question_id: The question ID to search for

        Returns:
            The question if found, None otherwise
        """
        for question in self.questions:
            if question.question_id == question_id:
                return question
        return None

    def get_questions_by_type(self, question_type: QuestionType) -> List[QuizQuestion]:
        """Get all questions of a specific type.

        Args:
            question_type: The type of questions to retrieve

        Returns:
            List of questions matching the type
        """
        return [q for q in self.questions if q.question_type == question_type]

    @property
    def num_questions(self) -> int:
        """Get the total number of questions."""
        return len(self.questions)
