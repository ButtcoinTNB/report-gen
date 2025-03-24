from prometheus_client import Counter, Gauge, Histogram
from functools import wraps
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from typing import Callable, Any, Optional
import time
import asyncio

# Metrics
TASK_DURATION = Histogram('task_duration_seconds', 'Task duration in seconds')
ACTIVE_TASKS = Gauge('active_tasks', 'Number of active tasks')
ERROR_COUNTER = Counter('task_errors_total', 'Number of task errors')
API_REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration in seconds')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_monitoring(sentry_dsn: Optional[str] = None):
    """Initialize monitoring systems"""
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )

def monitor_task(task_name: str):
    """Decorator for monitoring async tasks"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            ACTIVE_TASKS.inc()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                TASK_DURATION.labels(task=task_name).observe(duration)
                return result
            except Exception as e:
                ERROR_COUNTER.labels(task=task_name).inc()
                logger.exception(f"Task {task_name} failed: {str(e)}")
                raise
            finally:
                ACTIVE_TASKS.dec()
                
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.is_open = False
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.is_open:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.is_open = False
                self.failure_count = 0
            else:
                raise Exception("Circuit breaker is open")
                
        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                
            raise 