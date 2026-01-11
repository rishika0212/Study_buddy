"""
Lazy loading system for user state to optimize performance.

Loads only lightweight metadata initially and fetches full state on-demand.
Implements pagination for long conversation histories.

NOTE: session_id has been REMOVED. All state is now per-user, topic-centric.
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from backend.app.config import settings
from backend.app.utils.logger import logger


class UserMetadata:
    """Lightweight user metadata for fast loading."""
    
    def __init__(self, user_id: str):
        """
        Initialize user metadata.
        
        Args:
            user_id: User identifier (session_id is DEPRECATED and removed)
        """
        self.user_id = user_id
        self.metadata_dir = os.path.join(settings.USER_DATA_DIRECTORY, "user_metadata")
        os.makedirs(self.metadata_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.metadata_dir, f"{user_id}_metadata.json")
        self._load()

    def _load(self):
        """Load metadata from disk."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading user metadata: {e}")
                self._initialize_default()
        else:
            self._initialize_default()

    def _initialize_default(self):
        """Initialize default metadata structure."""
        self.data = {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "topic_count": 0,
            "message_count": 0,
            "total_assessment_count": 0,
            "topics_summary": [],  # List of topic names
            "current_topic": None,
            "assessment_state": None
        }
        self._save()

    def _save(self):
        """Save metadata to disk."""
        self.data["last_accessed"] = datetime.now().isoformat()
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.data, f)
        except Exception as e:
            logger.error(f"Error saving session metadata: {e}")

    def get(self, key: str, default=None):
        """Get metadata value."""
        return self.data.get(key, default)

    def update(self, updates: Dict[str, Any]):
        """Update metadata."""
        self.data.update(updates)
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """Get all metadata."""
        return self.data.copy()


class PaginatedConversationHistory:
    """Manages paginated conversation history for lazy loading."""
    
    def __init__(self, user_id: str, page_size: int = 50):
        """
        Initialize paginated conversation history.
        
        Args:
            user_id: User identifier (session_id is DEPRECATED and removed)
            page_size: Number of messages per page
        """
        self.user_id = user_id
        self.page_size = page_size
        self.history_dir = os.path.join(settings.USER_DATA_DIRECTORY, "conversation_pages")
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = os.path.join(self.history_dir, f"{user_id}_history.json")
        self._load()

    def _load(self):
        """Load conversation history."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.history = json.load(f)
            except Exception as e:
                logger.error(f"Error loading conversation history: {e}")
                self.history = []
        else:
            self.history = []

    def _save(self):
        """Save conversation history."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f)
        except Exception as e:
            logger.error(f"Error saving conversation history: {e}")

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.history.append(message)
        self._save()

    def get_page(self, page: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get a page of conversation history.
        
        Args:
            page: Page number (0-indexed)
        
        Returns:
            Tuple of (messages, total_pages)
        """
        total_messages = len(self.history)
        total_pages = (total_messages + self.page_size - 1) // self.page_size
        
        start_idx = page * self.page_size
        end_idx = start_idx + self.page_size
        
        messages = self.history[start_idx:end_idx]
        
        logger.info(f"Retrieved page {page} ({len(messages)} messages, {total_pages} total pages)")
        return messages, total_pages

    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most recent N messages."""
        return self.history[-count:]

    def get_total_count(self) -> int:
        """Get total message count."""
        return len(self.history)

    def clear(self):
        """Clear conversation history."""
        self.history = []
        if os.path.exists(self.history_file):
            os.remove(self.history_file)


class LazyUserLoader:
    """Loads user data on-demand to minimize startup latency."""
    
    def __init__(self, user_id: str):
        """
        Initialize lazy user loader.
        
        Args:
            user_id: User identifier (session_id is DEPRECATED and removed)
        """
        self.user_id = user_id
        self.metadata = UserMetadata(user_id)
        self.history = PaginatedConversationHistory(user_id)
        self._profile_cache = None
        self._topics_cache = None

    def get_user_metadata(self) -> Dict[str, Any]:
        """
        Get lightweight user metadata (fast, no I/O intensive operations).
        
        This returns only essential user information for quick loading.
        """
        return self.metadata.get_all()

    def get_conversation_history(self, page: int = 0, count: int = None) -> Dict[str, Any]:
        """
        Get paginated conversation history on-demand.
        
        Args:
            page: Page number to fetch
            count: Specific count to fetch (overrides pagination)
        
        Returns:
            Dict with messages and pagination info
        """
        if count is not None:
            messages = self.history.get_recent(count)
            return {
                "messages": messages,
                "total": self.history.get_total_count(),
                "returned": len(messages),
                "paginated": False
            }
        else:
            messages, total_pages = self.history.get_page(page)
            return {
                "messages": messages,
                "page": page,
                "total_pages": total_pages,
                "total_messages": self.history.get_total_count(),
                "paginated": True
            }

    def get_profile_lazy(self) -> Dict[str, Any]:
        """
        Get user profile with lazy loading of full data.
        
        Returns only cached profile if already loaded, otherwise loads from disk.
        """
        if self._profile_cache is None:
            try:
                from backend.app.memory.user_profile import UserProfile
                profile = UserProfile(self.user_id)
                self._profile_cache = profile.data
            except Exception as e:
                logger.error(f"Error loading profile: {e}")
                self._profile_cache = {}
        
        return self._profile_cache.copy()

    def get_topics_lazy(self) -> Dict[str, Any]:
        """
        Get topics with lazy loading.
        
        Returns only cached topics if already loaded.
        """
        if self._topics_cache is None:
            profile = self.get_profile_lazy()
            self._topics_cache = profile.get("topics", {})
        
        return self._topics_cache.copy()

    def update_metadata(self, key: str, value: Any):
        """Update a metadata field."""
        self.metadata.update({key: value})

    def invalidate_caches(self):
        """Invalidate all internal caches (when data changes)."""
        self._profile_cache = None
        self._topics_cache = None
        logger.info(f"Invalidated caches for {self.user_id}")


class UserLoaderPool:
    """Pool of lazy user loaders for multiple concurrent users."""
    
    def __init__(self):
        self.loaders: Dict[str, LazyUserLoader] = {}

    def get_loader(self, user_id: str) -> LazyUserLoader:
        """Get or create a user loader."""
        if user_id not in self.loaders:
            self.loaders[user_id] = LazyUserLoader(user_id)
        
        return self.loaders[user_id]

    def release_user(self, user_id: str):
        """Release a user loader (e.g., on logout)."""
        if user_id in self.loaders:
            del self.loaders[user_id]
            logger.info(f"Released user loader: {user_id}")


# Global pool instance
_user_loader_pool = UserLoaderPool()


def get_user_loader(user_id: str) -> LazyUserLoader:
    """Get or create a lazy user loader."""
    return _user_loader_pool.get_loader(user_id)


def release_user(user_id: str):
    """Release a user from the pool."""
    _user_loader_pool.release_user(user_id)
