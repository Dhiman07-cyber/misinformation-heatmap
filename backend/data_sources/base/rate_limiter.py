#!/usr/bin/env python3
"""
Rate limiting utilities for data source connectors.
Implements token bucket and sliding window rate limiting algorithms.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Dict, Optional
import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int = 60, burst_size: Optional[int] = None):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.tokens = self.burst_size
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
        # Calculate refill rate (tokens per second)
        self.refill_rate = requests_per_minute / 60.0
        
        logger.debug(f"Rate limiter initialized: {requests_per_minute} req/min, burst: {self.burst_size}")
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False if rate limited
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Acquired {tokens} tokens, {self.tokens} remaining")
                return True
            else:
                logger.debug(f"Rate limited: need {tokens} tokens, only {self.tokens} available")
                return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if tokens were acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                logger.warning(f"Rate limiter timeout after {timeout}s")
                return False
            
            # Calculate wait time until next token is available
            with self.lock:
                self._refill_tokens()
                if self.tokens >= tokens:
                    continue  # Try again immediately
                
                # Calculate how long to wait for enough tokens
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate
                wait_time = min(wait_time, 1.0)  # Cap at 1 second
            
            logger.debug(f"Waiting {wait_time:.2f}s for {tokens_needed} tokens")
            await asyncio.sleep(wait_time)
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            # Add tokens based on elapsed time
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_refill = now
    
    def get_status(self) -> Dict:
        """Get current rate limiter status."""
        with self.lock:
            self._refill_tokens()
            return {
                'requests_per_minute': self.requests_per_minute,
                'burst_size': self.burst_size,
                'available_tokens': self.tokens,
                'refill_rate': self.refill_rate
            }


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for more precise rate limiting."""
    
    def __init__(self, requests_per_window: int = 60, window_size: int = 60):
        """Initialize sliding window rate limiter.
        
        Args:
            requests_per_window: Maximum requests allowed per window
            window_size: Window size in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_size = window_size
        self.requests = deque()
        self.lock = threading.Lock()
        
        logger.debug(f"Sliding window rate limiter initialized: {requests_per_window} req/{window_size}s")
    
    async def acquire(self) -> bool:
        """Try to acquire a request slot.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        
        with self.lock:
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            # Check if we can make a new request
            if len(self.requests) < self.requests_per_window:
                self.requests.append(now)
                logger.debug(f"Request allowed, {len(self.requests)}/{self.requests_per_window} in window")
                return True
            else:
                logger.debug(f"Rate limited: {len(self.requests)}/{self.requests_per_window} requests in window")
                return False
    
    async def wait_for_slot(self, timeout: Optional[float] = None) -> bool:
        """Wait until a request slot is available.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if slot was acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            if await self.acquire():
                return True
            
            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                logger.warning(f"Sliding window rate limiter timeout after {timeout}s")
                return False
            
            # Calculate wait time until oldest request expires
            with self.lock:
                if self.requests:
                    oldest_request = self.requests[0]
                    wait_time = (oldest_request + self.window_size) - time.time()
                    wait_time = max(0.1, min(wait_time, 1.0))  # Between 0.1 and 1 second
                else:
                    wait_time = 0.1
            
            logger.debug(f"Waiting {wait_time:.2f}s for request slot")
            await asyncio.sleep(wait_time)
    
    def get_status(self) -> Dict:
        """Get current rate limiter status."""
        now = time.time()
        
        with self.lock:
            # Clean up old requests
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            return {
                'requests_per_window': self.requests_per_window,
                'window_size': self.window_size,
                'current_requests': len(self.requests),
                'available_slots': self.requests_per_window - len(self.requests)
            }


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on success/failure rates."""
    
    def __init__(self, initial_rate: int = 60, min_rate: int = 10, max_rate: int = 300):
        """Initialize adaptive rate limiter.
        
        Args:
            initial_rate: Initial requests per minute
            min_rate: Minimum requests per minute
            max_rate: Maximum requests per minute
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        
        self.base_limiter = RateLimiter(self.current_rate)
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment = time.time()
        self.adjustment_interval = 60  # Adjust every minute
        
        self.lock = threading.Lock()
        
        logger.debug(f"Adaptive rate limiter initialized: {initial_rate} req/min (range: {min_rate}-{max_rate})")
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens and track success/failure for adaptation.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False if rate limited
        """
        success = await self.base_limiter.acquire(tokens)
        
        with self.lock:
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
            
            # Check if it's time to adjust the rate
            if time.time() - self.last_adjustment >= self.adjustment_interval:
                self._adjust_rate()
        
        return success
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait for tokens with adaptive rate limiting."""
        success = await self.base_limiter.wait_for_tokens(tokens, timeout)
        
        with self.lock:
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
        
        return success
    
    def record_external_failure(self):
        """Record an external failure (e.g., HTTP 429, API error)."""
        with self.lock:
            self.failure_count += 1
    
    def record_external_success(self):
        """Record an external success."""
        with self.lock:
            self.success_count += 1
    
    def _adjust_rate(self):
        """Adjust rate based on success/failure ratio."""
        total_requests = self.success_count + self.failure_count
        
        if total_requests == 0:
            return
        
        success_rate = self.success_count / total_requests
        
        # Adjust rate based on success rate
        if success_rate > 0.95:  # Very high success rate, increase rate
            new_rate = min(self.max_rate, int(self.current_rate * 1.2))
        elif success_rate > 0.85:  # Good success rate, slight increase
            new_rate = min(self.max_rate, int(self.current_rate * 1.1))
        elif success_rate < 0.7:  # Poor success rate, decrease significantly
            new_rate = max(self.min_rate, int(self.current_rate * 0.7))
        elif success_rate < 0.8:  # Moderate success rate, slight decrease
            new_rate = max(self.min_rate, int(self.current_rate * 0.9))
        else:
            new_rate = self.current_rate  # No change
        
        if new_rate != self.current_rate:
            logger.info(f"Adjusting rate limit: {self.current_rate} -> {new_rate} req/min "
                       f"(success rate: {success_rate:.2%})")
            
            self.current_rate = new_rate
            self.base_limiter = RateLimiter(self.current_rate)
        
        # Reset counters
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment = time.time()
    
    def get_status(self) -> Dict:
        """Get current adaptive rate limiter status."""
        with self.lock:
            total_requests = self.success_count + self.failure_count
            success_rate = (self.success_count / total_requests) if total_requests > 0 else 0
            
            base_status = self.base_limiter.get_status()
            base_status.update({
                'adaptive': True,
                'current_rate': self.current_rate,
                'min_rate': self.min_rate,
                'max_rate': self.max_rate,
                'success_rate': success_rate,
                'success_count': self.success_count,
                'failure_count': self.failure_count
            })
            
            return base_status


# Utility functions for common rate limiting scenarios

async def with_rate_limit(rate_limiter: RateLimiter, coro, *args, **kwargs):
    """Execute a coroutine with rate limiting.
    
    Args:
        rate_limiter: Rate limiter instance
        coro: Coroutine to execute
        *args, **kwargs: Arguments for the coroutine
        
    Returns:
        Result of the coroutine
        
    Raises:
        Exception: If rate limit cannot be acquired or coroutine fails
    """
    if not await rate_limiter.wait_for_tokens(timeout=30):
        raise Exception("Rate limit timeout")
    
    return await coro(*args, **kwargs)


def create_rate_limiter(config: Dict) -> RateLimiter:
    """Create rate limiter from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured rate limiter instance
    """
    limiter_type = config.get('type', 'token_bucket')
    
    if limiter_type == 'token_bucket':
        return RateLimiter(
            requests_per_minute=config.get('requests_per_minute', 60),
            burst_size=config.get('burst_size')
        )
    elif limiter_type == 'sliding_window':
        return SlidingWindowRateLimiter(
            requests_per_window=config.get('requests_per_window', 60),
            window_size=config.get('window_size', 60)
        )
    elif limiter_type == 'adaptive':
        return AdaptiveRateLimiter(
            initial_rate=config.get('initial_rate', 60),
            min_rate=config.get('min_rate', 10),
            max_rate=config.get('max_rate', 300)
        )
    else:
        raise ValueError(f"Unknown rate limiter type: {limiter_type}")