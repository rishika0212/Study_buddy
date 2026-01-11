"""
Error logging and monitoring for Study Buddy.
Implements structured logging for all error events.
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
import traceback
import sys
import os


class StructuredJsonFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        # Add any extra fields passed to the logger
        if hasattr(record, 'error_data'):
            log_data.update(record.error_data)
        
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """
    Set up structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("study_buddy")
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = StructuredJsonFormatter()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with JSON formatting
    file_handler = logging.FileHandler(f"{log_dir}/study_buddy.log")
    file_formatter = StructuredJsonFormatter()
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error-specific log file
    error_handler = logging.FileHandler(f"{log_dir}/errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger


def log_error(
    error: Exception,
    error_type: str,
    user_action: str,
    session_state: Optional[Dict[str, Any]] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """
    Log an error with full context.
    
    Args:
        error: The exception that occurred
        error_type: Category of error
        user_action: The action that triggered the error
        session_state: Current session state (if applicable)
        additional_context: Any additional context to log
    """
    logger = logging.getLogger("study_buddy")
    
    error_id = getattr(error, 'error_id', None)
    
    log_data = {
        "error_data": {
            "error_id": error_id,
            "error_type": error_type,
            "error_class": error.__class__.__name__,
            "user_action": user_action,
            "session_state": session_state or {},
            "additional_context": additional_context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    # Create a log record with extra data
    record = logger.makeRecord(
        name="study_buddy",
        level=logging.ERROR,
        fn="",
        lno=0,
        msg=str(error),
        args=(),
        exc_info=None
    )
    record.error_data = log_data["error_data"]
    
    logger.handle(record)


def log_retry_attempt(
    operation: str,
    attempt: int,
    max_attempts: int,
    error: Optional[Exception] = None
):
    """Log a retry attempt for a failed operation."""
    logger = logging.getLogger("study_buddy")
    
    message = f"Retry attempt {attempt}/{max_attempts} for operation: {operation}"
    if error:
        message += f" - Last error: {str(error)}"
    
    logger.warning(message)


def log_state_recovery(
    event_type: str,
    old_state: Dict[str, Any],
    new_state: Optional[Dict[str, Any]] = None,
    action_taken: str = ""
):
    """Log state recovery and repair operations."""
    logger = logging.getLogger("study_buddy")
    
    log_data = {
        "error_data": {
            "event_type": event_type,
            "old_state": old_state,
            "new_state": new_state,
            "action_taken": action_taken,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    record = logger.makeRecord(
        name="study_buddy",
        level=logging.WARNING,
        fn="",
        lno=0,
        msg=f"State recovery event: {event_type}",
        args=(),
        exc_info=None
    )
    record.error_data = log_data["error_data"]
    
    logger.handle(record)


# Initialize logger on import
logger = setup_logging()
