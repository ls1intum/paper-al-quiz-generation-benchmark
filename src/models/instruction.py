from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class QuizInstructions(BaseModel):
    """
    User-supplied intent for what the quiz should be.
    Passed to every metric so scoring can be intent-aware.
    """

    language: Optional[str] = None
    num_questions: Optional[int] = None
    question_types: List[str] = Field(default_factory=list)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    custom_prompt: Optional[str] = None  # Free-text override: "do not include this topic at all"
