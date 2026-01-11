import time
from typing import Dict, Any, List, Optional, Tuple
from backend.app.utils.logger import logger

class StateValidationService:
    @staticmethod
    def validate_profile(profile_data: Dict[str, Any], history: List[Any]) -> Tuple[bool, List[str]]:
        errors = []
        
        # Check 1: Reference Integrity
        topics = profile_data.get("topics", {})
        topic_ids = {t["topic_id"] for t in topics.values()}
        
        for area in ["weak_areas", "strong_areas"]:
            for tid in profile_data.get(area, []):
                if tid not in topic_ids:
                    errors.append(f"Orphaned topic ID {tid} found in {area}")

        # Check 2: Mastery Accuracy & Check 4: Counter Logic
        for name, topic in topics.items():
            attempted = topic.get("questions_attempted", 0)
            correct = topic.get("correct_answers", 0)
            stored_mastery = topic.get("mastery_score", 0.0)
            
            if attempted < 0:
                errors.append(f"Negative attempted count for topic {name}")
            if correct < 0:
                errors.append(f"Negative correct count for topic {name}")
            if correct > attempted:
                errors.append(f"Correct answers ({correct}) exceed attempted ({attempted}) for topic {name}")
            
            if attempted > 0:
                expected_mastery = round(correct / attempted, 4)
                if abs(stored_mastery - expected_mastery) > 0.0001:
                    errors.append(f"Mastery mismatch for topic {name}: stored {stored_mastery}, expected {expected_mastery}")
            elif stored_mastery != 0.0:
                 errors.append(f"Mastery should be 0.0 for unattempted topic {name}")

        # Check 3: Assessment Consistency
        asst = profile_data.get("assessment_state")
        if asst:
            total = asst.get("total_questions", 0)
            current = asst.get("current_question_index", 0)
            if current >= total and total > 0:
                errors.append(f"Assessment index {current} out of bounds for total {total}")
            
            user_answers = asst.get("user_answers", {})
            # If we had evaluations stored per question, we'd check them here
            # For now, let's check if all answered questions have entries
            for idx in asst.get("answered_questions", []):
                if str(idx) not in user_answers and idx not in user_answers:
                    errors.append(f"Answered question {idx} missing evaluation/answer data")

        # Check 5: Timestamp Sequence
        # Note: History format from FileChatMessageHistory uses "data": {"content": ..., "additional_kwargs": {"timestamp": ...}} 
        # or we might need to add it ourselves.
        last_ts = 0
        for i, msg in enumerate(history):
            # msg is likely a BaseMessage or dict depending on how it's passed
            ts = 0
            if isinstance(msg, dict):
                ts = msg.get("data", {}).get("additional_kwargs", {}).get("timestamp", 0)
            else:
                ts = getattr(msg, "additional_kwargs", {}).get("timestamp", 0)
            
            if ts != 0:
                if ts < last_ts:
                    errors.append(f"Out-of-order timestamp at message {i}")
                last_ts = ts

        if errors:
            logger.error(f"Validation Failure: {errors}")
            logger.debug(f"Full State: {profile_data}")
            return False, errors
            
        return True, []
