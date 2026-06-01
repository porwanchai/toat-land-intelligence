import logging
import time
from fastapi import Request, HTTPException, status
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class RateLimiterMiddleware:
    """
    Highly resilient rate limiting class protecting the FastAPI app.
    Implements standard Token Bucket algorithm:
    - Uses local memory dictionary as default.
    - Limits requests on a per-IP basis.
    - Allows 100 requests per 60 seconds by default.
    """
    def __init__(self, limit: int = 100, window_sec: int = 60):
        self.limit = limit
        self.window_sec = window_sec
        # Memory structure: {ip: [timestamps]}
        self.buckets: Dict[str, list] = {}

    async def check_rate_limit(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Initialize client bucket if absent
        if client_ip not in self.buckets:
            self.buckets[client_ip] = []
            
        bucket = self.buckets[client_ip]
        
        # Remove expired timestamps falling outside temporal window
        self.buckets[client_ip] = [t for t in bucket if current_time - t < self.window_sec]
        
        if len(self.buckets[client_ip]) >= self.limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}. Refused.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and wait before retrying."
            )
            
        # Append active timestamp
        self.buckets[client_ip].append(current_time)
        return True

# Export standard global rate limiter instance (100 requests / 1 min window)
rate_limiter = RateLimiterMiddleware(limit=100, window_sec=60)
