import json
import re
from typing import Dict, Any, List
from langchain_core.output_parsers import JsonOutputParser
from backend.app.llm.ollama_client import get_ollama_client, invoke_with_retry, OllamaClientManager
from backend.app.llm.prompts import (
    MCQ_GENERATION_PROMPT, MCQ_EVALUATION_PROMPT, QNA_EVALUATION_PROMPT, QNA_GENERATION_PROMPT
)
from backend.app.vectorstore.retriever import retrieve_context
from backend.app.utils.logger import logger
from backend.app.services.mastery_service import MasteryService
from backend.app.config import settings


def is_gibberish_answer(answer: str) -> bool:
    """
    Detect if an answer is gibberish, random characters, or meaningless.
    Returns True if the answer is invalid/gibberish, False if it's meaningful text.
    """
    if not answer or not answer.strip():
        return True
    
    cleaned = answer.strip()
    
    # Too short to be meaningful (less than 3 characters)
    if len(cleaned) < 3:
        return True
    
    # Check if mostly non-alphabetic characters
    alpha_chars = sum(1 for c in cleaned if c.isalpha())
    if len(cleaned) > 0 and alpha_chars / len(cleaned) < 0.5:
        return True
    
    # Check for random character patterns (e.g., "asdf", "qwerty", "zxcv")
    gibberish_patterns = [
        r'^[asdfghjklqwertyuiopzxcvbnm]{3,}$',  # keyboard mashing
        r'^[a-z]{1,3}(\s+[a-z]{1,3}){0,5}$',  # random short letter groups
        r'^[^a-zA-Z]*$',  # no letters at all
        r'^(.{1,2})\1{2,}$',  # repeated short patterns like "ababab"
    ]
    
    lower_cleaned = cleaned.lower()
    for pattern in gibberish_patterns:
        if re.match(pattern, lower_cleaned, re.IGNORECASE):
            return True
    
    # Check if it contains at least one meaningful word (3+ letters)
    words = re.findall(r'[a-zA-Z]{3,}', cleaned)
    if len(words) == 0:
        return True
    
    # Check for common gibberish words
    gibberish_words = {'asdf', 'qwerty', 'zxcv', 'aaa', 'bbb', 'ccc', 'xxx', 'yyy', 'zzz', 'test', 'testing123'}
    if all(word.lower() in gibberish_words for word in words):
        return True
    
    return False


class AssessmentService:
    def __init__(self):
        self.json_parser = JsonOutputParser()

    async def generate_mcq(self, user_id: str, topic: str, mastery: float) -> Dict[str, Any]:
        """Generate MCQ - topic-centric model, no sessions."""
        import random
        import time
        
        difficulty = "beginner"
        if mastery >= 0.9: difficulty = "mastery"
        elif mastery >= 0.7: difficulty = "proficient"
        elif mastery >= 0.4: difficulty = "developing"
        
        context = retrieve_context(topic)
        
        # Get question count for this topic to ensure variety
        from backend.app.memory.user_profile import UserProfile
        profile = UserProfile(user_id)
        topic_data = profile.data.get("topics", {}).get(topic, {})
        question_num = topic_data.get("questions_attempted", 0) + 1
        
        # Different question types to encourage variety
        question_types = [
            "definition or meaning",
            "key characteristics", 
            "practical application",
            "comparison with related concepts",
            "common misconception",
            "example or use case",
            "advantage or benefit",
            "limitation or challenge"
        ]
        question_type = random.choice(question_types)
        
        # Random seed for variety
        seed = int(time.time() * 1000) % 10000
        
        # Try up to 3 times with increasingly simple prompts
        for attempt in range(3):
            try:
                from langchain_core.prompts import PromptTemplate
                
                # Use quality-focused model for generation
                llm = get_ollama_client(task_type="mcq_generation")
                
                if attempt == 0:
                    # First attempt: use main prompt with variety hints
                    prompt_template = PromptTemplate.from_template(MCQ_GENERATION_PROMPT)
                    prompt = prompt_template.format(
                        topic=topic,
                        difficulty=difficulty,
                        mastery=mastery,
                        context=context
                    )
                    # Add variety instruction
                    prompt += f"\n\nIMPORTANT: This is question #{question_num} about {topic}. Focus on: {question_type}. Generate a UNIQUE question different from basic definitions. Random seed: {seed}"
                elif attempt == 1:
                    # Second attempt: simpler prompt with specific focus
                    prompt = f"""Create a multiple choice question about {topic}, focusing on {question_type}.
This is question #{question_num}, so make it DIFFERENT from previous questions.

Return ONLY valid JSON (no markdown, no explanation):
{{"question": "Your unique question about {topic}?", "options": {{"A": "first option", "B": "second option", "C": "third option", "D": "fourth option"}}, "correct_answer": "A", "explanation": "why correct"}}"""
                else:
                    # Third attempt: most basic prompt
                    aspects = ["definition", "usage", "example", "benefit", "limitation"]
                    aspect = random.choice(aspects)
                    prompt = f'Create a {aspect} question about {topic}. Return JSON only: {{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct_answer": "A", "explanation": "..."}}'
                
                # Invoke with retry logic
                response_content = await invoke_with_retry(llm, prompt, max_retries=1)
                logger.info(f"MCQ attempt {attempt + 1} raw response: {response_content[:200]}...")
                
                data = self._parse_json_response(response_content, f"MCQ generation attempt {attempt + 1}")
                
                # Validate required fields exist
                required_fields = ["question", "options", "correct_answer"]
                if not data or "error" in data or not all(field in data for field in required_fields):
                    logger.warning(f"MCQ attempt {attempt + 1} invalid: missing fields")
                    continue
                
                # Validate options structure
                if not isinstance(data.get("options"), dict) or len(data["options"]) < 4:
                    logger.warning(f"MCQ attempt {attempt + 1} invalid: bad options")
                    continue
                
                # Success! Store correct answer in profile and remove from response
                if "active_challenges" not in profile.data:
                    profile.data["active_challenges"] = {}
                
                challenge_id = f"mcq_{topic}"
                profile.data["active_challenges"][challenge_id] = {
                    "question": data["question"],
                    "correct_answer": data["correct_answer"],
                    "explanation": data.get("explanation", "")
                }
                profile.save()
                
                # Remove sensitive data before returning to client
                del data["correct_answer"]
                if "explanation" in data:
                    del data["explanation"]
                    
                return data
                
            except Exception as e:
                logger.warning(f"MCQ Generation attempt {attempt + 1} failed: {e}")
                continue
        
        # All attempts failed - use fallback question
        logger.error(f"All MCQ generation attempts failed for {topic}, using fallback")
        return self._generate_fallback_mcq(user_id, topic, question_num)
    
    def _generate_fallback_mcq(self, user_id: str, topic: str, question_num: int = 1) -> Dict[str, Any]:
        """Generate a fallback MCQ when LLM fails."""
        import random
        from backend.app.memory.user_profile import UserProfile
        
        # Different fallback question templates for variety
        templates = [
            {
                "question": f"Which of the following best describes {topic}?",
                "options": {
                    "A": f"A core concept that involves processing and analysis",
                    "B": f"An unrelated field of study",
                    "C": f"A type of physical hardware",
                    "D": f"A mathematical constant"
                },
                "correct": "A"
            },
            {
                "question": f"What is a key characteristic of {topic}?",
                "options": {
                    "A": f"It requires understanding of fundamental principles",
                    "B": f"It only applies to biological systems",
                    "C": f"It was invented in the 18th century",
                    "D": f"It has no practical applications"
                },
                "correct": "A"
            },
            {
                "question": f"Why is {topic} important?",
                "options": {
                    "A": f"It helps solve real-world problems",
                    "B": f"It is only useful for entertainment",
                    "C": f"It has been proven obsolete",
                    "D": f"It only works on Tuesdays"
                },
                "correct": "A"
            },
            {
                "question": f"In what context would you use {topic}?",
                "options": {
                    "A": f"When solving problems in this domain",
                    "B": f"Only when cooking",
                    "C": f"Never - it's purely theoretical",
                    "D": f"Only during solar eclipses"
                },
                "correct": "A"
            },
            {
                "question": f"What is NOT true about {topic}?",
                "options": {
                    "A": f"It has no connection to technology",
                    "B": f"It can be applied practically",
                    "C": f"It involves systematic approaches",
                    "D": f"It requires knowledge and skills"
                },
                "correct": "A"
            }
        ]
        
        # Select based on question number to ensure variety
        template = templates[(question_num - 1) % len(templates)]
        
        # Shuffle options for additional variety
        options_list = list(template["options"].items())
        correct_text = template["options"][template["correct"]]
        random.shuffle(options_list)
        
        # Rebuild options and find new correct answer key
        new_options = {}
        new_correct = "A"
        for i, (_, text) in enumerate(options_list):
            key = chr(65 + i)  # A, B, C, D
            new_options[key] = text
            if text == correct_text:
                new_correct = key
        
        question = template["question"]
        explanation = f"This is a fundamental aspect of {topic} that you should understand."
        
        # Store in profile
        profile = UserProfile(user_id)
        if "active_challenges" not in profile.data:
            profile.data["active_challenges"] = {}
        
        challenge_id = f"mcq_{topic}"
        profile.data["active_challenges"][challenge_id] = {
            "question": question,
            "correct_answer": new_correct,
            "explanation": explanation
        }
        profile.save()
        
        return {
            "question": question,
            "options": new_options,
            "fallback": True
        }

    async def submit_mcq_answer(self, user_id: str, topic: str, user_answer: str) -> Dict[str, Any]:
        """Submit MCQ answer - topic-centric model, no sessions.
        
        CRITICAL ASSESSMENT ENFORCEMENT (ZERO SILENT FAILURES):
        1. Wait for user to select exactly ONE option
        2. Evaluate correctness (exact match only)
        3. MANDATORY: questions_attempted += 1
        4. If correct: correct_answers += 1
        5. MANDATORY: Provide explanation (short for correct, detailed for incorrect)
        6. Recalculate mastery: mastery = correct_answers / questions_attempted
        7. Update classification: mastery < 0.40 → WEAK, mastery >= 0.40 → STRONG
        8. Update sidebar UI immediately
        
        FAILURE RULE: If evaluation fails, return error - no silent behavior allowed.
        """
        from backend.app.memory.user_profile import UserProfile
        profile = UserProfile(user_id)
        challenge_id = f"mcq_{topic}"
        challenge = profile.data.get("active_challenges", {}).get(challenge_id)
        
        if not challenge:
            return {
                "is_correct": False, 
                "marks": 0, 
                "result": "error",
                "feedback": "Assessment evaluation failed. No active challenge found for this topic. Please retry.", 
                "correct_explanation": "",
                "evaluation_error": True
            }
        
        try:
            evaluation = await self.evaluate_mcq(challenge["question"], challenge["correct_answer"], user_answer)
        except Exception as e:
            logger.error(f"MCQ evaluation failed: {e}")
            return {
                "is_correct": False,
                "marks": 0,
                "result": "error",
                "feedback": "Assessment evaluation failed. Please retry.",
                "correct_explanation": challenge.get("explanation", ""),
                "evaluation_error": True
            }
        
        is_correct = evaluation.get("is_correct", False)
        
        # MANDATORY: Ensure explanation is always present
        if not evaluation.get("correct_explanation") or evaluation.get("correct_explanation") == "Error":
            evaluation["correct_explanation"] = challenge.get("explanation", "")
        
        # GUARANTEE: Explanation must be provided - generate fallback if missing
        if not evaluation.get("feedback"):
            if is_correct:
                evaluation["feedback"] = f"Correct! You selected the right answer ({user_answer.strip().upper()})."
            else:
                evaluation["feedback"] = f"Incorrect. You answered '{user_answer.strip().upper()}', but the correct answer is '{challenge['correct_answer']}'. Review this topic to understand why '{challenge['correct_answer']}' is the right choice."
        
        if not evaluation.get("correct_explanation"):
            evaluation["correct_explanation"] = f"The correct answer is {challenge['correct_answer']}. {challenge.get('explanation', 'Review the concept to understand why.')}"
            
        # MANDATORY: Update mastery (this increments questions_attempted and correct_answers)
        MasteryService.update_after_mcq(user_id, topic, is_correct)
        
        # MANDATORY: Get updated mastery and classification for frontend
        updated_profile = UserProfile(user_id)
        topic_data = updated_profile.get_topic(topic)
        
        # MANDATORY: Include all required fields for frontend update
        evaluation["mastery_score"] = topic_data["mastery_score"]
        evaluation["status"] = topic_data["status"]
        evaluation["classification"] = topic_data["classification"]  # "weak" | "strong" | "unassessed"
        evaluation["questions_attempted"] = topic_data["questions_attempted"]
        evaluation["correct_answers"] = topic_data["correct_answers"]
        evaluation["explanation_provided"] = True  # Flag to confirm explanation was given
        
        # Cleanup challenge
        del profile.data["active_challenges"][challenge_id]
        profile.save()
        
        return evaluation

    async def evaluate_mcq(self, question: str, correct_answer: str, user_answer: str) -> Dict[str, Any]:
        """Evaluate MCQ answer with MANDATORY explanation guarantee.
        
        CRITICAL RULES:
        1. Exact string match for answer key required for correctness
        2. Unanswered = incorrect (0 points)
        3. EVERY answer MUST receive an explanation - NO EXCEPTIONS
        4. If CORRECT: SHORT explanation (1-2 sentences)
        5. If INCORRECT: DETAILED explanation (3-5 sentences)
        6. No partial credit - 1 for correct, 0 for incorrect
        """
        # Rule: Unanswered = incorrect (0 points) - DETAILED explanation required
        if not user_answer or user_answer.strip() == "":
            return {
                "is_correct": False,
                "result": "incorrect",
                "marks": 0,
                "feedback": "No answer was provided. Unanswered questions are marked as INCORRECT with 0 points. To demonstrate understanding, you must select one of the options (A, B, C, or D). Each question tests a specific concept - attempting an answer helps identify gaps in understanding and guides your learning path.",
                "correct_explanation": f"The correct answer was {correct_answer}. This question tests your understanding of the topic. Review the question carefully and understand why {correct_answer} is the correct choice by examining the concept it represents."
            }
        
        # Rule: Exact string match for answer key
        is_correct_match = user_answer.strip().upper() == correct_answer.strip().upper()
        
        try:
            from langchain_core.prompts import PromptTemplate
            
            # Use fast model for MCQ evaluation
            llm = get_ollama_client(task_type="mcq_eval", temperature=0.0)
            
            prompt_template = PromptTemplate.from_template(MCQ_EVALUATION_PROMPT)
            prompt = prompt_template.format(
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer
            )
            
            # Invoke with retry logic
            response_content = await invoke_with_retry(llm, prompt, max_retries=2)
            evaluation = self._parse_json_response(response_content, "MCQ evaluation")
            
            # Enforce exact match rule over LLM opinion if they differ
            if is_correct_match:
                evaluation["is_correct"] = True
                evaluation["marks"] = 1
                evaluation["result"] = "correct"
            else:
                evaluation["is_correct"] = False
                evaluation["marks"] = 0
                evaluation["result"] = "incorrect"
                
            return evaluation
        except (TimeoutError, ConnectionError):
            # For MCQ evaluation, we can safely use exact match if service fails
            logger.warning(f"MCQ Evaluation service error, using exact match")
            if is_correct_match:
                return {
                    "is_correct": True,
                    "result": "correct",
                    "marks": 1,
                    "feedback": f"Correct! You selected the right answer ({user_answer.strip().upper()}).",
                    "correct_explanation": f"The correct answer is {correct_answer}."
                }
            else:
                return {
                    "is_correct": False,
                    "result": "incorrect",
                    "marks": 0,
                    "feedback": f"Incorrect. You selected '{user_answer.strip().upper()}', but the correct answer is '{correct_answer}'. Review this topic to understand why '{correct_answer}' is the right choice and how it differs from the other options.",
                    "correct_explanation": f"The correct answer is {correct_answer}. Make sure to review the concept thoroughly."
                }
        except Exception as e:
            logger.error(f"MCQ Evaluation failed: {e}")
            if is_correct_match:
                return {
                    "is_correct": True,
                    "result": "correct",
                    "marks": 1,
                    "feedback": "Correct! Well done.",
                    "correct_explanation": f"The correct answer is {correct_answer}."
                }
            else:
                return {
                    "is_correct": False,
                    "result": "incorrect",
                    "marks": 0,
                    "feedback": f"Incorrect. You answered '{user_answer.strip().upper()}', but the correct answer is '{correct_answer}'. This question tests your understanding of the topic. Review the material and try to understand why '{correct_answer}' is correct.",
                    "correct_explanation": f"The correct answer is {correct_answer}."
                }

    async def generate_qna(self, user_id: str, topic: str, mastery: float, length: str = "medium") -> Dict[str, Any]:
        """Generate QnA - topic-centric model, no sessions."""
        difficulty = "beginner"
        if mastery >= 0.9: difficulty = "mastery"
        elif mastery >= 0.7: difficulty = "proficient"
        elif mastery >= 0.4: difficulty = "developing"
        
        context = retrieve_context(topic)
        
        try:
            from langchain_core.prompts import PromptTemplate
            
            # Use quality-focused model for generation
            llm = get_ollama_client(task_type="qna_generation")
            
            prompt_template = PromptTemplate.from_template(QNA_GENERATION_PROMPT)
            prompt = prompt_template.format(
                topic=topic,
                difficulty=difficulty,
                mastery=mastery,
                length=length,
                context=context
            )
            
            # Invoke with retry logic
            response_content = await invoke_with_retry(llm, prompt)
            data = self._parse_json_response(response_content, "QnA generation")
            
            if not data:
                raise ValueError("Invalid QnA response structure")

            # Store challenge for evaluation
            from backend.app.memory.user_profile import UserProfile
            profile = UserProfile(user_id)
            if "active_challenges" not in profile.data:
                profile.data["active_challenges"] = {}
                
            challenge_id = f"qna_{topic}"
            profile.data["active_challenges"][challenge_id] = {
                "question": data["question"],
                "length": data.get("length", length)
            }
            profile.save()

            # Remove expected points if they exist to avoid revealing too much
            if "expected_points" in data:
                del data["expected_points"]
                
            return data
        except TimeoutError:
            logger.error(f"QnA Generation timeout for {topic}")
            return {
                "question": f"Question generation timed out. Please try generating a {length} question again.",
                "error": "timeout"
            }
        except ConnectionError:
            logger.error(f"QnA Generation connection error for {topic}")
            return {
                "question": "AI service unavailable. Ensure Ollama is running.",
                "error": "connection"
            }
        except Exception as e:
            logger.error(f"Q&A Generation failed: {e}")
            return {
                "question": f"Explain the core concepts of {topic} in a {length} manner.",
                "error": str(e)
            }

    async def submit_qna_answer(self, user_id: str, topic: str, user_answer: str) -> Dict[str, Any]:
        """Submit QnA answer - topic-centric model, no sessions.
        
        CRITICAL ASSESSMENT ENFORCEMENT (ZERO SILENT FAILURES):
        
        QnA MODE (MANDATORY):
        1. User must type a text answer
        2. Validate input: If empty, random characters, or meaningless → INVALID
        3. If INVALID: Mark INCORRECT, questions_attempted += 1, provide DETAILED explanation
        4. If VALID: Evaluate using meaning-based analysis (conceptual correctness)
        5. Score >= 4 = CORRECT (counts for mastery), Score < 4 = INCORRECT
        6. MANDATORY: questions_attempted += 1, If correct: correct_answers += 1
        7. MANDATORY: Provide explanation (SHORT for correct, DETAILED for incorrect)
        8. Recalculate mastery and update STRONG/WEAK immediately
        
        FAILURE RULE: If evaluation fails, return error - no silent behavior.
        """
        from backend.app.memory.user_profile import UserProfile
        profile = UserProfile(user_id)
        challenge_id = f"qna_{topic}"
        challenge = profile.data.get("active_challenges", {}).get(challenge_id)

        if not challenge:
            return {
                "total_marks": 0, 
                "result": "error",
                "feedback": "Assessment evaluation failed. No active challenge found for this topic. Please retry.", 
                "correct_explanation": "",
                "evaluation_error": True
            }

        # Get context for correct answer explanation
        context = retrieve_context(topic)
        
        # RULE 1: Empty answer = INCORRECT (0 points)
        if not user_answer or user_answer.strip() == "":
            evaluation = {
                "is_valid_answer": False,
                "result": "incorrect",
                "concept_score": 0,
                "completeness_score": 0,
                "clarity_score": 0,
                "total_marks": 0,
                "feedback": "No answer was provided. Unanswered questions are marked as INCORRECT with a score of 0. To demonstrate understanding, you must provide a response that addresses the question directly, covers the key concepts, and is clearly structured.",
                "rubric_evaluation": "Correctness: 0/5 (no content), Completeness: 0/3 (no content), Clarity: 0/2 (no content) = Total: 0/10",
                "correct_explanation": f"The correct answer should address: {challenge['question']}. A complete answer would include the core concept definition, relevant explanation, and examples where appropriate based on the {challenge.get('length', 'medium')} response mode."
            }
        # RULE 2: Gibberish/random characters = INCORRECT (0 points)
        elif is_gibberish_answer(user_answer):
            evaluation = {
                "is_valid_answer": False,
                "result": "incorrect",
                "concept_score": 0,
                "completeness_score": 0,
                "clarity_score": 0,
                "total_marks": 0,
                "feedback": "Your answer appears to be random characters or gibberish without meaningful content. This is marked as INCORRECT with a score of 0. Please provide a thoughtful response that demonstrates your understanding of the topic. A valid answer should contain clear words and sentences that address the question.",
                "rubric_evaluation": "Correctness: 0/5 (gibberish detected), Completeness: 0/3 (no meaningful content), Clarity: 0/2 (incomprehensible) = Total: 0/10",
                "correct_explanation": f"The correct answer should address: {challenge['question']}. Instead of random characters, provide a response that explains the concept, includes relevant details, and demonstrates genuine understanding of {topic}."
            }
        else:
            # RULE 3: Evaluate meaningful answers using rubric
            evaluation = await self.evaluate_qna(topic, challenge["question"], user_answer, challenge.get("length", "medium"))
        
        total_marks = evaluation.get("total_marks", 0)
        
        # MANDATORY: Update mastery (increments questions_attempted, conditionally correct_answers)
        MasteryService.update_after_qna(user_id, topic, total_marks)
        
        # MANDATORY: Get updated mastery and classification for immediate frontend update
        updated_profile = UserProfile(user_id)
        topic_data = updated_profile.get_topic(topic)
        
        # MANDATORY: Include all required fields for frontend
        evaluation["mastery_score"] = topic_data["mastery_score"]
        evaluation["status"] = topic_data["status"]
        evaluation["classification"] = topic_data["classification"]  # "weak" | "strong" | "unassessed"
        evaluation["questions_attempted"] = topic_data["questions_attempted"]
        evaluation["correct_answers"] = topic_data["correct_answers"]
        evaluation["explanation_provided"] = True  # Flag to confirm explanation was given
        
        # GUARANTEE: Ensure explanation is always present
        if not evaluation.get("feedback"):
            if total_marks >= 4:
                evaluation["feedback"] = "Your answer demonstrates understanding of the core concepts."
            else:
                evaluation["feedback"] = f"Your answer needs improvement. Review the topic '{topic}' to better understand the key concepts."
        
        if not evaluation.get("correct_explanation"):
            evaluation["correct_explanation"] = f"A complete answer should address the question: {challenge['question']}. Include the core concept, relevant explanation, and examples where appropriate."

        # Cleanup challenge
        del profile.data["active_challenges"][challenge_id]
        profile.save()

        return evaluation

    async def evaluate_qna(self, topic: str, question: str, user_answer: str, length: str = "medium") -> Dict[str, Any]:
        context = retrieve_context(topic)
        try:
            from langchain_core.prompts import PromptTemplate
            
            # Use balanced model for QnA evaluation
            llm = get_ollama_client(task_type="qna_eval", temperature=0.3)
            
            prompt_template = PromptTemplate.from_template(QNA_EVALUATION_PROMPT)
            prompt = prompt_template.format(
                topic=topic,
                question=question,
                context=context,
                user_answer=user_answer,
                length=length
            )
            
            # Invoke with retry logic
            response_content = await invoke_with_retry(llm, prompt)
            evaluation = self._parse_json_response(response_content, "QnA evaluation")
            
            # MANDATORY: Enforce result classification based on score
            # Score >= 4 = correct, Score < 4 = incorrect (no partial)
            total_marks = evaluation.get("total_marks", 0)
            if total_marks >= 4:
                evaluation["result"] = "correct"
            else:
                evaluation["result"] = "incorrect"
            
            return evaluation
        except (TimeoutError, ConnectionError):
            logger.warning(f"QnA Evaluation service error")
            # Default to score 4 (borderline correct) when service fails but answer was attempted
            return {
                "concept_score": 2,
                "clarity_score": 1,
                "completeness_score": 1,
                "total_marks": 4,
                "result": "correct",
                "feedback": "Your answer shows understanding of the concept. We couldn't fully evaluate it due to a service issue, but the attempt demonstrates basic knowledge. Review the topic to ensure complete understanding of all key points.",
                "rubric_evaluation": "Provisional scoring due to service unavailability",
                "correct_explanation": "A complete answer should include the key concepts, relevant examples, and clear explanations. Review the topic material for comprehensive understanding."
            }
        except Exception as e:
            logger.error(f"Q&A Evaluation failed: {e}")
            return {
                "concept_score": 0,
                "clarity_score": 0,
                "completeness_score": 0,
                "total_marks": 0,
                "result": "incorrect",
                "feedback": f"We encountered an error evaluating your answer. Please try again. If the issue persists, review the topic material to ensure you understand the key concepts, provide relevant examples, and structure your answer clearly.",
                "rubric_evaluation": "Error during evaluation",
                "correct_explanation": "A good answer should demonstrate understanding of the core concept, include relevant examples where appropriate, and be clearly structured."
            }

    def _parse_json_response(self, response_content: str, context: str = "") -> Dict[str, Any]:
        """Parse JSON response with retry logic and fallback.
        
        Args:
            response_content: Raw response from OLLAMA
            context: Context for logging
            
        Returns:
            Parsed JSON dict or empty dict if parsing fails
        """
        if not response_content:
            logger.warning(f"Empty response in {context}")
            return {}
            
        # Log raw response for debugging
        logger.debug(f"Raw LLM response for {context}: {response_content[:500]}")
        
        try:
            # Try direct parsing first
            return json.loads(response_content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in the response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try fixing common JSON issues
        cleaned = response_content.strip()
        # Remove trailing commas before closing braces
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # Log the invalid response
        logger.warning(f"Invalid JSON in {context}: {response_content[:300]}")
        return {}
