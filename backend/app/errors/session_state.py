"""
User state management and validation.
Handles state corruption detection and recovery.

NOTE: session_id has been REMOVED. All state is now per-user, topic-centric.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from backend.app.errors import (
    StateCorruptionError,
    MissingContextError,
    log_state_recovery,
)


@dataclass
class UserState:
    """Represents the state of a user."""
    user_id: str
    data: Dict[str, Any]
    created_at: str
    last_updated: str
    read_only: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "data": self.data,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "read_only": self.read_only,
        }


class UserStateValidator:
    """Validates user state for corruption."""
    
    REQUIRED_FIELDS = {"user_id", "data", "created_at"}
    
    @staticmethod
    def validate(state: Dict[str, Any]) -> bool:
        """
        Validate user state.
        
        Args:
            state: User state dictionary
        
        Returns:
            True if valid, False otherwise
        
        Raises:
            MissingContextError: If required fields are missing
            StateCorruptionError: If validation fails
        """
        # Check for required fields
        missing_fields = UserStateValidator.REQUIRED_FIELDS - set(state.keys())
        if missing_fields:
            raise MissingContextError(
                message="User state missing required fields",
                required_fields=list(missing_fields)
            )
        
        # Validate data structure
        if not isinstance(state.get("data"), dict):
            raise StateCorruptionError(
                message="User data is corrupted (invalid format)",
                session_state=state
            )
        
        # Validate IDs are non-empty strings
        if not isinstance(state.get("user_id"), str) or not state["user_id"]:
            raise StateCorruptionError(
                message="Invalid user_id in user state",
                session_state=state
            )
        
        return True
    
    @staticmethod
    def validate_assessment_state(assessment_data: Dict[str, Any]) -> bool:
        """Validate assessment state for completeness."""
        required_fields = {"assessment_id", "question_id", "status"}
        missing = required_fields - set(assessment_data.keys())
        
        if missing:
            raise MissingContextError(
                message="Assessment state incomplete",
                required_fields=list(missing)
            )
        
        # Validate status is valid
        valid_statuses = {"in_progress", "completed", "failed"}
        if assessment_data.get("status") not in valid_statuses:
            raise StateCorruptionError(
                message=f"Invalid assessment status: {assessment_data.get('status')}",
                session_state=assessment_data
            )
        
        return True


class UserStateManager:
    """Manages user state with recovery capabilities."""
    
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        """
        Initialize user state manager.
        
        Args:
            state: Initial user state dictionary
        """
        self.state = state or {}
        self.read_only = False
        self.corruption_detected = False
        
        if self.state:
            try:
                UserStateValidator.validate(self.state)
            except (MissingContextError, StateCorruptionError) as e:
                self.corruption_detected = True
                self.read_only = True
                raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get current user state."""
        return self.state.copy()
    
    def update_state(self, updates: Dict[str, Any]) -> None:
        """
        Update user state.
        
        Args:
            updates: Dictionary of updates to apply
        
        Raises:
            StateCorruptionError: If state is in read-only mode
        """
        if self.read_only:
            raise StateCorruptionError(
                message="Cannot update state in read-only mode",
                session_state=self.state
            )
        
        # Merge updates
        self.state.update(updates)
        self.state["last_updated"] = datetime.utcnow().isoformat()
        
        # Validate after update
        try:
            UserStateValidator.validate(self.state)
        except (MissingContextError, StateCorruptionError) as e:
            self.corruption_detected = True
            self.read_only = True
            raise
    
    def repair_state(self) -> Dict[str, Any]:
        """
        Attempt to repair corrupted state.
        
        Returns:
            Repaired state dictionary
        """
        old_state = self.state.copy()
        repaired = {
            "user_id": self.state.get("user_id", "unknown"),
            "data": self.state.get("data", {}),
            "created_at": self.state.get("created_at", datetime.utcnow().isoformat()),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        # Validate repaired state
        try:
            UserStateValidator.validate(repaired)
            self.state = repaired
            self.read_only = False
            self.corruption_detected = False
            
            log_state_recovery(
                event_type="state_repaired",
                old_state=old_state,
                new_state=self.state,
                action_taken="automatic_repair"
            )
            
            return repaired
        except Exception as e:
            raise StateCorruptionError(
                message="Could not repair corrupted state",
                session_state=old_state
            )
    
    def export_state(self) -> str:
        """Export user state as JSON string."""
        return json.dumps(self.state, indent=2)
    
    def create_checkpoint(self) -> Dict[str, Any]:
        """Create a checkpoint of current state."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "state": self.state.copy(),
            "checksum": self._calculate_checksum(self.state)
        }
    
    def restore_from_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Restore state from a checkpoint."""
        if not self._verify_checkpoint(checkpoint):
            raise StateCorruptionError(
                message="Checkpoint integrity check failed",
                session_state=checkpoint.get("state")
            )
        
        self.state = checkpoint["state"]
        self.read_only = False
        self.corruption_detected = False
    
    @staticmethod
    def _calculate_checksum(data: Dict[str, Any]) -> str:
        """Calculate checksum of state data."""
        import hashlib
        state_json = json.dumps(data, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()
    
    @staticmethod
    def _verify_checkpoint(checkpoint: Dict[str, Any]) -> bool:
        """Verify checkpoint integrity."""
        if not checkpoint or "state" not in checkpoint or "checksum" not in checkpoint:
            return False
        
        expected_checksum = UserStateManager._calculate_checksum(checkpoint["state"])
        return expected_checksum == checkpoint.get("checksum")
    
    def is_read_only(self) -> bool:
        """Check if state is in read-only mode."""
        return self.read_only
    
    def is_corrupted(self) -> bool:
        """Check if corruption has been detected."""
        return self.corruption_detected


# Backward compatibility aliases (DEPRECATED)
SessionState = UserState
SessionValidator = UserStateValidator
SessionStateManager = UserStateManager
