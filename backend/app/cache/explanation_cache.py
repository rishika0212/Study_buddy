"""
Explanation caching system for performance optimization.

Caches generated explanations per user to avoid regenerating the same content.
Supports cache invalidation and rephrasing on demand.

NOTE: session_id has been REMOVED. All caching is now per-user, topic-centric.
"""

import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from backend.app.config import settings
from backend.app.utils.logger import logger


class ExplanationCache:
    """Manages cached explanations for topics for a user."""
    
    def __init__(self, user_id: str):
        """
        Initialize explanation cache for a user.
        
        Args:
            user_id: User identifier (session_id is DEPRECATED and removed)
        """
        self.user_id = user_id
        self.cache_dir = os.path.join(settings.USER_DATA_DIRECTORY, "explanation_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, f"{user_id}_explanations.json")
        self.cache_ttl_hours = 24  # Cache expires after 24 hours
        self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
                    logger.info(f"Loaded explanation cache for {self.user_id}")
            except Exception as e:
                logger.error(f"Error loading explanation cache: {e}")
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Error saving explanation cache: {e}")

    def _is_cache_valid(self, cached_item: Dict[str, Any]) -> bool:
        """Check if cached item has expired."""
        if "timestamp" not in cached_item:
            return False
        
        cached_time = datetime.fromisoformat(cached_item["timestamp"])
        expiry_time = cached_time + timedelta(hours=self.cache_ttl_hours)
        return datetime.now() < expiry_time

    def get(self, topic: str, depth: str = "level_1") -> Optional[str]:
        """
        Retrieve cached explanation for a topic.
        
        Args:
            topic: Topic name
            depth: Explanation depth level (level_1, level_2, level_3, beginner, intermediate, advanced)
        
        Returns:
            Cached explanation or None if not found/expired
        """
        cache_key = f"{topic}:{depth}"
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if self._is_cache_valid(cached_item):
                logger.info(f"Cache hit for {cache_key}")
                return cached_item["explanation"]
            else:
                # Remove expired cache
                del self.cache[cache_key]
                self._save_cache()
                logger.info(f"Cache expired for {cache_key}")
        
        return None

    def set(self, topic: str, explanation: str, depth: str = "level_1", metadata: Dict[str, Any] = None):
        """
        Cache an explanation for a topic.
        
        Args:
            topic: Topic name
            explanation: The explanation text to cache
            depth: Explanation depth level
            metadata: Optional metadata (model used, generation time, etc.)
        """
        cache_key = f"{topic}:{depth}"
        
        self.cache[cache_key] = {
            "explanation": explanation,
            "timestamp": datetime.now().isoformat(),
            "depth": depth,
            "metadata": metadata or {}
        }
        
        self._save_cache()
        logger.info(f"Cached explanation for {cache_key}")

    def invalidate(self, topic: str, depth: Optional[str] = None):
        """
        Invalidate cached explanations for a topic.
        
        Args:
            topic: Topic name
            depth: Specific depth level to invalidate, or None to invalidate all depths
        """
        if depth is None:
            # Invalidate all depths for this topic
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{topic}:")]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Invalidated all explanations for {topic}")
        else:
            cache_key = f"{topic}:{depth}"
            if cache_key in self.cache:
                del self.cache[cache_key]
                logger.info(f"Invalidated explanation for {cache_key}")
        
        self._save_cache()

    def clear_user_cache(self):
        """Clear all explanations for this user."""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info(f"Cleared explanation cache for {self.user_id}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the current cache."""
        return {
            "total_cached_items": len(self.cache),
            "items": [{"key": k, "depth": v.get("depth"), "cached_at": v.get("timestamp")} for k, v in self.cache.items()]
        }
