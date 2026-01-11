"""
Error handlers and middleware for Study Buddy.
Implements global error handling and recovery protocols.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional, Dict, Any

from backend.app.errors.exceptions import (
    StudyBuddyException,
    StateCorruptionError,
    MissingContextError,
    AssessmentInterruptionError,
    EvaluationFailureError,
    StorageFailureError,
    ValidationError,
    ExternalServiceError,
    ConfigurationError,
)
from backend.app.errors.logging import log_error


async def state_corruption_handler(request: Request, exc: StateCorruptionError):
    """Handle state corruption errors with read-only mode activation."""
    log_error(
        exc,
        error_type="STATE_CORRUPTION",
        user_action=f"{request.method} {request.url.path}",
        session_state=exc.session_state
    )
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": "Session inconsistent. Options: [Repair/New/Export]",
            "details": exc.to_dict(),
            "recovery_options": ["repair_session", "create_new", "export_data"]
        }
    )


async def missing_context_handler(request: Request, exc: MissingContextError):
    """Handle missing context errors by prompting for required fields."""
    log_error(
        exc,
        error_type="MISSING_CONTEXT",
        user_action=f"{request.method} {request.url.path}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": "Missing required context",
            "required_fields": exc.required_fields,
            "details": exc.to_dict()
        }
    )


async def assessment_interruption_handler(request: Request, exc: AssessmentInterruptionError):
    """Handle incomplete assessment sessions."""
    log_error(
        exc,
        error_type="ASSESSMENT_INTERRUPTION",
        user_action=f"{request.method} {request.url.path}",
        additional_context={"assessment_id": exc.assessment_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": f"Incomplete assessment: {exc.progress.get('answered', 0)}/{exc.progress.get('total', 0)} answered",
            "assessment_id": exc.assessment_id,
            "progress": exc.progress,
            "options": ["resume", "start_fresh", "discard"],
            "details": exc.to_dict()
        }
    )


async def evaluation_failure_handler(request: Request, exc: EvaluationFailureError):
    """Handle LLM evaluation failures - allow retry without counting toward mastery."""
    log_error(
        exc,
        error_type="EVALUATION_FAILURE",
        user_action=f"{request.method} {request.url.path}",
        additional_context={"question_id": exc.question_id, "retry_count": exc.retry_count}
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": "Evaluation service unavailable. Please try again. (Not counted toward mastery)",
            "question_id": exc.question_id,
            "evaluation_failed": True,
            "retry_count": exc.retry_count,
            "details": exc.to_dict()
        }
    )


async def storage_failure_handler(request: Request, exc: StorageFailureError):
    """Handle storage failures with retry information."""
    log_error(
        exc,
        error_type="STORAGE_FAILURE",
        user_action=f"{request.method} {request.url.path}",
        additional_context={"operation": exc.operation, "retry_count": exc.retry_count}
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": f"Unable to save your progress. Retrying... (Attempt {exc.retry_count}/3)",
            "operation": exc.operation,
            "retry_count": exc.retry_count,
            "requires_rollback": True,
            "details": exc.to_dict()
        }
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle input validation errors."""
    log_error(
        exc,
        error_type="VALIDATION_ERROR",
        user_action=f"{request.method} {request.url.path}",
        additional_context={"field": exc.field}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": f"Please enter a valid {exc.field}.",
            "field": exc.field,
            "details": exc.to_dict()
        }
    )


async def external_service_error_handler(request: Request, exc: ExternalServiceError):
    """Handle external service failures (Ollama, LLM)."""
    log_error(
        exc,
        error_type="EXTERNAL_SERVICE_ERROR",
        user_action=f"{request.method} {request.url.path}",
        additional_context={"service_name": exc.service_name, "retry_count": exc.retry_count}
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": f"Connection lost to {exc.service_name}. Reconnecting...",
            "service_name": exc.service_name,
            "retry_count": exc.retry_count,
            "details": exc.to_dict()
        }
    )


async def configuration_error_handler(request: Request, exc: ConfigurationError):
    """Handle configuration errors."""
    log_error(
        exc,
        error_type="CONFIGURATION_ERROR",
        user_action=f"{request.method} {request.url.path}",
        additional_context={"config_key": exc.config_key}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_id": exc.error_id,
            "error_code": exc.error_code,
            "message": "System configuration error. Please contact support.",
            "config_key": exc.config_key,
            "details": exc.to_dict()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    error_id = str(id(exc))
    log_error(
        exc,
        error_type="UNEXPECTED_ERROR",
        user_action=f"{request.method} {request.url.path}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_id": error_id,
            "message": "Something went wrong. Please try again.",
            "error_code": "INTERNAL_ERROR"
        }
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app."""
    app.add_exception_handler(StateCorruptionError, state_corruption_handler)
    app.add_exception_handler(MissingContextError, missing_context_handler)
    app.add_exception_handler(AssessmentInterruptionError, assessment_interruption_handler)
    app.add_exception_handler(EvaluationFailureError, evaluation_failure_handler)
    app.add_exception_handler(StorageFailureError, storage_failure_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(ExternalServiceError, external_service_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)
    app.add_exception_handler(StudyBuddyException, generic_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
