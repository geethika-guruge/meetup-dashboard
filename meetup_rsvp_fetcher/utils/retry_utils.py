"""
Retry utilities with exponential backoff for handling transient failures.

This module provides decorators and utilities for implementing retry logic
with exponential backoff, jitter, and configurable retry conditions.
"""

import time
import random
import logging
from typing import Callable, Type, Union, Tuple, Optional, Any
from functools import wraps
from dataclasses import dataclass
import requests


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_factor: float = 1.0


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


class RetryableError(Exception):
    """Base class for errors that should trigger retries."""
    pass


class NetworkRetryableError(RetryableError):
    """Network-related errors that should be retried."""
    pass


class APIRetryableError(RetryableError):
    """API-related errors that should be retried."""
    pass


class RateLimitError(RetryableError):
    """Rate limiting errors that should be retried with backoff."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


def is_retryable_exception(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the exception should trigger a retry
    """
    # Always retry RetryableError and its subclasses
    if isinstance(exception, RetryableError):
        return True
    
    # Retry specific requests exceptions
    if isinstance(exception, requests.exceptions.RequestException):
        # Retry on connection errors, timeouts, and server errors
        if isinstance(exception, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError
        )):
            # For HTTP errors, only retry on server errors (5xx)
            if isinstance(exception, requests.exceptions.HTTPError):
                if hasattr(exception, 'response') and exception.response:
                    return 500 <= exception.response.status_code < 600
                return True  # Retry if we can't determine status code
            return True
    
    # Don't retry other exceptions by default
    return False


def calculate_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: Optional[int] = None
) -> float:
    """
    Calculate delay before next retry attempt.
    
    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration
        retry_after: Optional retry-after value from rate limiting
        
    Returns:
        Delay in seconds before next attempt
    """
    if retry_after is not None:
        # Respect rate limiting retry-after header
        base_delay = max(retry_after, config.base_delay)
    else:
        # Calculate exponential backoff
        base_delay = config.base_delay * (config.exponential_base ** attempt)
    
    # Apply backoff factor
    delay = base_delay * config.backoff_factor
    
    # Cap at maximum delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to avoid thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Decorator that adds retry logic with exponential backoff to a function.
    
    Args:
        config: Retry configuration (uses defaults if None)
        retryable_exceptions: Tuple of exception types to retry on
        logger: Logger for retry attempts (creates one if None)
        
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()
    
    if retryable_exceptions is None:
        retryable_exceptions = (RetryableError, requests.exceptions.RequestException)
    
    if logger is None:
        logger = logging.getLogger(__name__)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should trigger a retry
                    should_retry = (
                        isinstance(e, retryable_exceptions) or
                        is_retryable_exception(e)
                    )
                    
                    if not should_retry or attempt == config.max_attempts - 1:
                        # Don't retry this exception or we've exhausted attempts
                        break
                    
                    # Calculate delay
                    retry_after = None
                    if isinstance(e, RateLimitError):
                        retry_after = e.retry_after
                    
                    delay = calculate_delay(attempt, config, retry_after)
                    
                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: "
                        f"{type(e).__name__}: {str(e)}. Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # All attempts failed
            error_msg = (
                f"All {config.max_attempts} retry attempts failed for {func.__name__}. "
                f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
            )
            logger.error(error_msg)
            raise RetryError(error_msg, last_exception, config.max_attempts)
        
        return wrapper
    return decorator


class RetrySession:
    """HTTP session with built-in retry logic."""
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        session: Optional[requests.Session] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize retry session.
        
        Args:
            config: Retry configuration
            session: Optional existing session to wrap
            logger: Logger for retry attempts
        """
        self.config = config or RetryConfig()
        self.session = session or requests.Session()
        self.logger = logger or logging.getLogger(__name__)
    
    def _make_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            Response object
            
        Raises:
            RetryError: If all retry attempts fail
        """
        @retry_with_backoff(
            config=self.config,
            logger=self.logger
        )
        def make_request():
            response = self.session.request(method, url, **kwargs)
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = None
                if 'Retry-After' in response.headers:
                    try:
                        retry_after = int(response.headers['Retry-After'])
                    except ValueError:
                        pass
                raise RateLimitError(
                    f"Rate limit exceeded (429): {response.text}",
                    retry_after=retry_after
                )
            
            # Check for server errors
            if 500 <= response.status_code < 600:
                raise APIRetryableError(
                    f"Server error ({response.status_code}): {response.text}"
                )
            
            # Raise for other HTTP errors (4xx won't be retried)
            response.raise_for_status()
            
            return response
        
        return make_request()
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request with retry logic."""
        return self._make_request_with_retry('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make POST request with retry logic."""
        return self._make_request_with_retry('POST', url, **kwargs)
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """Make PUT request with retry logic."""
        return self._make_request_with_retry('PUT', url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """Make DELETE request with retry logic."""
        return self._make_request_with_retry('DELETE', url, **kwargs)
    
    def close(self):
        """Close the underlying session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience functions for common retry scenarios
def retry_api_call(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """Decorator for API calls with standard retry configuration."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True
    )
    return retry_with_backoff(config=config)


def retry_network_call(
    max_attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 30.0
):
    """Decorator for network calls with aggressive retry configuration."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=1.5,
        jitter=True
    )
    return retry_with_backoff(config=config)