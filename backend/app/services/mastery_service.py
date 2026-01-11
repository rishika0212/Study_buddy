from backend.app.memory.user_profile import UserProfile
from backend.app.utils.logger import logger
import time

class MasteryService:
    """
    CRITICAL ASSESSMENT ENFORCEMENT - MASTERY SERVICE
    
    This service handles all mastery calculations and classification updates.
    ZERO SILENT FAILURES - all operations must complete or raise errors.
    """
    
    # Classification thresholds - GLOBAL CONSTANTS
    WEAK_THRESHOLD = 0.40  # mastery < 0.40 → WEAK
    STRONG_THRESHOLD = 0.40  # mastery >= 0.40 → STRONG
    
    @staticmethod
    def record_assessment_result(user_id: str, topic_name: str, score_type: str, score: float):
        """
        Record assessment result - topic-centric model, no sessions.
        
        CRITICAL ASSESSMENT ENFORCEMENT (MANDATORY):
        
        After EVERY assessed question (MCQ or QnA):
        1. questions_attempted += 1 (ALWAYS incremented)
        2. If correct (score >= 1.0): correct_answers += 1
        3. Recalculate mastery: mastery = correct_answers / questions_attempted
        4. Update classification IMMEDIATELY:
           - questions_attempted == 0: "unassessed"
           - mastery < 0.40: "weak"  
           - mastery >= 0.40: "strong"
        5. Update weak_areas and strong_areas lists
        6. Persist changes to profile
        
        FAILURE RULE: If any step fails, log error and raise exception.
        """
        try:
            profile = UserProfile(user_id)
            topic = profile.add_topic(topic_name)  # Ensure topic exists
        except Exception as e:
            logger.error(f"MasteryService: Failed to load profile for {user_id}: {e}")
            raise
        
        updates = {
            "questions_attempted": topic["questions_attempted"] + 1,
            "last_assessed": time.time()
        }
        
        # MANDATORY: Binary scoring - correct (1.0) or incorrect (0.0)
        # NO PARTIAL CREDIT - this is enforced strictly
        if score >= 1.0:
            updates["correct_answers"] = topic["correct_answers"] + 1
            result_type = "correct"
        else:
            updates["correct_answers"] = topic["correct_answers"]
            result_type = "incorrect"
        
        # Initialize result history if not present
        if "result_history" not in topic:
            topic["result_history"] = []
        
        # Store the result for tracking (last 10 only)
        topic["result_history"].append({
            "result": result_type,
            "timestamp": time.time(),
            "score_type": score_type
        })
        
        # Keep only last 10 results for performance
        if len(topic["result_history"]) > 10:
            topic["result_history"] = topic["result_history"][-10:]
        
        # MANDATORY: Update topic with new values
        # This triggers _update_derived_state which recalculates mastery and classification
        profile.update_topic(topic_name, updates)
        
        # Log the update for verification
        updated_topic = profile.get_topic(topic_name)
        logger.info(
            f"MasteryService: {user_id}/{topic_name} - "
            f"Result: {result_type}, "
            f"Attempted: {updated_topic['questions_attempted']}, "
            f"Correct: {updated_topic['correct_answers']}, "
            f"Mastery: {updated_topic['mastery_score']:.2%}, "
            f"Classification: {updated_topic['classification']}"
        )
        
        # Apply tagging logic AFTER updating mastery
        MasteryService._apply_tagging_logic(profile, topic_name, result_type)
        profile.save()

    @staticmethod
    def _apply_tagging_logic(profile: UserProfile, topic_name: str, result_type: str):
        """
        STRONG / WEAK CLASSIFICATION (GLOBAL) - Applied after EVERY assessed question.
        
        Classification is PURELY based on mastery score, calculated as:
        mastery = correct_answers / questions_attempted
        
        Classification Rules (threshold: 0.40):
        - questions_attempted == 0 → "unassessed" (not in weak or strong)
        - mastery < 0.40 → "weak" (added to weak_areas)
        - mastery >= 0.40 → "strong" (added to strong_areas)
        
        This update MUST reflect instantly in:
        - All Topics sidebar
        - Weak Topics dropdown
        - Strong Topics dropdown
        
        The actual classification is handled by UserProfile._update_derived_state
        when update_topic is called. This method is kept for compatibility.
        """
        topic = profile.get_topic(topic_name)
        if not topic:
            logger.warning(f"MasteryService: Topic {topic_name} not found for classification")
            return
        
        # Classification is already updated by _update_derived_state
        # Log the current classification for verification
        logger.debug(
            f"MasteryService tagging: {topic_name} - "
            f"Classification: {topic.get('classification', 'unknown')}"
        )

    @staticmethod
    def update_after_mcq(user_id: str, topic: str, is_correct: bool):
        """Update mastery after MCQ - topic-centric model, no sessions.
        
        MCQ MODE (MANDATORY):
        1. Evaluate correctness (exact match only)
        2. questions_attempted += 1
        3. If correct: correct_answers += 1
        4. Recalculate mastery: mastery = correct_answers / questions_attempted
        5. Update classification: mastery < 0.40 → WEAK, mastery >= 0.40 → STRONG
        """
        score = 1.0 if is_correct else 0.0
        MasteryService.record_assessment_result(user_id, topic, "mcq", score)

    @staticmethod
    def update_after_qna(user_id: str, topic: str, qna_score: int):
        """
        Update mastery after QnA - topic-centric model, no sessions.
        
        QnA MODE (MANDATORY):
        qna_score: 0-10 based on word-based rubric:
          - Correctness (0-5): Are core concepts correct?
          - Completeness (0-3): Are key points covered?
          - Clarity (0-2): Is the answer understandable?
        
        Scoring interpretation (STRICT - NO PARTIAL CATEGORY):
          - qna_score >= 4 -> CORRECT: Full credit (+1.0 to correct_answers)
          - qna_score < 4  -> INCORRECT: No credit (0 to correct_answers)
        
        Mastery calculation (after EVERY question):
          - questions_attempted += 1
          - If correct: correct_answers += 1
          - mastery = correct_answers / questions_attempted
        
        Classification update (IMMEDIATE):
          - mastery < 0.40 -> topic is WEAK
          - mastery >= 0.40 -> topic is STRONG
          - questions_attempted == 0 -> UNASSESSED
        
        Note: Empty answers, gibberish, or random characters always get score = 0 (INCORRECT)
        """
        # MANDATORY RULE: QnA score >= 4 counts as CORRECT for mastery
        if qna_score >= 4:
            score = 1.0  # CORRECT - full credit (correct_answers += 1)
        else:
            score = 0.0  # INCORRECT - no credit
        MasteryService.record_assessment_result(user_id, topic, "qna", score)
