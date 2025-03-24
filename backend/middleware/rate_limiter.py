from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
import asyncio
from collections import defaultdict
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from utils.monitoring import logger
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.utils.monitoring import logger

class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.cleanup_interval = cleanup_interval
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def stop(self):
        """Stop the cleanup task"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            
    async def _cleanup_loop(self):
        """Periodically clean up old request records"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_old_records()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {str(e)}")
                
    def _cleanup_old_records(self):
        """Remove old request records and expired blocks"""
        current_time = time.time()
        cutoff_time = current_time - 60  # Keep last minute
        
        # Clean up request records
        for ip, requests in list(self.requests.items()):
            self.requests[ip] = [req for req in requests if req > cutoff_time]
            if not self.requests[ip]:
                del self.requests[ip]
                
        # Clean up blocked IPs
        current_datetime = datetime.now()
        for ip, block_until in list(self.blocked_ips.items()):
            if current_datetime > block_until:
                del self.blocked_ips[ip]
                
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
        
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Optional[Dict]]:
        """
        Check if request should be rate limited
        Returns (is_allowed, rate_limit_info)
        """
        client_ip = self.get_client_ip(request)
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            block_until = self.blocked_ips[client_ip]
            if datetime.now() > block_until:
                del self.blocked_ips[client_ip]
            else:
                remaining_time = (block_until - datetime.now()).total_seconds()
                return False, {
                    "message": "Too many requests, please try again later",
                    "retry_after": int(remaining_time)
                }
                
        # Get request history for this IP
        current_time = time.time()
        requests = self.requests[client_ip]
        
        # Remove requests older than 1 minute
        requests = [req for req in requests if req > current_time - 60]
        self.requests[client_ip] = requests
        
        # Check burst limit (requests in last second)
        recent_requests = len([req for req in requests if req > current_time - 1])
        if recent_requests >= self.burst_limit:
            # Block IP for 5 minutes on burst limit violation
            self.blocked_ips[client_ip] = datetime.now() + timedelta(minutes=5)
            return False, {
                "message": "Burst limit exceeded, please try again later",
                "retry_after": 300
            }
            
        # Check rate limit
        if len(requests) >= self.requests_per_minute:
            # Block IP for 1 minute on rate limit violation
            self.blocked_ips[client_ip] = datetime.now() + timedelta(minutes=1)
            return False, {
                "message": "Rate limit exceeded, please try again later",
                "retry_after": 60
            }
            
        # Request is allowed, record it
        self.requests[client_ip].append(current_time)
        
        # Return rate limit information
        remaining = self.requests_per_minute - len(requests) - 1
        return True, {
            "X-RateLimit-Limit": self.requests_per_minute,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": int(current_time - (current_time % 60) + 60)
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Middleware to apply rate limiting"""
    is_allowed, info = await rate_limiter.check_rate_limit(request)
    
    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": info["message"]
                }
            },
            headers={"Retry-After": str(info["retry_after"])}
        )
        
    response = await call_next(request)
    
    # Add rate limit headers to response
    if isinstance(info, dict):
        for header, value in info.items():
            if header.startswith("X-RateLimit"):
                response.headers[header] = str(value)
                
    return response 