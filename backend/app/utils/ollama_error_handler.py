"""Error handling utilities for OLLAMA integration."""

import asyncio
from typing import Callable, Any, Dict, Optional
from backend.app.utils.logger import logger
from backend.app.config import settings


class OllamaErrorHandler:
    """Unified error handling for OLLAMA operations."""
    
    ERROR_MESSAGES = {
        "connection": {
            "user": "AI service unavailable. Please ensure Ollama is running.",
            "log": "Connection to OLLAMA failed",
            "recovery": "Check if Ollama is running: ollama serve"
        },
        "timeout": {
            "user": "Request timed out. Please try again or check if Ollama is responsive.",
            "log": "OLLAMA request timed out",
            "recovery": f"Increase timeout (current: {settings.OLLAMA_TIMEOUT}s) or check system load"
        },
        "model_not_found": {
            "user": "Model not available. Please pull the required model.",
            "log": "Requested model not found in OLLAMA",
            "recovery": "Run: ollama pull <model_name>"
        },
        "invalid_json": {
            "user": "Unable to process response. Please try again.",
            "log": "Invalid JSON in OLLAMA response",
            "recovery": "Check prompt formatting or model's JSON output capabilities"
        },
        "rate_limited": {
            "user": "Too many requests. Please wait a moment and try again.",
            "log": "OLLAMA rate limit exceeded",
            "recovery": "Implement request queuing or reduce concurrent requests"
        }
    }
    
    @staticmethod
    def get_user_message(error_type: str) -> str:
        """Get user-friendly error message."""
        return OllamaErrorHandler.ERROR_MESSAGES.get(
            error_type, {}
        ).get("user", "An unexpected error occurred. Please try again.")
    
    @staticmethod
    def get_recovery_hint(error_type: str) -> str:
        """Get recovery instructions."""
        return OllamaErrorHandler.ERROR_MESSAGES.get(
            error_type, {}
        ).get("recovery", "Try again later")
    
    @staticmethod
    def log_error(error_type: str, context: str = "", details: str = ""):
        """Log error with context."""
        message = OllamaErrorHandler.ERROR_MESSAGES.get(
            error_type, {}
        ).get("log", "Unknown error")
        
        if context:
            message = f"{context}: {message}"
        if details:
            message = f"{message} - {details}"
        
        logger.error(message)


async def handle_ollama_call(
    func: Callable,
    *args,
    fallback: Optional[Any] = None,
    error_context: str = "",
    **kwargs
) -> Any:
    """Execute OLLAMA call with comprehensive error handling.
    
    Args:
        func: Async function to execute
        fallback: Fallback value if function fails
        error_context: Context for error logging
        args: Positional arguments for func
        kwargs: Keyword arguments for func
    
    Returns:
        Function result or fallback
    """
    try:
        return await func(*args, **kwargs)
    except TimeoutError as e:
        OllamaErrorHandler.log_error("timeout", error_context, str(e))
        if fallback is not None:
            return fallback
        raise
    except ConnectionError as e:
        OllamaErrorHandler.log_error("connection", error_context, str(e))
        if fallback is not None:
            return fallback
        raise
    except ValueError as e:
        if "model" in str(e).lower():
            OllamaErrorHandler.log_error("model_not_found", error_context, str(e))
        else:
            OllamaErrorHandler.log_error("invalid_json", error_context, str(e))
        if fallback is not None:
            return fallback
        raise
    except Exception as e:
        OllamaErrorHandler.log_error("generic", error_context, str(e))
        if fallback is not None:
            return fallback
        raise


def create_fallback_response(
    task_type: str,
    topic: Optional[str] = None,
    extra_info: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create fallback response for failed OLLAMA calls.
    
    Args:
        task_type: Type of task (explanation, mcq, qna, etc.)
        topic: Topic name if applicable
        extra_info: Additional info to include
    
    Returns:
        Fallback response dict
    """
    fallback_responses = {
        "explanation": {
            "content": "I'm temporarily unable to provide an explanation. Please try again in a moment.",
            "error": True,
            "recovery": "Ensure Ollama is running"
        },
        "mcq": {
            "question": "Unable to generate question at this time.",
            "options": {"A": "Retry", "B": "Retry", "C": "Retry", "D": "Retry"},
            "error": True,
            "recovery": "Check Ollama status"
        },
        "qna": {
            "question": f"Please explain the key concepts of {topic or 'this topic'} in your own words.",
            "error": True,
            "recovery": "Check Ollama status"
        },
        "evaluation": {
            "result": "error",
            "feedback": "Unable to evaluate at this time. Please try again.",
            "error": True,
            "recovery": "Check Ollama status"
        }
    }
    
    response = fallback_responses.get(task_type, {"error": True})
    if extra_info:
        response.update(extra_info)
    
    return response
