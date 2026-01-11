import json
import os
import uuid
from backend.app.config import settings

class UserProfile:
    """
    Topic-based memory model - NO SESSIONS.
    All topics are stored per user, not per session.
    Topics are only created when explanations are given.
    """
    def __init__(self, user_id: str, session_id: str = None):
        """
        Initialize user profile. session_id parameter is DEPRECATED and ignored.
        All data is stored per user only.
        """
        self.user_id = user_id
        # Session concept removed - single profile per user
        self.path = os.path.join(settings.USER_DATA_DIRECTORY, f"{user_id}_profile.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                data = json.load(f)
                # Migrate old session-based data if needed
                if "session_id" in data:
                    del data["session_id"]
                return data
        return {
            "mastery": 0.0,
            "topics": {},  # Only topics that have been EXPLAINED
            "weak_areas": [],  # Topics with mastery < 40%
            "strong_areas": [],  # Topics with mastery >= 40%
            "conversation_history": [],
            "mode": "idle",
            "active_challenges": {},
            "assessment_state": None,
            "created_at": None
        }

    def add_topic(self, topic_name: str, parent_topic_id: str = None, explanation_summary: str = None):
        """
        Add a topic ONLY after it has been explained.
        Topics should not be created from casual mentions or questions alone.
        """
        # Validation
        if not (3 <= len(topic_name) <= 50):
            raise ValueError("Topic name must be between 3 and 50 characters.")
        
        import re
        if not re.match(r"^[a-zA-Z0-9 \-&]+$", topic_name):
            raise ValueError("Topic name contains invalid characters.")

        # Case-insensitive duplicate check
        existing_names = {t["name"].lower(): name for name, t in self.data["topics"].items()}
        if topic_name.lower() in existing_names:
            return self.data["topics"][existing_names[topic_name.lower()]]

        topic_id = str(uuid.uuid4())
        self.data["topics"][topic_name] = {
            "topic_id": topic_id,
            "name": topic_name,
            "parent_topic_id": parent_topic_id,
            "explanation_summary": explanation_summary or "",  # Summary of what was explained
            "mastery_score": 0.0000,
            "questions_attempted": 0,
            "correct_answers": 0,
            "last_assessed": None,
            "explanation_cache": None,
            "classification": "unassessed"  # unassessed | weak | strong
        }
        self._update_derived_state(topic_name)
        self.save()
        return self.data["topics"][topic_name]

    def get_topic(self, topic_name: str):
        return self.data["topics"].get(topic_name)

    def get_explanation_cache(self, topic_name: str, depth: str = "level_1"):
        topic = self.get_topic(topic_name)
        if topic and topic.get("explanation_cache"):
            cache = topic["explanation_cache"]
            return cache.get(depth)
        return None

    def set_explanation_cache(self, topic_name: str, depth: str, explanation: str):
        topic = self.get_topic(topic_name)
        if topic is not None:
            if topic.get("explanation_cache") is None:
                topic["explanation_cache"] = {}
            topic["explanation_cache"][depth] = explanation
            self.save()

    def update_topic(self, topic_name: str, updates: dict):
        if topic_name in self.data["topics"]:
            self.data["topics"][topic_name].update(updates)
            self._update_derived_state(topic_name)
            self.save()

    def _update_derived_state(self, topic_name: str):
        """Update derived state for a topic after mastery changes.
        
        Per-Topic Mastery Rules:
        - topic_mastery = correct_answers / questions_attempted
        - If questions_attempted == 0: topic_mastery = 0.0, classification = "unassessed"
        
        Classification Thresholds:
        - topic_mastery < 0.40 → "weak"
        - topic_mastery >= 0.40 → "strong"
        """
        topic = self.data["topics"][topic_name]
        
        # Mastery Calculation: mastery = correct / attempted
        questions_attempted = topic.get("questions_attempted", 0)
        if questions_attempted > 0:
            topic["mastery_score"] = round(topic["correct_answers"] / questions_attempted, 4)
        else:
            topic["mastery_score"] = 0.0
            
        # Classification based on mastery
        # Unassessed: questions_attempted == 0
        # Weak: mastery < 0.40
        # Strong: mastery >= 0.40
        if questions_attempted == 0:
            topic["classification"] = "unassessed"
        elif topic["mastery_score"] < 0.40:
            topic["classification"] = "weak"
        else:
            topic["classification"] = "strong"
            
        # Status Derivation (for backward compatibility)
        topic["status"] = self.get_status_label(topic["mastery_score"], questions_attempted)

        # Update weak/strong areas with IDs based on classification
        topic_id = topic["topic_id"]
        if topic["classification"] == "strong":
            if topic_id not in self.data["strong_areas"]:
                self.data["strong_areas"].append(topic_id)
            if topic_id in self.data["weak_areas"]:
                self.data["weak_areas"].remove(topic_id)
        elif topic["classification"] == "weak":
            if topic_id not in self.data["weak_areas"]:
                self.data["weak_areas"].append(topic_id)
            if topic_id in self.data["strong_areas"]:
                self.data["strong_areas"].remove(topic_id)
        else:
            # Unassessed - remove from both weak and strong areas
            if topic_id in self.data["strong_areas"]:
                self.data["strong_areas"].remove(topic_id)
            if topic_id in self.data["weak_areas"]:
                self.data["weak_areas"].remove(topic_id)

    @staticmethod
    def get_status_label(mastery_score: float, attempted: int):
        """Get status label based on mastery.
        
        Classification Rules:
        - Unassessed: questions_attempted == 0
        - Weak: mastery_score < 0.40
        - Strong: mastery_score >= 0.40
        """
        if attempted == 0:
            return "Unassessed"
        if mastery_score < 0.40:
            return "Weak"
        return "Strong"

    def get_overall_mastery(self):
        """Calculate overall mastery dynamically.
        
        Overall Mastery Rules:
        - NOT stored directly, calculated dynamically
        - overall_mastery = average(topic_mastery of all ASSESSED topics)
        - Unassessed topics (questions_attempted == 0) are EXCLUDED
        - If no topics are assessed: overall_mastery = 0.0
        """
        if not self.data["topics"]:
            return 0.0
        
        # Only include assessed topics (questions_attempted > 0)
        assessed_topics = [
            t for t in self.data["topics"].values() 
            if t.get("questions_attempted", 0) > 0
        ]
        
        # If no topics are assessed, return 0
        if not assessed_topics:
            return 0.0
        
        total_mastery = sum(t["mastery_score"] for t in assessed_topics)
        return round(total_mastery / len(assessed_topics), 4)

    def save(self):
        # Update session level mastery before saving
        self.data["mastery"] = self.get_overall_mastery()
        if self.data.get("created_at") is None:
            import time
            self.data["created_at"] = time.time()
        os.makedirs(settings.USER_DATA_DIRECTORY, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=4)

    def update(self, key, value):
        self.data[key] = value
        self.save()

    def get(self, key):
        return self.data.get(key)

    def get_weak_areas_with_metadata(self, max_display: int = 10):
        """
        Returns weak areas sorted by lowest mastery first, with metadata.
        """
        import time
        
        weak_areas_data = []
        # Handle legacy topics without topic_id by using topic key as fallback
        id_to_topic = {}
        for topic_key, t in self.data["topics"].items():
            topic_id = t.get("topic_id", topic_key)
            id_to_topic[topic_id] = t
        
        for topic_id in self.data["weak_areas"]:
            if topic_id in id_to_topic:
                topic, topic_key = id_to_topic[topic_id]
                mastery_pct = round(topic.get("mastery_score", 0) * 100)
                last_assessed = topic.get("last_assessed")
                
                # Convert timestamp to readable format
                if last_assessed:
                    from datetime import datetime
                    assessed_date = datetime.fromtimestamp(last_assessed).strftime("%b %d, %Y")
                else:
                    assessed_date = "Not yet assessed"
                
                weak_areas_data.append({
                    "name": topic.get("name", topic_key),
                    "mastery_pct": mastery_pct,
                    "last_assessed": assessed_date,
                    "parent_topic_id": topic.get("parent_topic_id")
                })
        
        # Sort by lowest mastery first
        weak_areas_data.sort(key=lambda x: x["mastery_pct"])
        
        # Separate full list and "more" count
        displayed = weak_areas_data[:max_display]
        more_count = len(weak_areas_data) - max_display if len(weak_areas_data) > max_display else 0
        
        return {"areas": displayed, "more_count": more_count}

    def get_strong_areas_with_metadata(self, max_display: int = 10):
        """
        Returns strong areas sorted by highest mastery first, with metadata.
        """
        strong_areas_data = []
        # Handle legacy topics without topic_id by using topic key as fallback
        id_to_topic = {}
        for topic_key, t in self.data["topics"].items():
            topic_id = t.get("topic_id", topic_key)
            id_to_topic[topic_id] = (t, topic_key)  # Store tuple with topic_key for name fallback
        
        for topic_id in self.data["strong_areas"]:
            if topic_id in id_to_topic:
                topic, topic_key = id_to_topic[topic_id]
                mastery_pct = round(topic.get("mastery_score", 0) * 100)
                last_assessed = topic.get("last_assessed")
                
                # Convert timestamp to readable format
                if last_assessed:
                    from datetime import datetime
                    assessed_date = datetime.fromtimestamp(last_assessed).strftime("%b %d, %Y")
                else:
                    assessed_date = "Not yet assessed"
                
                strong_areas_data.append({
                    "name": topic.get("name", topic_key),
                    "mastery_pct": mastery_pct,
                    "mastery_achieved": assessed_date,
                    "parent_topic_id": topic.get("parent_topic_id")
                })
        
        # Sort by highest mastery first
        strong_areas_data.sort(key=lambda x: x["mastery_pct"], reverse=True)
        
        # Separate full list and "more" count
        displayed = strong_areas_data[:max_display]
        more_count = len(strong_areas_data) - max_display if len(strong_areas_data) > max_display else 0
        
        return {"areas": displayed, "more_count": more_count}

    def to_frontend_format(self):
        """Convert profile to frontend format - topic-centric, no sessions."""
        m = self.data.get("mastery", 0.0)
        
        # Get all topics, weak topics, and strong topics
        all_topics = list(self.data.get("topics", {}).keys())
        
        # Map IDs back to names for frontend
        id_to_name = {}
        for topic_key, t in self.data["topics"].items():
            topic_id = t.get("topic_id", topic_key)
            topic_name = t.get("name", topic_key)
            id_to_name[topic_id] = topic_name
        
        strong = [id_to_name[tid] for tid in self.data["strong_areas"] if tid in id_to_name]
        weak = [id_to_name[tid] for tid in self.data["weak_areas"] if tid in id_to_name]
        
        # Calculate overall knowledge level
        knowledge_level = self.get_status_label(m, len(self.data["topics"]))
            
        return {
            "knowledge_level": knowledge_level,
            "mastery_display": f"{round(m * 100)}%",
            "all_topics": all_topics,  # All explained topics
            "strong_topics": strong,    # Topics with mastery >= 40%
            "weak_topics": weak,        # Topics with mastery < 40%
            "known_concepts": strong,   # Backward compatibility
            "weak_areas": weak,         # Backward compatibility
            "mastery": m,
            "topics": self.data.get("topics", {}),
            "mode": self.data.get("mode", "idle"),
            "assessment_state": self.data.get("assessment_state")
        }
