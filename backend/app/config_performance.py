"""
Performance Optimization Configuration

Centralized configuration for all performance-related settings.
Adjust these values to tune performance for your deployment.
"""

from enum import Enum
from typing import Dict


class PerformanceConfig:
    """Master performance configuration."""
    
    # ==================== Caching Configuration ====================
    
    # Explanation cache settings
    EXPLANATION_CACHE_TTL_HOURS = 24
    EXPLANATION_CACHE_MIN_LENGTH = 200  # Only cache explanations > 200 chars
    
    # Question pool cache settings
    QUESTION_POOL_SIZE = 20  # Number of questions to pre-generate per topic
    QUESTION_POOL_REFILL_THRESHOLD = 5  # Trigger refill when pool drops below this
    
    # ==================== Lazy Loading Configuration ====================
    
    # Pagination settings
    CONVERSATION_HISTORY_PAGE_SIZE = 50
    MAX_TOPICS_IN_MEMORY = 100  # Load max topics before requiring pagination
    
    # Session metadata loading
    LAZY_LOAD_PROFILE = True  # Only load profile when explicitly requested
    LAZY_LOAD_HISTORY = True  # Only load conversation history when needed
    
    # ==================== Model Selection ====================
    
    # Model timeouts (seconds)
    TASK_TIMEOUTS = {
        "mcq_evaluation": 1.0,
        "question_evaluation": 1.0,
        "assessment_scoring": 1.0,
        "answer_validation": 1.5,
        "question_generation": 3.0,
        "quick_explanation": 2.0,
        "summary_generation": 2.5,
        "detailed_explanation": 5.0,
        "remedial_explanation": 5.0,
        "concept_breakdown": 5.0,
        "tutoring_response": 4.0,
    }
    
    # Model assignments
    FAST_MODELS = {
        "mcq_evaluation": "neural-chat",
        "question_evaluation": "neural-chat",
        "answer_validation": "neural-chat",
        "assessment_scoring": "mistral",
        "question_generation": "mistral",
    }
    
    QUALITY_MODELS = {
        "detailed_explanation": "neural-chat-7b-v3-3",
        "remedial_explanation": "neural-chat-7b-v3-3",
        "concept_breakdown": "neural-chat-7b-v3-3",
        "tutoring_response": "neural-chat-7b-v3-3",
        "quick_explanation": "mistral",
        "summary_generation": "mistral",
    }
    
    # ==================== Streaming Configuration ====================
    
    # Response streaming
    STREAMING_CHUNK_SIZE_TOKENS = 50  # Tokens per stream chunk
    STREAMING_MIN_LENGTH = 300  # Only stream responses > 300 chars
    STREAMING_CHUNK_DELAY_MS = 10  # Delay between chunks for UX
    
    # ==================== Performance Targets ====================
    
    PERFORMANCE_TARGETS_MS = {
        "simple_queries": 500,      # view progress, list topics
        "explanations": 2000,       # detailed explanations
        "question_generation": 3000,
        "mcq_evaluation": 1000,
        "qna_evaluation": 3000,
        "session_loading": 1000,
    }
    
    # ==================== Background Task Configuration ====================
    
    # Question generation
    BACKGROUND_QUESTION_BATCH_SIZE = 20
    BACKGROUND_QUESTION_BATCH_DELAY_MS = 100  # Delay between questions
    MAX_CONCURRENT_GENERATION_TASKS = 5
    
    # ==================== Monitoring Configuration ====================
    
    # Performance monitoring
    METRICS_RETENTION_DAYS = 7
    METRICS_FLUSH_INTERVAL_SECONDS = 60
    MONITOR_ALL_ENDPOINTS = True
    
    # Alert thresholds
    SLOW_RESPONSE_THRESHOLD_MS = 3000
    HIGH_CACHE_MISS_RATE = 0.3  # Alert if > 30% miss rate
    
    # ==================== Debug/Development ====================
    
    # Set to True to log all performance data (high overhead)
    VERBOSE_PERFORMANCE_LOGGING = False
    
    # Set to True to disable caching (testing only)
    DISABLE_CACHING = False
    
    # Set to True to use synchronous generation instead of background
    FORCE_SYNCHRONOUS_GENERATION = False
    
    # ==================== Helper Methods ====================
    
    @classmethod
    def get_model_for_task(cls, task_type: str, prefer_quality: bool = False) -> str:
        """
        Get model name for a task.
        
        Args:
            task_type: Type of task (e.g., "mcq_evaluation", "detailed_explanation")
            prefer_quality: If True, prefer quality models over speed
        
        Returns:
            Model name
        """
        if task_type in cls.QUALITY_MODELS:
            return cls.QUALITY_MODELS[task_type]
        elif task_type in cls.FAST_MODELS:
            return cls.FAST_MODELS[task_type]
        else:
            return "mistral"  # Default
    
    @classmethod
    def get_timeout_for_task(cls, task_type: str) -> float:
        """Get timeout in seconds for a task."""
        return cls.TASK_TIMEOUTS.get(task_type, 3.0)
    
    @classmethod
    def get_performance_target(cls, endpoint: str) -> int:
        """Get performance target in milliseconds for an endpoint."""
        endpoint_lower = endpoint.lower()
        
        if "chat" in endpoint_lower or "message" in endpoint_lower:
            return cls.PERFORMANCE_TARGETS_MS["explanations"]
        elif "mcq" in endpoint_lower:
            return (cls.PERFORMANCE_TARGETS_MS["question_generation"] 
                   if "generate" in endpoint_lower
                   else cls.PERFORMANCE_TARGETS_MS["mcq_evaluation"])
        elif "qna" in endpoint_lower:
            return (cls.PERFORMANCE_TARGETS_MS["question_generation"] 
                   if "generate" in endpoint_lower
                   else cls.PERFORMANCE_TARGETS_MS["qna_evaluation"])
        else:
            return cls.PERFORMANCE_TARGETS_MS["session_loading"]
    
    @classmethod
    def should_stream_response(cls, response_length: int, task_type: str = None) -> bool:
        """Determine if response should be streamed."""
        return response_length > cls.STREAMING_MIN_LENGTH
    
    @classmethod
    def should_cache_response(cls, task_type: str, response_length: int) -> bool:
        """Determine if response should be cached."""
        if task_type in ["mcq_evaluation", "assessment_scoring"]:
            return False  # Don't cache evaluation results
        
        return response_length > cls.EXPLANATION_CACHE_MIN_LENGTH


# ==================== Preset Configurations ====================

class DeploymentPreset(Enum):
    """Preset configurations for different deployments."""
    
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    LOW_RESOURCE = "low_resource"
    HIGH_THROUGHPUT = "high_throughput"


def get_preset_config(preset: DeploymentPreset) -> Dict:
    """Get configuration preset for a deployment type."""
    presets = {
        DeploymentPreset.DEVELOPMENT: {
            "VERBOSE_PERFORMANCE_LOGGING": True,
            "DISABLE_CACHING": False,
            "QUESTION_POOL_SIZE": 10,
            "METRICS_RETENTION_DAYS": 1,
        },
        DeploymentPreset.PRODUCTION: {
            "VERBOSE_PERFORMANCE_LOGGING": False,
            "DISABLE_CACHING": False,
            "QUESTION_POOL_SIZE": 20,
            "METRICS_RETENTION_DAYS": 7,
            "MAX_CONCURRENT_GENERATION_TASKS": 10,
        },
        DeploymentPreset.LOW_RESOURCE: {
            "QUESTION_POOL_SIZE": 5,
            "CONVERSATION_HISTORY_PAGE_SIZE": 25,
            "MAX_CONCURRENT_GENERATION_TASKS": 2,
            "FORCE_SYNCHRONOUS_GENERATION": True,
        },
        DeploymentPreset.HIGH_THROUGHPUT: {
            "QUESTION_POOL_SIZE": 50,
            "MAX_CONCURRENT_GENERATION_TASKS": 20,
            "STREAMING_CHUNK_SIZE_TOKENS": 100,
            "METRICS_RETENTION_DAYS": 14,
        },
    }
    
    return presets.get(preset, {})


# ==================== Configuration Validation ====================

def validate_config() -> bool:
    """Validate performance configuration."""
    errors = []
    
    # Validate question pool size
    if PerformanceConfig.QUESTION_POOL_SIZE < 5:
        errors.append("QUESTION_POOL_SIZE must be at least 5")
    
    # Validate timeouts are positive
    for task, timeout in PerformanceConfig.TASK_TIMEOUTS.items():
        if timeout <= 0:
            errors.append(f"Timeout for {task} must be positive")
    
    # Validate streaming chunk size
    if PerformanceConfig.STREAMING_CHUNK_SIZE_TOKENS < 10:
        errors.append("STREAMING_CHUNK_SIZE_TOKENS must be at least 10")
    
    if errors:
        print("Configuration validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


if __name__ == "__main__":
    # Test configuration
    if validate_config():
        print("✓ Configuration is valid")
        print(f"\nPerformance Targets:")
        for target, ms in PerformanceConfig.PERFORMANCE_TARGETS_MS.items():
            print(f"  {target}: {ms}ms")
    else:
        print("✗ Configuration has errors")
