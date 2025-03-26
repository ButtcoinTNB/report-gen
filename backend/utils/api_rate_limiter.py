"""
API rate limiter for external API services like OpenRouter.
Implements token bucket algorithm for fair rate limiting with burst capacity.
"""

import asyncio
import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Function to set up rate limiters
def setup_rate_limiters():
    """
    Initialize the API rate limiters.
    This function should be called during application startup.
    """
    rate_limiter = ApiRateLimiter.get_instance()
    rate_limiter.initialize()


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    Allows for bursts of activity while maintaining long-term rate limits.
    """

    def __init__(
        self,
        rate: float,
        capacity: float,
        initial_tokens: Optional[float] = None,
        name: str = "default",
    ):
        """
        Initialize a token bucket.

        Args:
            rate: Tokens per second to refill
            capacity: Maximum number of tokens the bucket can hold
            initial_tokens: Initial number of tokens (defaults to capacity)
            name: Name for this bucket for logging
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity if initial_tokens is None else initial_tokens
        self.last_refill = time.time()
        self.name = name
        self.last_used = time.time()
        self.metrics = {
            "total_requests": 0,
            "throttled_requests": 0,
            "last_allowed_time": time.time(),
            "last_throttled_time": None,
        }
        self._lock = threading.RLock()  # Add a lock for thread safety
        logger.info(
            f"Initialized rate limiter '{name}': {rate} requests/sec, capacity {capacity}"
        )

    def _refill(self):
        """Refill tokens based on elapsed time (without locking)"""
        # Note: This method is called within methods that already acquire the lock
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add based on elapsed time and rate
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        with self._lock:
            self._refill()
            self.metrics["total_requests"] += 1
            self.last_used = time.time()

            if self.tokens >= tokens:
                self.tokens -= tokens
                self.metrics["last_allowed_time"] = time.time()
                return True
            else:
                self.metrics["throttled_requests"] += 1
                self.metrics["last_throttled_time"] = time.time()
                return False

    async def consume_or_wait(
        self, tokens: float = 1.0, max_wait: float = 10.0
    ) -> bool:
        """
        Consume tokens or wait until they're available, up to max_wait seconds.

        Args:
            tokens: Number of tokens to consume
            max_wait: Maximum seconds to wait

        Returns:
            True if tokens were consumed, False if timed out
        """
        start_time = time.time()

        while True:
            # Try to consume tokens with lock
            with self._lock:
                self._refill()
                self.last_used = time.time()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    self.metrics["last_allowed_time"] = time.time()
                    return True

                # Check if we've exceeded maximum wait time
                elapsed = time.time() - start_time
                if elapsed >= max_wait:
                    self.metrics["throttled_requests"] += 1
                    self.metrics["last_throttled_time"] = time.time()
                    return False

                # Calculate wait time until we'll have enough tokens
                wait_time = (tokens - self.tokens) / self.rate
                # Clamp to reasonable wait times
                wait_time = min(max(0.01, wait_time), max_wait - elapsed)

            # Wait outside the lock to avoid blocking other threads
            await asyncio.sleep(wait_time)

    def reset_metrics(self) -> None:
        """Reset metrics counters"""
        with self._lock:
            self.metrics = {
                "total_requests": 0,
                "throttled_requests": 0,
                "last_allowed_time": time.time(),
                "last_throttled_time": None,
            }


class ApiRateLimiter:
    """
    API rate limiter for different services and endpoints.
    Supports multiple named limiters for different API services.
    """

    # Singleton instance
    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of ApiRateLimiter

        Returns:
            The singleton ApiRateLimiter instance
        """
        if cls._instance is None:
            cls._instance = ApiRateLimiter()
        return cls._instance

    def __init__(self):
        """Initialize the rate limiter with default buckets"""
        self.limiters: Dict[str, TokenBucket] = {}
        self._lock = threading.RLock()  # Add a lock for thread safety
        self.initialized = False
        self.default_rate = 5.0  # 5 requests per second
        self.default_capacity = 10.0  # Allow bursts of 10 requests

    async def start(self):
        """Initialize and start the rate limiter"""
        self.initialize()

    async def stop(self):
        """Stop the rate limiter and clean up resources"""
        pass

    def initialize(self):
        """Initialize default rate limiters"""
        with self._lock:
            if self.initialized:
                return

            # OpenRouter has tiered rate limits depending on the plan
            # Default to conservative limits (free tier)
            self.add_limiter("openrouter", 1.0, 5.0)  # 1 req/s with bursts up to 5

            # Add any other API services here
            self.add_limiter("supabase", 5.0, 10.0)  # 5 req/s with bursts up to 10

            self.initialized = True
            logger.info("API rate limiters initialized")

    def add_limiter(self, name: str, rate: float, capacity: float):
        """
        Add a new named rate limiter.

        Args:
            name: Name of the limiter
            rate: Tokens per second to refill
            capacity: Maximum number of tokens the bucket can hold
        """
        with self._lock:
            self.limiters[name] = TokenBucket(rate, capacity, name=name)
            logger.debug(
                f"Added rate limiter '{name}': {rate} req/s, capacity {capacity}"
            )

    def get_limiter(self, name: str) -> TokenBucket:
        """
        Get a rate limiter by name, creating one if it doesn't exist.

        Args:
            name: Name of the limiter

        Returns:
            The requested TokenBucket
        """
        if not self.initialized:
            self.initialize()

        with self._lock:
            if name not in self.limiters:
                logger.warning(
                    f"Rate limiter '{name}' not found, creating with default settings"
                )
                self.add_limiter(name, self.default_rate, self.default_capacity)

            return self.limiters[name]

    def allow_request(self, name: str, tokens: float = 1.0) -> bool:
        """
        Check if a request should be allowed.

        Args:
            name: Name of the rate limiter to use
            tokens: Number of tokens to consume

        Returns:
            True if the request is allowed, False otherwise
        """
        return self.get_limiter(name).consume(tokens)

    async def wait_for_token(
        self, name: str, tokens: float = 1.0, max_wait: float = 10.0
    ) -> bool:
        """
        Wait for tokens to become available, with a maximum wait time.

        Args:
            name: Name of the rate limiter to use
            tokens: Number of tokens to consume
            max_wait: Maximum seconds to wait

        Returns:
            True if tokens were consumed, False if timed out
        """
        return await self.get_limiter(name).consume_or_wait(tokens, max_wait)

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all limiters"""
        with self._lock:
            return {
                name: limiter.metrics.copy() for name, limiter in self.limiters.items()
            }

    def reset_metrics(self) -> None:
        """Reset metrics for all limiters"""
        with self._lock:
            for limiter in self.limiters.values():
                limiter.reset_metrics()
        logger.info("Rate limiter metrics reset")

    def cleanup_stale_limiters(self, max_age_seconds: int = 3600) -> List[str]:
        """
        Remove limiters that haven't been used for a specified period

        Args:
            max_age_seconds: Maximum age in seconds before a limiter is considered stale

        Returns:
            List of removed limiter names
        """
        now = time.time()
        stale_limiters = []

        with self._lock:
            # First identify stale limiters (except default ones)
            for name, limiter in list(self.limiters.items()):
                # Don't remove built-in limiters
                if name in ["openrouter", "supabase"]:
                    continue

                if now - limiter.last_used > max_age_seconds:
                    stale_limiters.append(name)

            # Then remove them
            for name in stale_limiters:
                del self.limiters[name]

        if stale_limiters:
            logger.info(
                f"Removed {len(stale_limiters)} stale rate limiters: {', '.join(stale_limiters)}"
            )

        return stale_limiters


# Create a singleton instance
rate_limiter = ApiRateLimiter()


# Decorator to rate limit a function
def rate_limited(limiter_name: str, tokens: float = 1.0, max_wait: float = 10.0):
    """
    Decorator to apply rate limiting to a function.

    Args:
        limiter_name: Name of the rate limiter to use
        tokens: Number of tokens to consume
        max_wait: Maximum seconds to wait

    Returns:
        Decorated function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Wait for token availability
            allowed = await rate_limiter.wait_for_token(limiter_name, tokens, max_wait)

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {limiter_name}, request dropped"
                )
                raise Exception(f"Rate limit exceeded for {limiter_name}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
