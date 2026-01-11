# backend/app/rate_limiter.py
from fastapi import HTTPException, Request
from collections import defaultdict
from datetime import datetime, timedelta
import threading

class RateLimiter:
    """
    Simple in-memory rate limiter for API endpoints
    Production: Use Redis for distributed rate limiting
    """
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def check_rate_limit(self, user_id: int, max_requests: int = 10, window_seconds: int = 60):
        """
        Check if user has exceeded rate limit
        
        Args:
            user_id: User ID to check
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=window_seconds)
            
            # Remove old requests
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > cutoff
            ]
            
            # Check if limit exceeded
            if len(self.requests[user_id]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
                )
            
            # Add current request
            self.requests[user_id].append(now)
    
    def cleanup_old_entries(self, max_age_minutes: int = 60):
        """Cleanup old entries to prevent memory leak"""
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
            users_to_remove = []
            
            for user_id, times in self.requests.items():
                # Remove old times
                self.requests[user_id] = [t for t in times if t > cutoff]
                # If no recent requests, remove user
                if not self.requests[user_id]:
                    users_to_remove.append(user_id)
            
            for user_id in users_to_remove:
                del self.requests[user_id]

# Global rate limiter instance
rate_limiter = RateLimiter()
