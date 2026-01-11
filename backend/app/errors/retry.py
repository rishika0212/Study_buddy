"""
Retry utility functions with exponential backoff.
Implements resilience patterns for storage and service operations.
"""

import time
import asyncio
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

from backend.app.errors.exceptions import (
    StorageFailureError,
    ExternalServiceError,
)
from backend.app.errors.logging import log_retry_attempt


T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exception_types: tuple = (Exception,),
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds (exponentially increased)
        max_delay: Maximum delay cap in seconds
        exception_types: Tuple of exception types to catch and retry on
    
    Returns:
        Decorated function that retries on failure
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        raise
                    
                    # Calculate exponential backoff
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    log_retry_attempt(
                        operation=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=e
                    )
                    
                    time.sleep(delay)
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exception_types: tuple = (Exception,),
):
    """
    Async version of retry_with_backoff decorator.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds (exponentially increased)
        max_delay: Maximum delay cap in seconds
        exception_types: Tuple of exception types to catch and retry on
    
    Returns:
        Decorated async function that retries on failure
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        raise
                    
                    # Calculate exponential backoff
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    log_retry_attempt(
                        operation=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=e
                    )
                    
                    await asyncio.sleep(delay)
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def save_with_retry(
    save_func: Callable[[], Any],
    operation_name: str = "save",
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """
    Retry a save operation with exponential backoff and rollback on failure.
    
    Args:
        save_func: Function that performs the save operation
        operation_name: Name of the operation for logging
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
    
    Returns:
        Result of save_func
    
    Raises:
        StorageFailureError: If all retry attempts fail
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = save_func()
            return result
        except Exception as e:
            last_exception = e
            
            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                log_retry_attempt(
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=e
                )
                time.sleep(delay)
    
    # All retries failed
    raise StorageFailureError(
        message=f"Could not {operation_name}. Try again.",
        operation=operation_name,
        retry_count=max_attempts
    )


async def async_save_with_retry(
    save_func: Callable[[], Any],
    operation_name: str = "save",
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """
    Async version of save_with_retry.
    
    Args:
        save_func: Sync or async function that performs the save operation
        operation_name: Name of the operation for logging
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
    
    Returns:
        Result of save_func
    
    Raises:
        StorageFailureError: If all retry attempts fail
    """
    import inspect
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Handle both sync and async save functions
            if inspect.iscoroutinefunction(save_func):
                result = await save_func()
            else:
                result = save_func()
            return result
        except Exception as e:
            last_exception = e
            
            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                log_retry_attempt(
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=e
                )
                await asyncio.sleep(delay)
    
    # All retries failed
    raise StorageFailureError(
        message=f"Could not {operation_name}. Try again.",
        operation=operation_name,
        retry_count=max_attempts
    )


def external_service_retry(
    service_name: str = "External Service",
    max_attempts: int = 3,
    base_delay: float = 2.0,
):
    """
    Decorator for retrying external service calls with service-specific error handling.
    
    Args:
        service_name: Name of the external service
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        raise ExternalServiceError(
                            message=f"Failed to connect to {service_name}",
                            service_name=service_name,
                            retry_count=max_attempts
                        )
                    
                    delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                    log_retry_attempt(
                        operation=f"{service_name}_call",
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=e
                    )
                    
                    time.sleep(delay)
            
            if last_exception:
                raise ExternalServiceError(
                    message=f"Failed to connect to {service_name}",
                    service_name=service_name,
                    retry_count=max_attempts
                )
                
        return wrapper
    return decorator


def async_external_service_retry(
    service_name: str = "External Service",
    max_attempts: int = 3,
    base_delay: float = 2.0,
):
    """
    Async version of external_service_retry decorator.
    
    Args:
        service_name: Name of the external service
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
    
    Returns:
        Decorated async function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        raise ExternalServiceError(
                            message=f"Failed to connect to {service_name}",
                            service_name=service_name,
                            retry_count=max_attempts
                        )
                    
                    delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                    log_retry_attempt(
                        operation=f"{service_name}_call",
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=e
                    )
                    
                    await asyncio.sleep(delay)
            
            if last_exception:
                raise ExternalServiceError(
                    message=f"Failed to connect to {service_name}",
                    service_name=service_name,
                    retry_count=max_attempts
                )
                
        return wrapper
    return decorator
