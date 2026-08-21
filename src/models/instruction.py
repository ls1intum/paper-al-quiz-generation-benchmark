from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .quiz import QuestionType


class QuizInstructions(BaseModel):
    """
    User-supplied intent for what the quiz should be.
    Passed to every metric so scoring can be intent-aware.
    """

    language: str | None = None
    num_questions: int | None = None
    question_types: list[str] = Field(
        default_factory=list,
        description="Allowed question types (e.g., 'multiple_choice', 'single_choice', 'true_false')",
    )
    difficulty: Literal["easy", "medium", "hard"] | None = None
    custom_prompt: str | None = None  # Free-text override: "do not include this topic at all"

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, v: list[str]) -> list[str]:
        """Validate that all question types are valid QuestionType enum values."""
        valid_types = {qt.value for qt in QuestionType}
        invalid = [t for t in v if t not in valid_types]
        if invalid:
            raise ValueError(
                f"Invalid question types: {invalid}. " f"Valid types are: {sorted(valid_types)}"
            )
        return v
