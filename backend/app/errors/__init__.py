"""
Initialization module for error handling.
"""

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

from backend.app.errors.logging import (
    setup_logging,
    log_error,
    log_retry_attempt,
    log_state_recovery,
)

from backend.app.errors.handlers import (
    register_error_handlers,
)

from backend.app.errors.retry import (
    retry_with_backoff,
    async_retry_with_backoff,
    save_with_retry,
    async_save_with_retry,
    external_service_retry,
    async_external_service_retry,
)

from backend.app.errors.session_state import (
    SessionState,
    SessionValidator,
    SessionStateManager,
)

__all__ = [
    # Exceptions
    "StudyBuddyException",
    "StateCorruptionError",
    "MissingContextError",
    "AssessmentInterruptionError",
    "EvaluationFailureError",
    "StorageFailureError",
    "ValidationError",
    "ExternalServiceError",
    "ConfigurationError",
    # Logging
    "setup_logging",
    "log_error",
    "log_retry_attempt",
    "log_state_recovery",
    # Handlers
    "register_error_handlers",
    # Retry utilities
    "retry_with_backoff",
    "async_retry_with_backoff",
    "save_with_retry",
    "async_save_with_retry",
    "external_service_retry",
    "async_external_service_retry",
    # Session State
    "SessionState",
    "SessionValidator",
    "SessionStateManager",
]
