"""
Response streaming and model selection for optimized performance.

Handles:
- Model selection based on task (fast for deterministic, quality for creative)
- Response streaming for long explanations
- Token counting for streaming optimization
"""

from typing import AsyncIterator, Dict, Any, Optional, List
from enum import Enum
from backend.app.utils.logger import logger


class TaskType(Enum):
    """Task types with different performance requirements."""
    
    # Fast deterministic tasks (<1s target)
    MCQ_EVALUATION = "mcq_evaluation"
    QUESTION_EVALUATION = "question_evaluation"
    ANSWER_VALIDATION = "answer_validation"
    ASSESSMENT_SCORING = "assessment_scoring"
    
    # Medium tasks (1-3s target)
    QUESTION_GENERATION = "question_generation"
    QUICK_EXPLANATION = "quick_explanation"
    SUMMARY_GENERATION = "summary_generation"
    
    # Quality tasks (2-5s+ target)
    DETAILED_EXPLANATION = "detailed_explanation"
    REMEDIAL_EXPLANATION = "remedial_explanation"
    CONCEPT_BREAKDOWN = "concept_breakdown"
    TUTORING_RESPONSE = "tutoring_response"


class ModelSelector:
    """
    Selects appropriate LLM model based on task requirements.
    
    Fast models: Smaller, optimized for latency
    Quality models: Larger, optimized for output quality
    """
    
    # Model mappings for different tasks
    FAST_MODELS = {
        TaskType.MCQ_EVALUATION: "neural-chat",  # Fast, deterministic
        TaskType.QUESTION_EVALUATION: "neural-chat",
        TaskType.ANSWER_VALIDATION: "neural-chat",
        TaskType.ASSESSMENT_SCORING: "mistral",  # Fast, good accuracy
        TaskType.QUESTION_GENERATION: "mistral",
    }
    
    QUALITY_MODELS = {
        TaskType.DETAILED_EXPLANATION: "neural-chat-7b-v3-3",  # More detailed
        TaskType.REMEDIAL_EXPLANATION: "neural-chat-7b-v3-3",
        TaskType.CONCEPT_BREAKDOWN: "neural-chat-7b-v3-3",
        TaskType.TUTORING_RESPONSE: "neural-chat-7b-v3-3",
        TaskType.QUICK_EXPLANATION: "mistral",
        TaskType.SUMMARY_GENERATION: "mistral",
    }

    @classmethod
    def select_model(cls, task_type: TaskType) -> str:
        """
        Select model for a task.
        
        Args:
            task_type: Type of task to perform
        
        Returns:
            Model name
        """
        # Try quality models first if task requires quality
        if task_type in cls.QUALITY_MODELS:
            model = cls.QUALITY_MODELS[task_type]
            logger.info(f"Selected quality model {model} for {task_type.value}")
            return model
        
        # Fall back to fast models
        if task_type in cls.FAST_MODELS:
            model = cls.FAST_MODELS[task_type]
            logger.info(f"Selected fast model {model} for {task_type.value}")
            return model
        
        # Default to mistral for unknown tasks
        logger.warning(f"Unknown task type {task_type}, using default model")
        return "mistral"

    @classmethod
    def is_fast_task(cls, task_type: TaskType) -> bool:
        """Check if task should use fast model."""
        return task_type in cls.FAST_MODELS and task_type not in cls.QUALITY_MODELS

    @classmethod
    def should_stream(cls, task_type: TaskType, expected_length: str = "medium") -> bool:
        """
        Determine if response should be streamed.
        
        Stream for:
        - Long explanations
        - Deterministic models with simple output (no streaming needed)
        - User-visible content where progressive display improves UX
        """
        # Always stream quality/long responses
        if task_type in [
            TaskType.DETAILED_EXPLANATION,
            TaskType.REMEDIAL_EXPLANATION,
            TaskType.CONCEPT_BREAKDOWN,
            TaskType.TUTORING_RESPONSE,
        ]:
            return True
        
        # Don't stream for evaluation/scoring (needs complete result)
        if task_type in [
            TaskType.MCQ_EVALUATION,
            TaskType.QUESTION_EVALUATION,
            TaskType.ASSESSMENT_SCORING,
        ]:
            return False
        
        # Stream if expected to be long
        return expected_length in ["long", "detailed"]


class ResponseStreamer:
    """Streams responses from LLM in chunks for progressive display."""
    
    CHUNK_SIZE = 50  # Tokens per chunk
    
    @classmethod
    async def stream_response(
        cls,
        llm,
        prompt: str,
        chunk_size: int = CHUNK_SIZE
    ) -> AsyncIterator[str]:
        """
        Stream LLM response in chunks.
        
        Args:
            llm: LLM instance from get_ollama_client()
            prompt: Prompt to send to LLM
            chunk_size: Approximate tokens per chunk
        
        Yields:
            Text chunks as they are generated
        """
        try:
            from backend.app.llm.ollama_client import invoke_with_retry
            
            # For Ollama, streaming isn't directly available via standard langchain
            # Instead, we can simulate streaming by chunking the response
            response = await invoke_with_retry(llm, prompt)
            
            # Chunk response by approximate token count (words * 1.3)
            words = response.split()
            words_per_chunk = int(chunk_size / 1.3)
            
            for i in range(0, len(words), words_per_chunk):
                chunk = " ".join(words[i:i + words_per_chunk])
                yield chunk
                logger.debug(f"Streamed chunk {i // words_per_chunk + 1}")
        
        except Exception as e:
            logger.error(f"Error in response streaming: {e}")
            yield f"Error generating response: {str(e)}"

    @classmethod
    async def stream_explanation(
        cls,
        llm,
        prompt: str,
        max_streaming_tokens: int = 500
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream explanation with metadata.
        
        Args:
            llm: LLM instance
            prompt: Explanation prompt
            max_streaming_tokens: Max tokens before stopping stream
        
        Yields:
            Dict with text chunk and metadata
        """
        token_count = 0
        
        async for chunk in cls.stream_response(llm, prompt):
            # Estimate tokens (rough calculation: 1 token ≈ 0.77 words)
            chunk_tokens = int(len(chunk.split()) * 1.3)
            token_count += chunk_tokens
            
            yield {
                "chunk": chunk,
                "tokens": chunk_tokens,
                "total_tokens": token_count,
                "done": token_count >= max_streaming_tokens
            }
            
            if token_count >= max_streaming_tokens:
                break


class PerformanceConfig:
    """Performance configuration for different response types."""
    
    # Response timeout in seconds for different task types
    TASK_TIMEOUTS = {
        TaskType.MCQ_EVALUATION: 1.0,
        TaskType.QUESTION_EVALUATION: 1.0,
        TaskType.ASSESSMENT_SCORING: 1.0,
        TaskType.ANSWER_VALIDATION: 1.5,
        TaskType.QUESTION_GENERATION: 3.0,
        TaskType.QUICK_EXPLANATION: 2.0,
        TaskType.SUMMARY_GENERATION: 2.5,
        TaskType.DETAILED_EXPLANATION: 5.0,
        TaskType.REMEDIAL_EXPLANATION: 5.0,
        TaskType.CONCEPT_BREAKDOWN: 5.0,
        TaskType.TUTORING_RESPONSE: 4.0,
    }

    # Cache durations (in hours) for different response types
    CACHE_DURATIONS = {
        TaskType.DETAILED_EXPLANATION: 24,
        TaskType.REMEDIAL_EXPLANATION: 24,
        TaskType.CONCEPT_BREAKDOWN: 24,
        TaskType.QUICK_EXPLANATION: 12,
        TaskType.SUMMARY_GENERATION: 12,
    }

    @classmethod
    def get_timeout(cls, task_type: TaskType) -> float:
        """Get timeout for a task."""
        return cls.TASK_TIMEOUTS.get(task_type, 3.0)

    @classmethod
    def get_cache_duration_hours(cls, task_type: TaskType) -> Optional[int]:
        """Get cache duration for a task, or None if shouldn't be cached."""
        return cls.CACHE_DURATIONS.get(task_type)

    @classmethod
    def should_cache(cls, task_type: TaskType) -> bool:
        """Check if task output should be cached."""
        return task_type in cls.CACHE_DURATIONS


def estimate_response_length(prompt: str) -> str:
    """
    Estimate expected response length based on prompt.
    
    Returns:
        "short" (<100 tokens), "medium" (100-300), or "long" (>300)
    """
    words = len(prompt.split())
    
    if words > 200:
        return "long"
    elif words > 100:
        return "medium"
    else:
        return "short"
