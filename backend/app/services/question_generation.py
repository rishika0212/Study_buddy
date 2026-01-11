"""
Background question generation system for pre-loading questions before assessment starts.

Generates questions in background when topic is added, caches them, and serves from pool
during assessment. Results in near-zero assessment start latency.
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.config import settings
from backend.app.utils.logger import logger
from backend.app.llm.ollama_client import get_ollama_client, invoke_with_retry
from backend.app.llm.prompts import MCQ_GENERATION_PROMPT, QNA_GENERATION_PROMPT


class QuestionPool:
    """Manages a pool of pre-generated questions for assessments."""
    
    def __init__(self, user_id: str):
        """
        Initialize question pool for a user.
        
        Args:
            user_id: User identifier (session_id is DEPRECATED and removed)
        """
        self.user_id = user_id
        self.pool_dir = os.path.join(settings.USER_DATA_DIRECTORY, "question_pools")
        os.makedirs(self.pool_dir, exist_ok=True)
        self.pool_file = os.path.join(self.pool_dir, f"{user_id}_questions.json")
        self._load_pool()

    def _load_pool(self):
        """Load question pool from disk."""
        if os.path.exists(self.pool_file):
            try:
                with open(self.pool_file, "r") as f:
                    self.pool = json.load(f)
            except Exception as e:
                logger.error(f"Error loading question pool: {e}")
                self.pool = {}
        else:
            self.pool = {}

    def _save_pool(self):
        """Save question pool to disk."""
        try:
            with open(self.pool_file, "w") as f:
                json.dump(self.pool, f)
        except Exception as e:
            logger.error(f"Error saving question pool: {e}")

    def add_topic_questions(self, topic: str, questions: List[Dict[str, Any]], question_type: str = "mcq"):
        """
        Add pre-generated questions for a topic.
        
        Args:
            topic: Topic name
            questions: List of generated questions
            question_type: Type of questions (mcq, qna)
        """
        if topic not in self.pool:
            self.pool[topic] = {"mcq": [], "qna": [], "generated_at": datetime.now().isoformat()}
        
        self.pool[topic][question_type] = questions
        self._save_pool()
        logger.info(f"Added {len(questions)} {question_type} questions for {topic}")

    def get_next_question(self, topic: str, question_type: str = "mcq") -> Optional[Dict[str, Any]]:
        """
        Get the next question from the pool for a topic.
        
        Args:
            topic: Topic name
            question_type: Type of question (mcq, qna)
        
        Returns:
            Next question dict or None if pool is empty
        """
        if topic not in self.pool or not self.pool[topic].get(question_type):
            return None
        
        questions = self.pool[topic][question_type]
        if not questions:
            return None
        
        # Get first question and remove it from pool
        question = questions.pop(0)
        self._save_pool()
        
        logger.info(f"Retrieved question for {topic} ({question_type}), {len(questions)} remaining")
        return question

    def get_pool_status(self, topic: str) -> Dict[str, int]:
        """Get count of available questions in pool for a topic."""
        if topic not in self.pool:
            return {"mcq": 0, "qna": 0}
        
        return {
            "mcq": len(self.pool[topic].get("mcq", [])),
            "qna": len(self.pool[topic].get("qna", []))
        }

    def clear_topic_pool(self, topic: str):
        """Clear all questions for a topic."""
        if topic in self.pool:
            del self.pool[topic]
            self._save_pool()
            logger.info(f"Cleared question pool for {topic}")

    def clear_all(self):
        """Clear entire question pool."""
        self.pool = {}
        if os.path.exists(self.pool_file):
            os.remove(self.pool_file)
        logger.info(f"Cleared entire question pool for {self.user_id}")


class BackgroundQuestionGenerator:
    """Generates questions in background for topics."""
    
    def __init__(self):
        self.generation_tasks: Dict[str, asyncio.Task] = {}

    async def generate_questions_for_topic(
        self,
        user_id: str,
        topic: str,
        mastery: float = 0.0,
        count: int = 20,
        question_type: str = "mcq"
    ) -> List[Dict[str, Any]]:
        """
        Generate a pool of questions for a topic.
        
        Args:
            user_id: User ID
            topic: Topic name
            mastery: Current mastery level (0-1) for difficulty selection
            count: Number of questions to generate
            question_type: Type of questions (mcq, qna)
        
        Returns:
            List of generated questions
        """
        logger.info(f"Starting background generation of {count} {question_type} questions for {topic}")
        
        try:
            from backend.app.vectorstore.retriever import retrieve_context
            
            # Determine difficulty based on mastery
            if mastery >= 0.9:
                difficulty = "mastery"
            elif mastery >= 0.7:
                difficulty = "proficient"
            elif mastery >= 0.4:
                difficulty = "developing"
            else:
                difficulty = "beginner"
            
            context = retrieve_context(topic)
            
            # Use fast model for question generation
            llm = get_ollama_client(task_type="question_generation")
            
            questions = []
            for i in range(count):
                try:
                    if question_type == "mcq":
                        prompt = self._format_mcq_prompt(topic, difficulty, mastery, context, i + 1, count)
                    else:
                        prompt = self._format_qna_prompt(topic, difficulty, mastery, context, i + 1, count)
                    
                    response = await invoke_with_retry(llm, prompt)
                    question = self._parse_question_response(response, question_type)
                    
                    if question:
                        questions.append(question)
                        logger.debug(f"Generated question {i + 1}/{count} for {topic}")
                    
                    # Small delay to avoid overwhelming the model
                    await asyncio.sleep(0.1)
                
                except Exception as e:
                    logger.warning(f"Failed to generate question {i + 1}/{count} for {topic}: {e}")
                    continue
            
            logger.info(f"Successfully generated {len(questions)}/{count} questions for {topic}")
            
            # Save to pool
            pool = QuestionPool(user_id)
            pool.add_topic_questions(topic, questions, question_type)
            
            return questions
        
        except Exception as e:
            logger.error(f"Error in background question generation: {e}")
            return []

    def start_background_generation(
        self,
        user_id: str,
        topic: str,
        mastery: float = 0.0
    ) -> str:
        """
        Start background question generation as a non-blocking task.
        
        Args:
            user_id: User ID
            topic: Topic name
            mastery: Current mastery level
        
        Returns:
            Task ID for monitoring
        """
        task_id = f"{user_id}:{topic}"
        
        # Don't start if already generating for this topic
        if task_id in self.generation_tasks and not self.generation_tasks[task_id].done():
            logger.info(f"Question generation already in progress for {task_id}")
            return task_id
        
        # Start background task
        loop = asyncio.get_event_loop()
        task = loop.create_task(
            self.generate_questions_for_topic(user_id, topic, mastery, count=20, question_type="mcq")
        )
        self.generation_tasks[task_id] = task
        
        logger.info(f"Started background question generation task: {task_id}")
        return task_id

    def get_generation_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a generation task."""
        if task_id not in self.generation_tasks:
            return {"status": "not_found"}
        
        task = self.generation_tasks[task_id]
        return {
            "status": "pending" if not task.done() else "completed",
            "done": task.done()
        }

    def _format_mcq_prompt(
        self,
        topic: str,
        difficulty: str,
        mastery: float,
        context: str,
        question_num: int,
        total: int
    ) -> str:
        """Format MCQ generation prompt."""
        return MCQ_GENERATION_PROMPT.format(
            topic=topic,
            difficulty=difficulty,
            mastery=mastery,
            context=context,
            instruction=f"Generate question {question_num}/{total} with unique content different from any previous questions for this topic."
        )

    def _format_qna_prompt(
        self,
        topic: str,
        difficulty: str,
        mastery: float,
        context: str,
        question_num: int,
        total: int
    ) -> str:
        """Format QnA generation prompt."""
        return QNA_GENERATION_PROMPT.format(
            topic=topic,
            difficulty=difficulty,
            mastery=mastery,
            context=context,
            instruction=f"Generate question {question_num}/{total} with unique content different from any previous questions for this topic."
        )

    def _parse_question_response(self, response: str, question_type: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into question object."""
        try:
            import json
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            data = json.loads(json_str)
            
            # Validate required fields based on question type
            if question_type == "mcq":
                required = ["question", "options", "correct_answer"]
            else:
                required = ["question"]
            
            if all(field in data for field in required):
                return data
            
            logger.warning(f"Parsed question missing required fields: {data}")
            return None
        
        except Exception as e:
            logger.warning(f"Failed to parse question response: {e}")
            return None


# Global instance
_question_generator = None


def get_question_generator() -> BackgroundQuestionGenerator:
    """Get or create global question generator instance."""
    global _question_generator
    if _question_generator is None:
        _question_generator = BackgroundQuestionGenerator()
    return _question_generator
