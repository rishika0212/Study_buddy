"""
Response Template Examples - Test Cases and Usage Scenarios
"""

from backend.app.services.response_templates import ResponseTemplates, TemplateSelector

# ============================================================================
# TEMPLATE 1: TOPIC NOT IN SESSION
# ============================================================================

def example_topic_not_in_session():
    """User mentions a topic not in their session"""
    template = ResponseTemplates.topic_not_in_session("Machine Learning")
    return template

# Output:
# {
#     "content": "I notice you mentioned Machine Learning, but it's not in your current session yet.\n\nWould you like me to:\n1. Add \"Machine Learning\" to your session and explain it\n2. Select a different topic from your history\n\nPlease choose an option (1 or 2).",
#     "template_type": "TOPIC_NOT_IN_SESSION",
#     "requires_choice": True,
#     "choices": ["1", "2"]
# }


# ============================================================================
# TEMPLATE 2: ASSESSMENT VIA CHAT
# ============================================================================

def example_assessment_via_chat():
    """User tries to start assessment through chat"""
    template = ResponseTemplates.assessment_via_chat("JavaScript Basics")
    return template

# Output:
# {
#     "content": "To start an assessment, please:\n1. Click \"Assessments\" in the sidebar\n2. Choose \"MCQ\" or \"QnA\"\n3. Select the topic: JavaScript Basics\n4. Enter number of questions (1-50)\n5. Click \"Start Assessment\"\n\nI cannot start assessments through chat messages to ensure proper setup.",
#     "template_type": "ASSESSMENT_VIA_CHAT",
#     "requires_choice": False
# }


# ============================================================================
# TEMPLATE 3: MISSING CONTEXT
# ============================================================================

def example_missing_context():
    """User's message is ambiguous without context"""
    template = ResponseTemplates.missing_context()
    return template

# Output:
# {
#     "content": "I don't have enough context to answer that accurately.\n\nCould you:\n- Specify which topic you're referring to?\n- Rephrase with more detail?\n- Or, let me know if you'd like to start a new topic.",
#     "template_type": "MISSING_CONTEXT",
#     "requires_choice": False
# }


# ============================================================================
# TEMPLATE 4: UNASSESSED TOPIC
# ============================================================================

def example_unassessed_topic():
    """User asks about topic mastery with 0 attempts"""
    template = ResponseTemplates.unassessed_topic("Python Fundamentals", mastery=0.0)
    return template

# Output:
# {
#     "content": "Python Fundamentals - 0% mastery\nStatus: Unassessed 🔵\n\nYou haven't attempted any questions for this topic yet.\n\nWould you like to:\n1. Learn the basics first (I'll explain the concept)\n2. Test your current knowledge (Start assessment)\n\nChoose 1 or 2.",
#     "template_type": "UNASSESSED_TOPIC",
#     "requires_choice": True,
#     "choices": ["1", "2"],
#     "topic_name": "Python Fundamentals",
#     "mastery": 0.0
# }


# ============================================================================
# TEMPLATE 5: CORRUPTED SESSION
# ============================================================================

def example_corrupted_session():
    """Session data validation fails"""
    template = ResponseTemplates.corrupted_session(error_id="a1b2c3d4")
    return template

# Output:
# {
#     "content": "⚠️ Session Data Issue Detected\n\nYour session data appears inconsistent.\n\nOptions:\n1. Attempt automatic repair\n2. Start a new session (current archived)\n3. Export data for support\n\nWhich would you like to do?\n\nError ID: a1b2c3d4 - Logged for investigation.",
#     "template_type": "CORRUPTED_SESSION",
#     "requires_choice": True,
#     "choices": ["1", "2", "3"],
#     "error_id": "a1b2c3d4"
# }


# ============================================================================
# TEMPLATE 6: OFF-TOPIC
# ============================================================================

def example_off_topic():
    """User engages in non-educational chat"""
    template = ResponseTemplates.off_topic()
    return template

# Output:
# {
#     "content": "I'm Study Buddy, focused on helping you learn effectively.\n\nI can:\n- Explain topics you want to learn\n- Assess your understanding\n- Track your progress\n- Identify weak areas\n\nWould you like to add a topic to your session, or is there something else I can help you learn?",
#     "template_type": "OFF_TOPIC",
#     "requires_choice": False
# }


# ============================================================================
# TEMPLATE 7: USER FRUSTRATION
# ============================================================================

def example_user_frustration():
    """User expresses difficulty or repeated failures"""
    template = ResponseTemplates.user_frustration(
        state_facts="You've attempted 4 questions on 'Recursion' and got 2 correct",
        highlight_progress="You're improving - last attempt was better than the first",
        offer_options="We can break down recursion into smaller, easier concepts first"
    )
    return template

# Output:
# {
#     "content": "I can see this is challenging. Let's break it down:\n\nCurrent situation: You've attempted 4 questions on 'Recursion' and got 2 correct\nWhat's working: You're improving - last attempt was better than the first\nWhat we can adjust: We can break down recursion into smaller, easier concepts first\n\nYou're making progress. Would you like to:\n1. Review weaker areas with focused explanations\n2. Take a break and come back later\n3. Try a different topic to build confidence",
#     "template_type": "USER_FRUSTRATION",
#     "requires_choice": True,
#     "choices": ["1", "2", "3"]
# }


# ============================================================================
# TEMPLATE 8: SUCCESS MILESTONE
# ============================================================================

def example_success_milestone():
    """User achieves mastery milestone"""
    template = ResponseTemplates.success_milestone(
        milestone="90% Mastery",
        specific_accomplishment="Achieved 90% mastery on Advanced Python",
        significance="You're now an expert in this topic and ready for real-world applications"
    )
    return template

# Output:
# {
#     "content": "🎉 Congratulations!\n\nYou've achieved 90% Mastery: Achieved 90% mastery on Advanced Python\n\nThis means: You're now an expert in this topic and ready for real-world applications\n\nKeep up the excellent work!",
#     "template_type": "SUCCESS_MILESTONE",
#     "requires_choice": False
# }


# ============================================================================
# TEMPLATE 9: CLARIFICATION NEEDED
# ============================================================================

def example_clarification_needed():
    """User's intent is ambiguous"""
    template = ResponseTemplates.clarification_needed([
        "Deep dive into Python decorators",
        "Overview of Python in general",
        "Common Python mistakes to avoid"
    ])
    return template

# Output:
# {
#     "content": "I want to help, but I need clarification.\n\nDid you want to:\n1. Deep dive into Python decorators\n2. Overview of Python in general\n3. Common Python mistakes to avoid\n\nPlease choose a number.",
#     "template_type": "CLARIFICATION_NEEDED",
#     "requires_choice": True,
#     "choices": ["1", "2", "3"]
# }


# ============================================================================
# TEMPLATE 10: ASSESSMENT COMPLETE
# ============================================================================

def example_assessment_complete():
    """User finishes assessment"""
    template = ResponseTemplates.assessment_complete(
        topic_name="React Hooks",
        total_questions=10,
        correct_answers=8,
        old_mastery=0.6,
        new_mastery=0.82,
        personalized_insight="Excellent improvement! You now understand the fundamentals of React Hooks well. Focus on useCallback and useContext next."
    )
    return template

# Output:
# {
#     "content": "Assessment Complete ✓\n\nTopic: React Hooks\nQuestions: 10\nCorrect: 8 (80%)\nUpdated Mastery: 60% → 82%\nStatus: Proficient ✅\n\nExcellent improvement! You now understand the fundamentals of React Hooks well. Focus on useCallback and useContext next.\n\nNext steps:\n- Review incorrect questions\n- Start new assessment\n- Study weak areas",
#     "template_type": "ASSESSMENT_COMPLETE",
#     "requires_choice": False,
#     "metrics": {
#         "topic_name": "React Hooks",
#         "total_questions": 10,
#         "correct_answers": 8,
#         "percentage": 80,
#         "old_mastery": 0.6,
#         "new_mastery": 0.82,
#         "old_mastery_pct": 60,
#         "new_mastery_pct": 82,
#         "status": "Proficient ✅"
#     }
# }


# ============================================================================
# TEMPLATE SELECTOR USAGE
# ============================================================================

def example_selector():
    """Using TemplateSelector to automatically pick template"""
    
    # Observation from agent
    observation = {
        "user_id": "user123",
        "user_input": "Can you test me on Python?",
        "profile": {},  # UserProfile object
        "memory": {},   # Memory object
        "last_10_history": [],
        "pending_transactions": {}
    }
    
    # Context from route execution
    context = {
        "template_trigger": "assessment_via_chat",
        "topic_name": "Python Basics"
    }
    
    # Get template
    template = TemplateSelector.select_template(observation, context)
    
    return template

# Returns assessment_via_chat template automatically


# ============================================================================
# STATUS BADGE GENERATION
# ============================================================================

def example_status_badges():
    """How assessment_complete determines status badge"""
    
    # 0% - 49%: Beginner
    template1 = ResponseTemplates.assessment_complete(
        "Topic", 10, 3, 0.0, 0.30, "Starting out"
    )
    print(template1["metrics"]["status"])  # "Beginner 🔵"
    
    # 50% - 69%: Intermediate
    template2 = ResponseTemplates.assessment_complete(
        "Topic", 10, 6, 0.4, 0.60, "Good progress"
    )
    print(template2["metrics"]["status"])  # "Intermediate 🟡"
    
    # 70% - 89%: Proficient
    template3 = ResponseTemplates.assessment_complete(
        "Topic", 10, 8, 0.6, 0.80, "Well done"
    )
    print(template3["metrics"]["status"])  # "Proficient ✅"
    
    # 90%+: Expert
    template4 = ResponseTemplates.assessment_complete(
        "Topic", 10, 10, 0.8, 1.0, "Perfect"
    )
    print(template4["metrics"]["status"])  # "Expert 🌟"


# ============================================================================
# AGENT INTEGRATION EXAMPLE
# ============================================================================

async def example_agent_integration():
    """How templates integrate in StudyAgent._route_and_execute()"""
    
    # When user tries to explain a topic not in session:
    result = {
        "action": "topic_not_in_session",
        "template_trigger": "topic_not_in_session",
        "topic": "Machine Learning"
    }
    
    # In _respond():
    template = TemplateSelector.select_template({}, result)
    
    # Returns:
    # {
    #     "content": "I notice you mentioned Machine Learning...",
    #     "template_type": "TOPIC_NOT_IN_SESSION",
    #     ...
    # }
    
    # Response to user:
    response = {
        "response": template["content"],
        "metadata": {
            "intent": "explain_topic",
            "template_type": template["template_type"]
        }
    }
    
    return response


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("Template Examples Generated Successfully")
    print("\nTo test, run:")
    print("  python -c 'from response_templates_examples import *'")
    print("\nThen call any example function:")
    print("  t = example_topic_not_in_session()")
    print("  print(t['content'])")
