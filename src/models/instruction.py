from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from .quiz import QuestionType


class QuizInstructions(BaseModel):
    """
    User-supplied intent for what the quiz should be.
    Passed to every metric so scoring can be intent-aware.
    """

    language: Optional[str] = None
    num_questions: Optional[int] = None
    question_types: List[str] = Field(
        default_factory=list,
        description="Allowed question types (e.g., 'multiple_choice', 'single_choice', 'true_false')",
    )
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    custom_prompt: Optional[str] = None  # Free-text override: "do not include this topic at all"

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, v: List[str]) -> List[str]:
        """Validate that all question types are valid QuestionType enum values."""
        valid_types = {qt.value for qt in QuestionType}
        invalid = [t for t in v if t not in valid_types]
        if invalid:
            raise ValueError(
                f"Invalid question types: {invalid}. " f"Valid types are: {sorted(valid_types)}"
            )
        return v
