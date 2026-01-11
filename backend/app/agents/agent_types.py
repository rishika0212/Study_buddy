from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any, Dict

class Observation(BaseModel):
    intent: str = Field(description="The user's primary goal in this turn")
    confidence_level: float = Field(description="Score from 0 to 1 indicating user's confidence")
    confusion_detected: bool = Field(description="Whether the user seems confused")
    detected_concepts: List[str] = Field(default_factory=list)

class Plan(BaseModel):
    strategy: Literal["explain", "analogy", "example", "quiz", "revision", "summarize", "encourage"]
    depth: Literal["beginner", "intermediate", "advanced"]
    focus_area: str
    reasoning: str

class Reflection(BaseModel):
    effectiveness: float = Field(description="Score from 0 to 1 on how helpful the response was likely to be")
    user_progress: Any = Field(description="Summary of how this turn moved the needle on learning")
    adaptation_needed: bool = Field(description="Whether the strategy should change in next turn")

class AssessmentState(BaseModel):
    total_questions: int
    current_question_index: int
    answered_questions: List[int] = Field(default_factory=list)
    unanswered_questions: List[int] = Field(default_factory=list)
    user_answers: Dict[int, str] = Field(default_factory=dict)
    correct_answers: int = 0
    incorrect_answers: int = 0
    submitted: bool = False
    evaluated: bool = False
    topic: str
    mode: str = "Medium" # Short, Medium, Long
    questions: List[Dict[str, Any]]

class AgentState(BaseModel):
    user_id: str
    last_observation: Optional[Observation] = None
    last_plan: Optional[Plan] = None
    last_reflection: Optional[Reflection] = None
    mastery_levels: dict = Field(default_factory=dict)
