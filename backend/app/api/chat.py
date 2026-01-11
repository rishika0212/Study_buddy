from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from backend.app.services.tutor_service import TutorService
from backend.app.services.assessment_service import AssessmentService
from backend.app.memory.user_profile import UserProfile
from backend.app.errors import (
    MissingContextError,
    ValidationError,
    AssessmentInterruptionError,
    log_error,
)

router = APIRouter()
tutor_service = TutorService()
assessment_service = AssessmentService()

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # DEPRECATED - ignored
    message: str

class ChatResponse(BaseModel):
    response: str
    metadata: dict = {}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message - topic-centric model, no sessions.
    session_id parameter is DEPRECATED and ignored.
    """
    if not request.user_id or not isinstance(request.user_id, str):
        raise ValidationError("user_id is required and must be a string", field="user_id")
    
    if not request.message or not isinstance(request.message, str):
        raise ValidationError("message is required and must be a string", field="message")
    
    try:
        data = await tutor_service.process_message(request.user_id, request.message)
        return ChatResponse(
            response=data["response"],
            metadata=data.get("metadata", {})
        )
    except (MissingContextError, ValidationError):
        raise
    except Exception as e:
        log_error(
            e,
            error_type="CHAT_PROCESSING_ERROR",
            user_action=f"POST /api/chat",
            additional_context={"user_id": request.user_id}
        )
        raise

class MCQGenerateRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # DEPRECATED - ignored
    topic: str

class MCQSubmitRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # DEPRECATED - ignored
    topic: str
    user_answer: str

@router.post("/assessment/mcq/generate")
async def generate_mcq(request: MCQGenerateRequest):
    """Generate MCQ - topic must exist (have been explained)."""
    if not request.user_id or not request.topic:
        raise ValidationError("user_id and topic are required", field="request")
    
    try:
        profile = UserProfile(request.user_id)
        # Check if topic exists (has been explained)
        if request.topic not in profile.data.get("topics", {}):
            raise MissingContextError(
                message=f"Topic '{request.topic}' has not been explained yet. Only explained topics can be assessed.",
                required_fields=["topic"]
            )
        
        topic_data = profile.data["topics"][request.topic]
        mastery = topic_data.get("mastery_score", 0.0)
        
        question_data = await assessment_service.generate_mcq(request.user_id, request.topic, mastery)
        return question_data
    except MissingContextError:
        raise
    except Exception as e:
        log_error(
            e,
            error_type="MCQ_GENERATION_ERROR",
            user_action=f"POST /api/assessment/mcq/generate",
            additional_context={"topic": request.topic}
        )
        raise

@router.post("/assessment/mcq/submit")
async def submit_mcq(request: MCQSubmitRequest):
    """Submit MCQ answer."""
    if not request.user_id or not request.topic:
        raise ValidationError("user_id and topic are required", field="request")
    
    try:
        result = await assessment_service.submit_mcq_answer(
            request.user_id, request.topic, request.user_answer
        )
        return result
    except Exception as e:
        log_error(
            e,
            error_type="MCQ_SUBMISSION_ERROR",
            user_action=f"POST /api/assessment/mcq/submit",
            additional_context={"topic": request.topic}
        )
        raise

class QNAGenerateRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # DEPRECATED - ignored
    topic: str
    length: str = "medium"

class QNASubmitRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # DEPRECATED - ignored
    topic: str
    user_answer: str

@router.post("/assessment/qna/generate")
async def generate_qna(request: QNAGenerateRequest):
    """Generate QNA - topic must exist (have been explained)."""
    if not request.user_id or not request.topic:
        raise ValidationError("user_id and topic are required", field="request")
    
    try:
        profile = UserProfile(request.user_id)
        # Check if topic exists (has been explained)
        if request.topic not in profile.data.get("topics", {}):
            raise MissingContextError(
                message=f"Topic '{request.topic}' has not been explained yet. Only explained topics can be assessed.",
                required_fields=["topic"]
            )
        
        topic_data = profile.data["topics"][request.topic]
        mastery = topic_data.get("mastery_score", 0.0)
        
        question_data = await assessment_service.generate_qna(request.user_id, request.topic, mastery, request.length)
        return question_data
    except MissingContextError:
        raise
    except Exception as e:
        log_error(
            e,
            error_type="QNA_GENERATION_ERROR",
            user_action=f"POST /api/assessment/qna/generate",
            additional_context={"topic": request.topic}
        )
        raise

@router.post("/assessment/qna/submit")
async def submit_qna(request: QNASubmitRequest):
    """Submit QNA answer."""
    if not request.user_id or not request.topic:
        raise ValidationError("user_id and topic are required", field="request")
    
    try:
        result = await assessment_service.submit_qna_answer(
            request.user_id, request.topic, request.user_answer
        )
        return result
    except Exception as e:
        log_error(
            e,
            error_type="QNA_SUBMISSION_ERROR",
            user_action=f"POST /api/assessment/qna/submit",
            additional_context={"topic": request.topic}
        )
        raise

class AddTopicRequest(BaseModel):
    user_id: str
    topic: str
    explanation_summary: Optional[str] = None

@router.post("/topic/add")
async def add_topic(request: AddTopicRequest):
    """
    Add topic - should only be called after explanation is given.
    Topics should NOT be created from casual mentions or questions.
    """
    if not request.user_id or not request.topic:
        raise ValidationError("user_id and topic are required", field="request")
    
    try:
        profile = UserProfile(request.user_id)
        profile.add_topic(request.topic, explanation_summary=request.explanation_summary)
        return {"message": f"Topic '{request.topic}' added."}
    except Exception as e:
        log_error(
            e,
            error_type="ADD_TOPIC_ERROR",
            user_action=f"POST /api/topic/add",
            additional_context={"topic": request.topic}
        )
        raise

class AreasRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None  # DEPRECATED - ignored

@router.post("/areas/get")
async def get_learning_areas(request: AreasRequest):
    """
    Get weak and strong areas with metadata for the UI.
    Topic-centric model - no sessions.
    """
    profile = UserProfile(request.user_id)
    
    weak_areas = profile.get_weak_areas_with_metadata(max_display=10)
    strong_areas = profile.get_strong_areas_with_metadata(max_display=10)
    
    return {
        "weak_areas": weak_areas,
        "strong_areas": strong_areas
    }