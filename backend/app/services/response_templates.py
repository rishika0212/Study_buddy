"""
Response Templates Service

Provides consistent, template-based responses for specific scenarios in Study Buddy.
Uses exact wording and structure to ensure consistency across the application.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import uuid


class TemplateType(Enum):
    TOPIC_NOT_IN_SESSION = 1
    ASSESSMENT_VIA_CHAT = 2
    MISSING_CONTEXT = 3
    UNASSESSED_TOPIC = 4
    CORRUPTED_SESSION = 5
    OFF_TOPIC = 6
    USER_FRUSTRATION = 7
    SUCCESS_MILESTONE = 8
    CLARIFICATION_NEEDED = 9
    ASSESSMENT_COMPLETE = 10


class ResponseTemplates:
    """Service for managing and rendering response templates."""

    @staticmethod
    def topic_not_in_session(topic_name: str) -> Dict[str, Any]:
        """
        Trigger: User mentions topic not added to session
        Note: This template is deprecated - we should just explain topics directly
        without asking for confirmation.
        """
        # Return None to indicate no template should be used - just explain directly
        return None

    @staticmethod
    def assessment_via_chat(topic_name: str) -> Dict[str, Any]:
        """
        Trigger: User tries starting assessment through chat
        """
        return {
            "content": f"""To start an assessment, please:
1. Click "Assessments" in the sidebar
2. Choose "MCQ" or "QnA"
3. Select the topic: {topic_name}
4. Enter number of questions (1-50)
5. Click "Start Assessment"

I cannot start assessments through chat messages to ensure proper setup.""",
            "template_type": TemplateType.ASSESSMENT_VIA_CHAT.name,
            "requires_choice": False
        }

    @staticmethod
    def missing_context() -> Dict[str, Any]:
        """
        Trigger: User's message is ambiguous without context
        """
        return {
            "content": """I don't have enough context to answer that accurately.

Could you:
- Specify which topic you're referring to?
- Rephrase with more detail?
- Or, let me know if you'd like to start a new topic.""",
            "template_type": TemplateType.MISSING_CONTEXT.name,
            "requires_choice": False
        }

    @staticmethod
    def unassessed_topic(topic_name: str, mastery: float = 0.0) -> Dict[str, Any]:
        """
        Trigger: User asks about mastery with 0 questions attempted
        """
        return {
            "content": f"""{topic_name} - {int(mastery * 100)}% mastery
Status: Unassessed 🔵

You haven't attempted any questions for this topic yet.

Would you like to:
1. Learn the basics first (I'll explain the concept)
2. Test your current knowledge (Start assessment)

Choose 1 or 2.""",
            "template_type": TemplateType.UNASSESSED_TOPIC.name,
            "requires_choice": True,
            "choices": ["1", "2"],
            "topic_name": topic_name,
            "mastery": mastery
        }

    @staticmethod
    def corrupted_session(error_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger: State validation fails
        """
        if error_id is None:
            error_id = str(uuid.uuid4())[:8]
        
        return {
            "content": f"""⚠️ Session Data Issue Detected

Your session data appears inconsistent.

Options:
1. Attempt automatic repair
2. Start a new session (current archived)
3. Export data for support

Which would you like to do?

Error ID: {error_id} - Logged for investigation.""",
            "template_type": TemplateType.CORRUPTED_SESSION.name,
            "requires_choice": True,
            "choices": ["1", "2", "3"],
            "error_id": error_id
        }

    @staticmethod
    def off_topic() -> Dict[str, Any]:
        """
        Trigger: User engages in non-educational chat
        """
        return {
            "content": """I'm Study Buddy, focused on helping you learn effectively.

I can:
- Explain topics you want to learn
- Assess your understanding
- Track your progress
- Identify weak areas

Would you like to add a topic to your session, or is there something else I can help you learn?""",
            "template_type": TemplateType.OFF_TOPIC.name,
            "requires_choice": False
        }

    @staticmethod
    def user_frustration(state_facts: str, highlight_progress: str, offer_options: str) -> Dict[str, Any]:
        """
        Trigger: User expresses difficulty or repeated failures
        """
        return {
            "content": f"""I can see this is challenging. Let's break it down:

Current situation: {state_facts}
What's working: {highlight_progress}
What we can adjust: {offer_options}

You're making progress. Would you like to:
1. Review weaker areas with focused explanations
2. Take a break and come back later
3. Try a different topic to build confidence""",
            "template_type": TemplateType.USER_FRUSTRATION.name,
            "requires_choice": True,
            "choices": ["1", "2", "3"]
        }

    @staticmethod
    def success_milestone(milestone: str, specific_accomplishment: str, significance: str) -> Dict[str, Any]:
        """
        Trigger: User achieves 70%+ mastery, 90%+ mastery, or other milestone
        """
        return {
            "content": f"""🎉 Congratulations!

You've achieved {milestone}: {specific_accomplishment}

This means: {significance}

Keep up the excellent work!""",
            "template_type": TemplateType.SUCCESS_MILESTONE.name,
            "requires_choice": False
        }

    @staticmethod
    def clarification_needed(options: List[str]) -> Dict[str, Any]:
        """
        Trigger: User intent is ambiguous
        Expects: options = ["Option 1 description", "Option 2 description", "Option 3 description"]
        """
        if len(options) < 2:
            raise ValueError("At least 2 options required")
        
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        
        return {
            "content": f"""I want to help, but I need clarification.

Did you want to:
{options_text}

Please choose a number.""",
            "template_type": TemplateType.CLARIFICATION_NEEDED.name,
            "requires_choice": True,
            "choices": [str(i+1) for i in range(len(options))]
        }

    @staticmethod
    def assessment_complete(
        topic_name: str,
        total_questions: int,
        correct_answers: int,
        old_mastery: float,
        new_mastery: float,
        personalized_insight: str
    ) -> Dict[str, Any]:
        """
        Trigger: User finishes full assessment
        """
        percentage = round((correct_answers / total_questions * 100)) if total_questions > 0 else 0
        
        # Determine status badge
        if new_mastery >= 0.9:
            status_badge = "Expert 🌟"
        elif new_mastery >= 0.7:
            status_badge = "Proficient ✅"
        elif new_mastery >= 0.5:
            status_badge = "Intermediate 🟡"
        else:
            status_badge = "Beginner 🔵"
        
        old_mastery_pct = round(old_mastery * 100)
        new_mastery_pct = round(new_mastery * 100)
        
        return {
            "content": f"""Assessment Complete ✓

Topic: {topic_name}
Questions: {total_questions}
Correct: {correct_answers} ({percentage}%)
Updated Mastery: {old_mastery_pct}% → {new_mastery_pct}%
Status: {status_badge}

{personalized_insight}

Next steps:
- Review incorrect questions
- Start new assessment
- Study weak areas""",
            "template_type": TemplateType.ASSESSMENT_COMPLETE.name,
            "requires_choice": False,
            "metrics": {
                "topic_name": topic_name,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "percentage": percentage,
                "old_mastery": old_mastery,
                "new_mastery": new_mastery,
                "old_mastery_pct": old_mastery_pct,
                "new_mastery_pct": new_mastery_pct,
                "status": status_badge
            }
        }


class TemplateSelector:
    """Determines which template to use based on scenario triggers."""

    @staticmethod
    def select_template(observation: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply selection logic to determine if a template applies.
        
        Args:
            observation: Current state observation from agent
            context: Additional context about intent and user state
        
        Returns:
            Template dict if applicable, None otherwise
        """
        
        # 1. Check for corrupted session (highest priority)
        if context.get("validation_failed"):
            return ResponseTemplates.corrupted_session(context.get("error_id"))
        
        # 2. Check for topic not in session
        if context.get("template_trigger") == "topic_not_in_session":
            topic_name = context.get("topic_name", "that topic")
            return ResponseTemplates.topic_not_in_session(topic_name)
        
        # 3. Check for assessment via chat attempt
        if context.get("template_trigger") == "assessment_via_chat":
            topic_name = context.get("topic_name", "your selected topic")
            return ResponseTemplates.assessment_via_chat(topic_name)
        
        # 4. Check for missing context
        if context.get("template_trigger") == "missing_context":
            return ResponseTemplates.missing_context()
        
        # 5. Check for unassessed topic
        if context.get("template_trigger") == "unassessed_topic":
            topic_name = context.get("topic_name", "This topic")
            mastery = context.get("mastery", 0.0)
            return ResponseTemplates.unassessed_topic(topic_name, mastery)
        
        # 6. Check for off-topic chat
        if context.get("template_trigger") == "off_topic":
            return ResponseTemplates.off_topic()
        
        # 7. Check for user frustration
        if context.get("template_trigger") == "user_frustration":
            state_facts = context.get("state_facts", "You're encountering some challenges")
            highlight_progress = context.get("highlight_progress", "You have shown effort")
            offer_options = context.get("offer_options", "We can adjust our approach")
            return ResponseTemplates.user_frustration(state_facts, highlight_progress, offer_options)
        
        # 8. Check for success milestone
        if context.get("template_trigger") == "success_milestone":
            milestone = context.get("milestone", "a milestone")
            accomplishment = context.get("specific_accomplishment", "good progress")
            significance = context.get("significance", "You're advancing in your learning")
            return ResponseTemplates.success_milestone(milestone, accomplishment, significance)
        
        # 9. Check for clarification needed
        if context.get("template_trigger") == "clarification_needed":
            options = context.get("options", ["Continue with current topic", "Switch to a new topic"])
            return ResponseTemplates.clarification_needed(options)
        
        # 10. Check for assessment complete
        if context.get("template_trigger") == "assessment_complete":
            topic_name = context.get("topic_name", "Unknown Topic")
            total = context.get("total_questions", 0)
            correct = context.get("correct_answers", 0)
            old_mastery = context.get("old_mastery", 0.0)
            new_mastery = context.get("new_mastery", 0.0)
            insight = context.get("personalized_insight", "Keep practicing to improve!")
            return ResponseTemplates.assessment_complete(
                topic_name, total, correct, old_mastery, new_mastery, insight
            )
        
        return None
