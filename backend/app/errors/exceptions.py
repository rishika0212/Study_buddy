"""
Custom exception classes for Study Buddy error handling.
Implements comprehensive error categorization and recovery protocols.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime


class StudyBuddyException(Exception):
    """Base exception class for all Study Buddy errors."""
    
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
        }


# STATE CORRUPTION ERRORS
class StateCorruptionError(StudyBuddyException):
    """Raised when session/profile state validation fails."""
    
    def __init__(self, message: str, session_state: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="STATE_CORRUPTION",
            details={"session_state": session_state or {}}
        )
        self.session_state = session_state
        self.read_only_mode = True


# MISSING CONTEXT ERRORS
class MissingContextError(StudyBuddyException):
    """Raised when required data is not available."""
    
    def __init__(self, message: str, required_fields: Optional[list] = None):
        super().__init__(
            message=message,
            error_code="MISSING_CONTEXT",
            details={"required_fields": required_fields or []}
        )
        self.required_fields = required_fields or []


# ASSESSMENT ERRORS
class AssessmentInterruptionError(StudyBuddyException):
    """Raised when assessment is interrupted mid-session."""
    
    def __init__(self, message: str, assessment_id: str, progress: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="ASSESSMENT_INTERRUPTION",
            details={"assessment_id": assessment_id, "progress": progress or {}}
        )
        self.assessment_id = assessment_id
        self.progress = progress


class EvaluationFailureError(StudyBuddyException):
    """Raised when LLM evaluation/Ollama call fails."""
    
    def __init__(self, message: str, question_id: Optional[str] = None, retry_count: int = 0):
        super().__init__(
            message=message,
            error_code="EVALUATION_FAILURE",
            details={"question_id": question_id, "retry_count": retry_count}
        )
        self.question_id = question_id
        self.retry_count = retry_count
        self.evaluation_failed = True  # Mark for special handling


# STORAGE ERRORS
class StorageFailureError(StudyBuddyException):
    """Raised when storage/database operations fail."""
    
    def __init__(self, message: str, operation: str, retry_count: int = 0):
        super().__init__(
            message=message,
            error_code="STORAGE_FAILURE",
            details={"operation": operation, "retry_count": retry_count}
        )
        self.operation = operation
        self.retry_count = retry_count
        self.requires_rollback = True


# VALIDATION ERRORS
class ValidationError(StudyBuddyException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str, value: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": str(value)}
        )
        self.field = field
        self.value = value


# CONNECTION/EXTERNAL SERVICE ERRORS
class ExternalServiceError(StudyBuddyException):
    """Raised when external service (Ollama, LLM) fails."""
    
    def __init__(self, message: str, service_name: str, retry_count: int = 0):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service_name": service_name, "retry_count": retry_count}
        )
        self.service_name = service_name
        self.retry_count = retry_count


# CONFIGURATION ERRORS
class ConfigurationError(StudyBuddyException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: str):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key}
        )
        self.config_key = config_key
