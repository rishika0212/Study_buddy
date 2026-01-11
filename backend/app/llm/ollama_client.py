import asyncio
import json
from typing import Optional, Dict, Any
from langchain_ollama import ChatOllama
from backend.app.config import settings
from backend.app.utils.logger import logger

class OllamaClientManager:
    """Manages OLLAMA client instances with model selection and error handling."""
    
    # Model availability cache
    _available_models: Optional[Dict[str, bool]] = None
    
    @staticmethod
    def get_client(
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> ChatOllama:
        """Create an OLLAMA client with the specified model.
        
        Args:
            model: Model name. Defaults to settings.LLM_MODEL
            temperature: Temperature for generation
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
        """
        if model is None:
            model = settings.LLM_MODEL
        
        if timeout is None:
            timeout = settings.OLLAMA_TIMEOUT
        
        return ChatOllama(
            model=model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    
    @staticmethod
    def get_model_for_task(task_type: str) -> str:
        """Get the optimal model for a specific task type.
        
        Args:
            task_type: Type of task (explanation, mcq_eval, qna_eval, generation, brainstorm)
        
        Returns:
            Model name string
        """
        task_models = {
            "explanation": settings.MODEL_EXPLANATION,
            "mcq_eval": settings.MODEL_MCQ_EVALUATION,
            "mcq_generation": settings.MODEL_QUESTION_GENERATION,
            "qna_eval": settings.MODEL_QNA_EVALUATION,
            "qna_generation": settings.MODEL_QUESTION_GENERATION,
            "brainstorm": settings.MODEL_BRAINSTORM,
            "planning": settings.MODEL_BRAINSTORM,
        }
        return task_models.get(task_type, settings.LLM_MODEL)
    
    @staticmethod
    def get_timeout_for_task(task_type: str) -> int:
        """Get the appropriate timeout for a task type.
        
        Args:
            task_type: Type of task
        
        Returns:
            Timeout in seconds
        """
        if "eval" in task_type:
            return settings.MCQ_EVAL_TIMEOUT
        elif "generation" in task_type:
            return settings.GENERATION_TIMEOUT
        else:
            return settings.OLLAMA_TIMEOUT

def get_ollama_client(
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    task_type: Optional[str] = None
) -> ChatOllama:
    """Convenience function to get an OLLAMA client.
    
    Args:
        temperature: Temperature for generation
        max_tokens: Maximum tokens
        task_type: Task type for automatic model/timeout selection
    
    Returns:
        ChatOllama instance
    """
    model = OllamaClientManager.get_model_for_task(task_type) if task_type else None
    timeout = OllamaClientManager.get_timeout_for_task(task_type) if task_type else None
    return OllamaClientManager.get_client(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

async def invoke_with_retry(
    client: ChatOllama,
    prompt,
    max_retries: int = settings.RETRY_ATTEMPTS,
    retry_delay: float = settings.RETRY_DELAY
) -> str:
    """Invoke OLLAMA client with automatic retry logic.
    
    Args:
        client: ChatOllama instance
        prompt: Prompt text (str) or list of messages from ChatPromptTemplate
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Response content string
    
    Raises:
        ConnectionError: If connection fails after retries
        TimeoutError: If request times out
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Handle list of messages (from ChatPromptTemplate.format_messages())
            # ChatOllama.ainvoke can accept both strings and list of BaseMessage
            response = await client.ainvoke(prompt)
            return response.content
        except TimeoutError as e:
            last_error = e
            logger.warning(f"OLLAMA timeout (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        except ConnectionError as e:
            last_error = e
            logger.warning(f"OLLAMA connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        except Exception as e:
            last_error = e
            logger.error(f"OLLAMA error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    if isinstance(last_error, TimeoutError):
        raise TimeoutError(
            f"OLLAMA request timed out after {max_retries} attempts. "
            f"Ensure Ollama is running and not overloaded."
        )
    else:
        raise ConnectionError(
            f"Failed to connect to OLLAMA after {max_retries} attempts. "
            f"Ensure Ollama is running at {settings.OLLAMA_BASE_URL}"
        )
