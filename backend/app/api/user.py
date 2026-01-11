from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.memory.user_profile import UserProfile
from backend.app.errors import (
    ValidationError,
    MissingContextError,
    StorageFailureError,
    log_error,
    async_save_with_retry,
)
import os
import shutil
import uuid
from backend.app.config import settings

router = APIRouter()

# SESSION ENDPOINTS REMOVED - System is now topic-based only

@router.get("/user/{user_id}/profile")
async def get_profile(user_id: str, session_id: str = None):
    """
    Get user profile - topic-centric model.
    session_id parameter is DEPRECATED and ignored.
    """
    if not user_id:
        raise ValidationError("user_id is required", field="user_id")
    
    try:
        profile = UserProfile(user_id)
        return profile.to_frontend_format()
    except Exception as e:
        log_error(
            e,
            error_type="GET_PROFILE_ERROR",
            user_action=f"GET /api/user/{user_id}/profile"
        )
        raise

@router.get("/user/{user_id}/topics")
async def get_all_topics(user_id: str):
    """
    Get all explained topics for a user.
    Returns topics organized by classification (all, weak, strong).
    """
    if not user_id:
        raise ValidationError("user_id is required", field="user_id")
    
    try:
        profile = UserProfile(user_id)
        topics_data = profile.data.get("topics", {})
        
        all_topics = []
        weak_topics = []
        strong_topics = []
        
        for topic_name, topic_info in topics_data.items():
            topic_entry = {
                "name": topic_name,
                "mastery_score": topic_info.get("mastery_score", 0),
                "questions_attempted": topic_info.get("questions_attempted", 0),
                "correct_answers": topic_info.get("correct_answers", 0),
                "classification": topic_info.get("classification", "unassessed"),
                "explanation_summary": topic_info.get("explanation_summary", "")
            }
            all_topics.append(topic_entry)
            
            if topic_info.get("classification") == "weak":
                weak_topics.append(topic_entry)
            elif topic_info.get("classification") == "strong":
                strong_topics.append(topic_entry)
        
        return {
            "all_topics": all_topics,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics
        }
    except Exception as e:
        log_error(
            e,
            error_type="GET_TOPICS_ERROR",
            user_action=f"GET /api/user/{user_id}/topics"
        )
        raise

@router.post("/user/{user_id}/reset")
async def reset_memory(user_id: str):
    """Reset user memory - removes all topic data."""
    if not user_id:
        raise ValidationError("user_id is required", field="user_id")
    
    try:
        if os.path.exists(settings.USER_DATA_DIRECTORY):
            for filename in os.listdir(settings.USER_DATA_DIRECTORY):
                if filename.startswith(f"{user_id}_"):
                    try:
                        os.remove(os.path.join(settings.USER_DATA_DIRECTORY, filename))
                    except Exception as e:
                        log_error(
                            e,
                            error_type="DELETE_FILE_ERROR",
                            user_action=f"POST /api/user/{user_id}/reset",
                            additional_context={"filename": filename}
                        )
                        continue
        
        return {"message": "User memory reset successfully"}
    except Exception as e:
        log_error(
            e,
            error_type="RESET_MEMORY_ERROR",
            user_action=f"POST /api/user/{user_id}/reset"
        )
        raise

@router.get("/user/{user_id}/history")
async def get_history(user_id: str):
    """Get conversation history for a user."""
    if not user_id:
        raise ValidationError("user_id is required", field="user_id")
    
    try:
        from backend.app.memory.conversation import get_conversation_memory
        memory = get_conversation_memory(user_id)
        chat_history_vars = memory.load_memory_variables({})
        messages = chat_history_vars.get("chat_history", [])
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "text": msg.content,
                "sender": "user" if msg.type == "human" else "ai",
                "timestamp": None
            })
        return formatted_messages
    except Exception as e:
        log_error(
            e,
            error_type="GET_HISTORY_ERROR",
            user_action=f"GET /api/user/{user_id}/history"
        )
        raise


@router.post("/user/{user_id}/clear-history")
async def clear_history(user_id: str):
    """
    Clear chat conversation history for a user.
    
    This ONLY clears the chat messages. It does NOT affect:
    - Topics (all_topics, weak_topics, strong_topics)
    - Mastery scores
    - Assessment history
    - User profile data
    
    Use this for "New Session" functionality.
    """
    if not user_id:
        raise ValidationError("user_id is required", field="user_id")
    
    try:
        history_path = os.path.join(settings.USER_DATA_DIRECTORY, f"{user_id}_history.json")
        
        # Clear the history file by writing an empty array
        if os.path.exists(history_path):
            with open(history_path, 'w') as f:
                f.write('[]')
        
        return {"message": "Chat history cleared successfully", "topics_preserved": True}
    except Exception as e:
        log_error(
            e,
            error_type="CLEAR_HISTORY_ERROR",
            user_action=f"POST /api/user/{user_id}/clear-history"
        )
        raise
