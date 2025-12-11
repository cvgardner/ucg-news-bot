"""Error handling utilities and retry logic for UCG News Bot"""
import asyncio
import functools
import time
from typing import Callable, Optional, Type, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class TwitterAPIError(Exception):
    """Base exception for Twitter API errors"""
    pass


class RateLimitError(TwitterAPIError):
    """Raised when Twitter API rate limit is exceeded"""
    def __init__(self, reset_time: Optional[float] = None):
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded. Reset time: {reset_time}")


class AuthenticationError(TwitterAPIError):
    """Raised when Twitter API authentication fails"""
    pass


class NotFoundError(TwitterAPIError):
    """Raised when Twitter user or resource is not found"""
    pass


class DiscordAPIError(Exception):
    """Base exception for Discord API errors"""
    pass


class MissingPermissionsError(DiscordAPIError):
    """Raised when Discord bot lacks required permissions"""
    pass


class ChannelNotFoundError(DiscordAPIError):
    """Raised when Discord channel is not found"""
    pass


def handle_twitter_error(error) -> TwitterAPIError:
    """
    Convert Twitter API errors to custom exceptions.

    Args:
        error: The exception from Twitter API

    Returns:
        Custom TwitterAPIError exception
    """
    error_str = str(error).lower()

    if "401" in error_str or "unauthorized" in error_str:
        return AuthenticationError(f"Twitter authentication failed: {error}")
    elif "404" in error_str or "not found" in error_str:
        return NotFoundError(f"Twitter user not found: {error}")
    elif "429" in error_str or "rate limit" in error_str:
        return RateLimitError()
    else:
        return TwitterAPIError(f"Twitter API error: {error}")


def handle_discord_error(error) -> Optional[DiscordAPIError]:
    """
    Convert Discord API errors to custom exceptions.

    Args:
        error: The exception from Discord API

    Returns:
        Custom DiscordAPIError exception or None if not a known error
    """
    error_str = str(error).lower()

    if "forbidden" in error_str or "permission" in error_str:
        return MissingPermissionsError(f"Missing Discord permissions: {error}")
    elif "not found" in error_str:
        return ChannelNotFoundError(f"Discord channel not found: {error}")
    else:
        return None
