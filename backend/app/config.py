import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (where this config.py lives)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3"
    
    # Model selection by task type
    MODEL_EXPLANATION: str = "llama3"  # Quality priority
    MODEL_MCQ_EVALUATION: str = "llama3"  # Speed priority
    MODEL_QNA_EVALUATION: str = "llama3"  # Balanced
    MODEL_QUESTION_GENERATION: str = "llama3"  # Quality priority
    MODEL_BRAINSTORM: str = "llama3"  # Planning/reasoning
    
    # Timeouts (seconds)
    OLLAMA_TIMEOUT: int = 30
    MCQ_EVAL_TIMEOUT: int = 5
    GENERATION_TIMEOUT: int = 60
    
    # Retry configuration
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: float = 1.0
    
    # Use absolute paths based on backend directory
    CHROMA_PERSIST_DIRECTORY: str = os.path.join(_BACKEND_DIR, "data", "chroma")
    USER_DATA_DIRECTORY: str = os.path.join(_BACKEND_DIR, "data", "users")
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
