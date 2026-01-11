import json
import time
import datetime
from typing import Dict, Any, Optional, List, Tuple
from langchain_core.output_parsers import JsonOutputParser
from backend.app.llm.ollama_client import get_ollama_client, invoke_with_retry
from backend.app.llm.prompts import CHAT_PROMPT, BRAIN_PROMPT, REFLECTION_PROMPT
from backend.app.vectorstore.retriever import retrieve_context
from backend.app.memory.conversation import get_conversation_memory
from backend.app.memory.user_profile import UserProfile
from backend.app.services.gap_detector import GapDetector
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.validation_service import StateValidationService
from backend.app.services.response_templates import ResponseTemplates, TemplateSelector
from backend.app.utils.logger import logger

class StudyAgent:
    def __init__(self):
        self.json_parser = JsonOutputParser()
        self.gap_detector = GapDetector()
        self.assessment_service = AssessmentService()

    async def generate_response(self, user_id: str, user_input: str, session_id: str = None):
        """
        AGENT DECISION LOOP: Execute this loop on EVERY user message.
        Topic-centric model - session_id is DEPRECATED and ignored.
        """
        
        # Step 1: OBSERVE
        observation = await self._observe(user_id, user_input)
        
        # Step 2: VALIDATE
        is_valid, error_msg = await self._validate(observation)
        if not is_valid:
            # Check if user is trying to recover
            if user_input.strip().lower() in ["repair", "new", "export"]:
                return await self._handle_recovery(user_input.strip().lower(), observation)
            
            # Handle corrupted state template
            if error_msg == "corrupted_state":
                template = ResponseTemplates.corrupted_session()
                return {
                    "content": template["content"],
                    "metadata": {"template_type": template["template_type"]}
                }
            
            return {"content": error_msg}
            
        # Step 3: CLASSIFY INTENT
        intent_info = await self._classify_intent(observation)
        
        # Step 4 & 5: ROUTE & EXECUTE
        result = await self._route_and_execute(intent_info, observation)
        
        # Step 6: UPDATE STATE
        changes = await self._update_state(result, observation)
        
        # Step 7: PERSIST
        await self._persist(changes, observation)
        
        # Step 8: RESPOND
        response = await self._respond(result, observation, intent_info)
        
        # Step 9: LOG
        self._log(intent_info, observation, changes)
        
        return response

    async def _observe(self, user_id: str, user_input: str) -> Dict:
        """Observe current state - topic-centric model, no sessions."""
        profile_obj = UserProfile(user_id)
        memory = get_conversation_memory(user_id)
        
        chat_history_vars = memory.load_memory_variables({})
        chat_history = chat_history_vars.get("chat_history", [])
        last_10_history = chat_history[-20:]
        
        return {
            "user_id": user_id,
            "user_input": user_input,
            "profile": profile_obj,
            "memory": memory,
            "last_10_history": last_10_history,
            "pending_transactions": profile_obj.data.get("active_challenges", {})
        }

    async def _validate(self, obs: Dict) -> Tuple[bool, str]:
        profile = obs["profile"]
        if not profile.data:
            return False, "Profile data is missing or corrupted."
        
        # Use StateValidationService to enforce protocol
        is_valid, errors = StateValidationService.validate_profile(profile.data, obs["last_10_history"])
        if not is_valid:
            # Use corrupted state template
            logger.error(f"Validation failed for user {obs['user_id']}: {errors}")
            obs["validation_failed"] = True
            return False, "corrupted_state"
            
        return True, ""

    async def _handle_recovery(self, action: str, obs: Dict) -> Dict:
        """Handle recovery actions - topic-centric model, no sessions."""
        profile = obs["profile"]
        
        if action == "new":
            profile.data = {
                "mastery": 0.0,
                "topics": {},
                "weak_areas": [],
                "strong_areas": [],
                "conversation_history": [],
                "mode": "idle",
                "active_challenges": {},
                "assessment_state": None,
                "created_at": time.time()
            }
            profile.save()
            obs["memory"].clear()
            return {"content": "Profile reset. How can I help you today?"}
            
        elif action == "repair":
            repaired = False
            errors_fixed = []
            
            # 1. Repair Mastery
            for name, topic in profile.data.get("topics", {}).items():
                if topic["questions_attempted"] > 0:
                    expected = round(topic["correct_answers"] / topic["questions_attempted"], 4)
                    if abs(topic["mastery_score"] - expected) > 0.0001:
                        topic["mastery_score"] = expected
                        errors_fixed.append(f"Fixed mastery for {name}")
                        repaired = True
            
            # 2. Repair Orphaned IDs
            topic_ids = {t["topic_id"] for t in profile.data.get("topics", {}).values()}
            for area in ["weak_areas", "strong_areas"]:
                original = profile.data.get(area, [])
                filtered = [tid for tid in original if tid in topic_ids]
                if len(filtered) != len(original):
                    profile.data[area] = filtered
                    errors_fixed.append(f"Cleaned {area}")
                    repaired = True
                    
            if repaired:
                profile.save()
                return {"content": f"Repair successful: {', '.join(errors_fixed)}."}
            return {"content": "No automatic repairs possible. Please use 'New' to reset."}
            
        elif action == "export":
            return {"content": f"Current State:\n```json\n{json.dumps(profile.data, indent=2)}\n```"}
            
        return {"content": "Invalid option. [Repair/New/Export]"}

    async def _classify_intent(self, obs: Dict) -> Dict:
        brain_input = {
            "input": obs["user_input"],
            "chat_history": obs["last_10_history"],
            "summary": "N/A", 
            "profile": json.dumps(obs["profile"].to_frontend_format()),
            "last_strategy": "explain" 
        }
        
        prompt = BRAIN_PROMPT.format(**brain_input)
        try:
            # Use brainstorm model for intent classification
            llm = get_ollama_client(task_type="planning", temperature=0.3)
            response_content = await invoke_with_retry(llm, prompt, max_retries=2)
            result = self.json_parser.parse(response_content)
            
            # Validate focus_area - if it's "general" or empty, try to extract from input
            if not result.get("focus_area") or result.get("focus_area", "").lower() == "general":
                extracted_topic = self._extract_topic_from_input(obs["user_input"])
                if extracted_topic:
                    result["focus_area"] = extracted_topic
                    result["intent"] = "explain_topic"
            
            return result
        except Exception as e:
            logger.error(f"Error parsing brain response: {e}")
            # Fallback: try to extract topic from user input
            extracted_topic = self._extract_topic_from_input(obs["user_input"])
            return {
                "intent": "explain_topic" if extracted_topic else "general_chat",
                "strategy": "explain",
                "depth": "intermediate",
                "focus_area": extracted_topic or "general",
                "detected_concepts": [extracted_topic] if extracted_topic else [],
                "confidence_level": 0.5,
                "confusion_detected": False
            }
    
    def _extract_topic_from_input(self, user_input: str) -> Optional[str]:
        """Extract topic from user input using simple patterns."""
        import re
        
        # Common question patterns
        patterns = [
            r"(?:what is|what are|what's)\s+(?:a |an |the )?(.+?)(?:\?|$)",
            r"(?:explain|tell me about|describe)\s+(?:a |an |the )?(.+?)(?:\?|$)",
            r"(?:how does|how do|how is)\s+(.+?)(?:\s+work|\?|$)",
            r"(?:why is|why are|why does|why do)\s+(.+?)(?:\?|$)",
            r"(?:can you explain|please explain)\s+(?:a |an |the )?(.+?)(?:\?|$)",
            r"(?:teach me about|learn about)\s+(?:a |an |the )?(.+?)(?:\?|$)",
            r"(?:define|definition of)\s+(?:a |an |the )?(.+?)(?:\?|$)",
        ]
        
        user_input_lower = user_input.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, user_input_lower, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                # Clean up the topic - remove trailing punctuation and limit length
                topic = re.sub(r'[?.!,;:]+$', '', topic).strip()
                if len(topic) > 2 and len(topic) <= 50:
                    # Title case the topic
                    return topic.title() if len(topic.split()) <= 4 else topic[:50]
        
        # If no pattern matches but the input looks like a question, use key words
        if '?' in user_input or user_input_lower.startswith(('what', 'how', 'why', 'explain', 'describe')):
            # Extract the main subject (skip common words)
            stop_words = {'is', 'are', 'the', 'a', 'an', 'of', 'in', 'on', 'to', 'for', 'and', 'or', 'it', 'this', 'that', 'can', 'you', 'me', 'please', 'what', 'how', 'why', 'does', 'do'}
            words = [w for w in user_input_lower.replace('?', '').split() if w not in stop_words and len(w) > 2]
            if words:
                # Take up to 3 meaningful words as the topic
                topic = ' '.join(words[:3])
                return topic.title()
        
        return None

    async def _route_and_execute(self, intent_info: Dict, obs: Dict) -> Dict:
        intent = intent_info.get("intent", "general_chat")
        user_input = obs["user_input"]
        user_id = obs["user_id"]
        # session_id removed - system is now topic-centric
        
        if intent == "add_topic":
            # Extract topic from input or use focus_area
            topic_name = intent_info.get("focus_area") or user_input.replace("teach me ", "").replace("Teach me ", "").strip()
            
            # Check if topic already exists
            if topic_name in obs["profile"].data.get("topics", {}):
                return {
                    "action": "topic_already_exists",
                    "content": f"'{topic_name}' is already in your session! Would you like an explanation or a quiz on it?"
                }
            
            # Store pending topic confirmation in active_challenges
            challenge_id = f"confirm_topic_{topic_name}"
            obs["profile"].data["active_challenges"][challenge_id] = {
                "type": "topic_confirmation",
                "topic_name": topic_name
            }
            obs["profile"].save()
            
            return {"action": "ask_topic_confirmation", "topic": topic_name}
            
        elif intent == "explain_topic":
            topic = intent_info.get("focus_area") or "general"
            
            # Just answer the question - don't block with "topic not in session"
            # The user asked a question, so we should answer it directly
            
            # Depth level mapping
            depth_map = {"beginner": "level_1", "intermediate": "level_2", "advanced": "level_3"}
            user_depth = intent_info.get("depth", "intermediate")
            cache_depth = depth_map.get(user_depth, "level_1")
            
            # NOTE: Disabled caching - each question should get a fresh response
            # The cache was causing the same response for different questions on the same topic
            # TODO: Implement smarter caching based on question hash + topic + depth
            
            # Compose explanation prompt based on depth
            context = retrieve_context(user_input)
            input_vars = {
                "knowledge_level": obs["profile"].to_frontend_format()["knowledge_level"],
                "context": context,
                "chat_history": obs["last_10_history"],
                "summary": "", 
                "known_concepts": ", ".join(obs["profile"].to_frontend_format()["known_concepts"]),
                "weak_areas": ", ".join(obs["profile"].to_frontend_format()["weak_areas"]),
                "preferences": "Concise and factual",
                "strategy": intent_info.get("strategy", "explain"),
                "focus_area": topic,
                "depth": user_depth,
                "input": user_input
            }
            # Add depth-specific instructions if needed
            if cache_depth == "level_1":
                input_vars["depth_instructions"] = "Give a conceptual overview in 8-12 sentences."
            elif cache_depth == "level_2":
                input_vars["depth_instructions"] = "Go deeper: add examples, edge cases, and clarify nuances."
            elif cache_depth == "level_3":
                input_vars["depth_instructions"] = "Be technical: include math, algorithms, and detailed mechanisms."
            prompt = CHAT_PROMPT.format_messages(**input_vars)
            try:
                # Use explanation model for quality
                llm = get_ollama_client(task_type="explanation", temperature=0.7)
                # Pass messages directly instead of str(prompt) to preserve message structure
                response_content = await invoke_with_retry(llm, prompt)
                
                # Add topic to profile when explanation is provided (if not already exists)
                if topic and topic != "general" and topic not in obs["profile"].data.get("topics", {}):
                    obs["profile"].add_topic(topic, explanation_summary=response_content[:200] if response_content else "")
                
                return {"action": "explain", "content": response_content, "topic": topic}
            except ConnectionError:
                return {
                    "action": "explain",
                    "content": "AI service is unavailable. Please ensure Ollama is running. You can try again in a moment."
                }
            except TimeoutError:
                return {
                    "action": "explain", 
                    "content": "The explanation is taking too long. Please try a simpler question or check if Ollama is responsive."
                }
            
        elif intent == "start_assessment":
            topic = intent_info.get("focus_area")
            if not topic or topic not in obs["profile"].data.get("topics", {}):
                return {
                    "action": "assessment_via_chat",
                    "template_trigger": "assessment_via_chat",
                    "topic": topic or "your selected topic"
                }
            
            # Check if topic is unassessed
            topic_data = obs["profile"].data["topics"].get(topic, {})
            if topic_data.get("questions_attempted", 0) == 0:
                return {
                    "action": "unassessed_topic",
                    "template_trigger": "unassessed_topic",
                    "topic": topic,
                    "mastery": topic_data.get("mastery_score", 0.0)
                }
            
            mastery = obs["profile"].data["topics"][topic]["mastery_score"]
            # Default to MCQ for now
            mcq = await self.assessment_service.generate_mcq(user_id, topic, mastery)
            return {"action": "start_mcq", "mcq": mcq, "topic": topic}
            
        elif intent == "answer_question":
            # Check for active challenges
            challenges = obs["pending_transactions"]
            if not challenges:

                return {"action": "general_chat", "content": "I don't see an active assessment or request. What would you like to do?"}
            
            # Find the most recent or relevant challenge
            challenge_id = list(challenges.keys())[0]
            
            if challenge_id.startswith("confirm_topic_"):
                topic_name = challenges[challenge_id]["topic_name"]
                is_confirmed = user_input.lower() in ["yes", "y", "sure", "correct", "yep", "ok"]
                return {"action": "confirm_topic", "topic": topic_name, "confirmed": is_confirmed, "challenge_id": challenge_id}
            
            topic = challenge_id.split("_")[-1]
            if challenge_id.startswith("mcq_"):
                eval_result = await self.assessment_service.submit_mcq_answer(user_id, topic, user_input)
                return {"action": "evaluate_mcq", "result": eval_result, "topic": topic}
            elif challenge_id.startswith("qna_"):
                eval_result = await self.assessment_service.submit_qna_answer(user_id, topic, user_input)
                return {"action": "evaluate_qna", "result": eval_result, "topic": topic}
            
        # Add other intents...
        return {"action": "general_chat", "content": "I'm not sure how to help with that yet, but I'm here to study with you!"}

    async def _update_state(self, result: Dict, obs: Dict) -> Dict:
        changes = {}
        profile = obs["profile"]
        
        if result["action"] == "confirm_topic":
            if result["confirmed"]:
                topic_name = result["topic"]
                if topic_name not in profile.data["topics"]:
                    profile.add_topic(topic_name)
                    changes["added_topic"] = topic_name
            # Always remove the confirmation challenge
            if result["challenge_id"] in profile.data["active_challenges"]:
                del profile.data["active_challenges"][result["challenge_id"]]
        
        elif result["action"] == "explain":
            # Track topic addition from explanations
            topic_name = result.get("topic")
            if topic_name and topic_name != "general":
                if topic_name in profile.data.get("topics", {}):
                    changes["explained_topic"] = topic_name
                
        elif result["action"] == "evaluate_mcq" or result["action"] == "evaluate_qna":
            # State update already handled in assessment_service for now
            # But we should track it for atomic persistence if possible
            changes["assessment_completed"] = result["topic"]
            
        return changes

    async def _persist(self, changes: Dict, obs: Dict):
        profile = obs["profile"]
        max_retries = 3
        for attempt in range(max_retries):
            try:
                profile.save()
                return
            except Exception as e:
                logger.error(f"Persistence attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    # Rollback logic would go here if we had snapshots
                    raise e
                time.sleep(0.1)

    async def _respond(self, result: Dict, obs: Dict, intent_info: Dict) -> Dict:
        content = ""
        metadata = {"intent": intent_info.get("intent")}
        
        # Check if this action has a template trigger
        if "template_trigger" in result:
            template = TemplateSelector.select_template(obs, result)
            if template:
                content = template["content"]
                metadata["template_type"] = template.get("template_type")
        
        # Otherwise, handle action-based responses
        if not content:
            if result["action"] == "ask_topic_confirmation":
                content = f"I'll add '{result['topic']}' to your session. Correct?"
            elif result["action"] == "confirm_topic":
                if result["confirmed"]:
                    content = f"Adding '{result['topic']}' from history. Starting fresh." if intent_info.get("from_history") else f"Added '{result['topic']}' to your active topics! Would you like an explanation or a quick quiz?"
                else:
                    content = "Okay, I won't add that topic. What else would you like to study?"
            elif result["action"] == "explain":
                content = result["content"]
                # Just provide the explanation - no forced menu options
            elif result["action"] == "start_mcq":
                content = f"Starting MCQ for {result['topic']}:\n\n{result['mcq']['question']}\n"
                for k, v in result["mcq"]["options"].items():
                    content += f"{k}) {v}\n"
                metadata["mcq"] = result["mcq"]
            elif result["action"] == "evaluate_mcq" or result["action"] == "evaluate_qna":
                res = result["result"]
                total_marks = res.get("total_marks", 0)
                is_correct = res.get("is_correct") or total_marks >= 7
                is_partial = not is_correct and total_marks >= 4
                
                # Determine status based on result
                if is_correct:
                    status = "✅ Correct!"
                elif is_partial:
                    status = "⚠️ Partially Correct"
                else:
                    status = "❌ Incorrect"
                
                # Build explanation - MANDATORY: always show feedback and correct explanation
                feedback = res.get('feedback', '')
                correct_explanation = res.get('correct_explanation', '')
                rubric_evaluation = res.get('rubric_evaluation', '')
                
                # Format the response with mandatory explanation
                content = f"{status}\n\n"
                
                # For QnA, show score breakdown
                if result["action"] == "evaluate_qna":
                    content += f"**Score:** {total_marks}/10\n"
                    if rubric_evaluation:
                        content += f"**Rubric:** {rubric_evaluation}\n\n"
                    else:
                        # Show individual scores if available
                        concept = res.get('concept_score', 0)
                        complete = res.get('completeness_score', 0)
                        clarity = res.get('clarity_score', 0)
                        content += f"**Rubric:** Correctness: {concept}/5, Completeness: {complete}/3, Clarity: {clarity}/2\n\n"
                
                # MANDATORY: Always include explanation
                if feedback:
                    content += f"**Explanation:** {feedback}\n\n"
                
                # For incorrect/partial answers, ALWAYS show the correct answer
                if not is_correct and correct_explanation:
                    content += f"**Correct Answer:** {correct_explanation}"
                elif is_correct and correct_explanation:
                    # For correct, show brief explanation if available
                    content += f"{correct_explanation}"
                elif not is_correct:
                    # Fallback if no correct explanation provided
                    content += "**Note:** Review this topic to strengthen your understanding."
            
            if not content:
                content = result.get("content", "I'm listening.")
            
        # Save to memory with timestamps
        from langchain_core.messages import HumanMessage, AIMessage
        ts = time.time()
        obs["memory"].chat_memory.add_message(HumanMessage(content=obs["user_input"], additional_kwargs={"timestamp": ts}))
        obs["memory"].chat_memory.add_message(AIMessage(content=content, additional_kwargs={"timestamp": ts}))
        
        return {
            "content": content,
            "metadata": metadata
        }

    async def _log(self, intent_info: Dict, obs: Dict, changes: Dict):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_id": obs["user_id"],
            "intent": intent_info.get("intent"),
            "changes": changes,
            "confidence": intent_info.get("confidence_level")
        }
        logger.info(f"AGENT_LOOP_LOG: {json.dumps(log_entry)}")

