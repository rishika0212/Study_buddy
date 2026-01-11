"""
Enhanced chat API with performance optimizations.

Features:
- Response streaming for long explanations
- Performance monitoring
- Lazy session loading
- Caching integration
- Background question pre-generation
"""

from fastapi import APIRouter, HTTPException, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, AsyncIterator
import asyncio

from backend.app.services.tutor_service import TutorService
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.lazy_loading import get_session_loader, release_session
from backend.app.services.performance_monitor import get_performance_monitor, TimedResponse
from backend.app.services.streaming_and_models import TaskType, ModelSelector, ResponseStreamer
from backend.app.services.question_generation import get_question_generator, QuestionPool
from backend.app.cache.explanation_cache import ExplanationCache
from backend.app.memory.user_profile import UserProfile
from backend.app.utils.logger import logger

router = APIRouter()
tutor_service = TutorService()
assessment_service = AssessmentService()
performance_monitor = get_performance_monitor()


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    session_id: str
    metadata: dict = {}


class MCQGenerateRequest(BaseModel):
    user_id: str
    session_id: str
    topic: str


class MCQSubmitRequest(BaseModel):
    user_id: str
    session_id: str
    topic: str
    user_answer: str


class QNAGenerateRequest(BaseModel):
    user_id: str
    session_id: str
    topic: str
    length: str = "medium"


class QNASubmitRequest(BaseModel):
    user_id: str
    session_id: str
    topic: str
    user_answer: str


class SessionMetadataRequest(BaseModel):
    user_id: str
    session_id: str


class ConversationHistoryRequest(BaseModel):
    user_id: str
    session_id: str
    page: int = 0
    page_size: int = 50


class AreasRequest(BaseModel):
    user_id: str
    session_id: str


# ==================== Optimized Endpoints ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Chat endpoint with explanation caching and streaming support.
    
    Targets: <2s for explanations
    """
    with TimedResponse(f"/chat", "POST") as timer:
        try:
            cache = ExplanationCache(request.user_id, request.session_id)
            
            # Check if we need to cache this response
            cache_key = f"chat:{request.message[:50]}"
            cached = cache.get(cache_key)
            if cached:
                performance_monitor.record_cache_hit("explanation")
                return ChatResponse(
                    response=cached,
                    session_id=request.session_id,
                    metadata={"source": "cache"}
                )
            
            performance_monitor.record_cache_miss("explanation")
            
            # Process message
            data = await tutor_service.process_message(
                request.user_id, request.message, request.session_id
            )
            
            response_text = data.get("response", "")
            
            # Cache the response if it's a substantial explanation
            if len(response_text) > 200:
                cache.set(cache_key, response_text, metadata={
                    "task": "chat",
                    "message_length": len(request.message)
                })
            
            # Trigger background question pre-generation if topic mentioned
            if "topic" in request.message.lower():
                topic_mentioned = extract_topic_from_message(request.message)
                if topic_mentioned:
                    background_tasks.add_task(
                        get_question_generator().start_background_generation,
                        request.user_id, request.session_id, topic_mentioned
                    )
            
            return ChatResponse(
                response=response_text,
                session_id=request.session_id,
                metadata=data.get("metadata", {})
            )
        
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return ChatResponse(
                response=f"An error occurred: {str(e)}",
                session_id=request.session_id,
                metadata={"error": True}
            )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint for long explanations.
    
    Streams response in 50-token chunks for progressive display.
    """
    async def generate():
        try:
            # Get response from tutor
            data = await tutor_service.process_message(
                request.user_id, request.message, request.session_id
            )
            
            response_text = data.get("response", "")
            
            # Stream the response in chunks
            words = response_text.split()
            chunk_size = 50  # ~50 tokens per chunk
            words_per_chunk = int(chunk_size / 1.3)
            
            for i in range(0, len(words), words_per_chunk):
                chunk = " ".join(words[i:i + words_per_chunk])
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.01)  # Small delay for UX
            
            performance_monitor.record_response(
                endpoint="/chat/stream",
                method="POST",
                response_time_ms=0,  # Handled by context manager elsewhere
                streaming=True
            )
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/assessment/mcq/generate")
async def generate_mcq(request: MCQGenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate MCQ with question pool pre-loading.
    
    Targets: <3s for question generation
    - Tries to get from pre-generated pool (near-instant)
    - Falls back to generation if pool empty
    """
    with TimedResponse("/assessment/mcq/generate", "POST"):
        try:
            profile = UserProfile(request.user_id, request.session_id)
            topic_data = profile.add_topic(request.topic)
            mastery = topic_data["mastery_score"]
            
            # Try to get from pre-generated pool
            pool = QuestionPool(request.user_id, request.session_id)
            question = pool.get_next_question(request.topic, "mcq")
            
            if question:
                logger.info(f"Served MCQ from pre-generated pool for {request.topic}")
                performance_monitor.record_cache_hit("question_pool")
                
                # Trigger background re-generation to refill pool
                background_tasks.add_task(
                    get_question_generator().start_background_generation,
                    request.user_id, request.session_id, request.topic, mastery, "mcq"
                )
                
                return question
            
            # Pool empty, generate now
            performance_monitor.record_cache_miss("question_pool")
            logger.info(f"Generating MCQ on-demand for {request.topic}")
            
            question_data = await assessment_service.generate_mcq(
                request.user_id, request.session_id, request.topic, mastery
            )
            
            # Trigger background pre-generation for next time
            background_tasks.add_task(
                get_question_generator().start_background_generation,
                request.user_id, request.session_id, request.topic, mastery, "mcq"
            )
            
            return question_data
        
        except Exception as e:
            logger.error(f"MCQ generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment/mcq/submit")
async def submit_mcq(request: MCQSubmitRequest):
    """
    Submit MCQ answer with fast evaluation.
    
    Targets: <1s for evaluation
    """
    with TimedResponse("/assessment/mcq/submit", "POST"):
        try:
            result = await assessment_service.submit_mcq_answer(
                request.user_id, request.session_id, request.topic, request.user_answer
            )
            performance_monitor.record_response(
                endpoint="/assessment/mcq/submit",
                method="POST",
                response_time_ms=0,
                task_type=TaskType.MCQ_EVALUATION.value
            )
            return result
        except Exception as e:
            logger.error(f"MCQ submission error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment/qna/generate")
async def generate_qna(request: QNAGenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate QnA with question pool pre-loading.
    
    Targets: <3s for question generation
    """
    with TimedResponse("/assessment/qna/generate", "POST"):
        try:
            profile = UserProfile(request.user_id, request.session_id)
            topic_data = profile.add_topic(request.topic)
            mastery = topic_data["mastery_score"]
            
            # Try to get from pre-generated pool
            pool = QuestionPool(request.user_id, request.session_id)
            question = pool.get_next_question(request.topic, "qna")
            
            if question:
                logger.info(f"Served QnA from pre-generated pool for {request.topic}")
                performance_monitor.record_cache_hit("question_pool")
                
                # Trigger background re-generation
                background_tasks.add_task(
                    get_question_generator().start_background_generation,
                    request.user_id, request.session_id, request.topic, mastery, "qna"
                )
                
                return question
            
            performance_monitor.record_cache_miss("question_pool")
            logger.info(f"Generating QnA on-demand for {request.topic}")
            
            question_data = await assessment_service.generate_qna(
                request.user_id, request.session_id, request.topic, mastery, request.length
            )
            
            background_tasks.add_task(
                get_question_generator().start_background_generation,
                request.user_id, request.session_id, request.topic, mastery, "qna"
            )
            
            return question_data
        
        except Exception as e:
            logger.error(f"QnA generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment/qna/submit")
async def submit_qna(request: QNASubmitRequest):
    """
    Submit QnA answer with evaluation.
    
    Targets: <3s for evaluation
    """
    with TimedResponse("/assessment/qna/submit", "POST"):
        try:
            result = await assessment_service.submit_qna_answer(
                request.user_id, request.session_id, request.topic, request.user_answer
            )
            performance_monitor.record_response(
                endpoint="/assessment/qna/submit",
                method="POST",
                response_time_ms=0,
                task_type=TaskType.QUESTION_EVALUATION.value
            )
            return result
        except Exception as e:
            logger.error(f"QnA submission error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/topic/add")
async def add_topic(request: MCQGenerateRequest, background_tasks: BackgroundTasks):
    """
    Add topic with background question pre-generation.
    
    Targets: <500ms
    """
    with TimedResponse("/topic/add", "POST"):
        try:
            profile = UserProfile(request.user_id, request.session_id)
            profile.add_topic(request.topic)
            
            # Trigger background question generation
            background_tasks.add_task(
                get_question_generator().start_background_generation,
                request.user_id, request.session_id, request.topic, 0.0
            )
            
            return {
                "message": f"Topic '{request.topic}' added.",
                "background_generation": "started"
            }
        except Exception as e:
            logger.error(f"Topic add error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/metadata")
async def get_session_metadata(request: SessionMetadataRequest):
    """
    Get lightweight session metadata (lazy loading).
    
    Targets: <500ms
    """
    with TimedResponse("/session/metadata", "POST"):
        try:
            loader = get_session_loader(request.user_id, request.session_id)
            metadata = loader.get_session_metadata()
            return metadata
        except Exception as e:
            logger.error(f"Session metadata error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/history")
async def get_conversation_history(request: ConversationHistoryRequest):
    """
    Get paginated conversation history (lazy loading).
    
    Targets: <500ms
    """
    with TimedResponse("/session/history", "POST"):
        try:
            loader = get_session_loader(request.user_id, request.session_id)
            history = loader.get_conversation_history(
                page=request.page,
                count=None if request.page >= 0 else request.page_size
            )
            return history
        except Exception as e:
            logger.error(f"Conversation history error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/end")
async def end_session(request: SessionMetadataRequest):
    """
    End session and clean up resources.
    
    Clears caches and releases session loader.
    """
    try:
        # Clear explanation cache
        cache = ExplanationCache(request.user_id, request.session_id)
        cache.clear_session()
        
        # Release session loader
        release_session(request.user_id, request.session_id)
        
        return {"message": "Session ended and resources cleaned up"}
    except Exception as e:
        logger.error(f"Session end error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/areas/get")
async def get_learning_areas(request: AreasRequest):
    """
    Get weak and strong areas (lazy loaded).
    
    Targets: <500ms
    """
    with TimedResponse("/areas/get", "POST"):
        try:
            loader = get_session_loader(request.user_id, request.session_id)
            profile = loader.get_profile_lazy()
            
            weak_areas = profile.get("weak_areas", [])
            strong_areas = profile.get("strong_areas", [])
            
            return {
                "weak_areas": {"areas": weak_areas[:10], "more_count": max(0, len(weak_areas) - 10)},
                "strong_areas": {"areas": strong_areas[:10], "more_count": max(0, len(strong_areas) - 10)}
            }
        except Exception as e:
            logger.error(f"Learning areas error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/stats")
async def get_performance_stats():
    """
    Get performance statistics (admin endpoint).
    
    Shows response times, cache hit rates, etc.
    """
    try:
        return performance_monitor.get_performance_summary()
    except Exception as e:
        logger.error(f"Performance stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def extract_topic_from_message(message: str) -> Optional[str]:
    """Extract topic name from user message."""
    # Simple heuristic: look for keywords like "teach", "explain", "about"
    keywords = ["teach", "explain", "learn", "about", "topic", "subject"]
    
    message_lower = message.lower()
    for keyword in keywords:
        if keyword in message_lower:
            # Extract text after keyword
            idx = message_lower.find(keyword)
            potential_topic = message[idx + len(keyword):].strip()
            # Take first 50 chars as topic
            if potential_topic:
                return potential_topic.split()[0:3].__str__()
    
    return None
