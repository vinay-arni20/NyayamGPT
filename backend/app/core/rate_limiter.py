"""
NyayamGPT - Rate Limiter
========================
Thread-safe rate limiter implementation for API usage control.
"""

import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Thread-safe rate limiter enforcing a fixed time gap between requests.
    Ensures requests are spaced out evenly (e.g., 10 RPM = 1 request every 6 seconds).
    """
    def __init__(self, rpm: int = 10):
        """
        Initialize the rate limiter.
        
        Args:
            rpm: Requests Per Minute limit (default: 10)
        """
        self.rpm = rpm
        self.min_interval = 60.0 / rpm  # Minimum seconds between requests
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def wait_for_token(self):
        """
        Waits to ensure the minimum interval between requests has passed.
        """
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                logger.info(f"Rate limiting: Enforcing {self.min_interval}s gap. Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
                # Update time to when the wait finishes
                self.last_request_time = time.time()
            else:
                self.last_request_time = now
