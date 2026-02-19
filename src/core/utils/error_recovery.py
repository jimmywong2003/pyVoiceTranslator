"""
Error Recovery and Circuit Breaker System - Phase 2.2

Provides production-grade error handling with:
- Automatic retry with exponential backoff
- Circuit breaker pattern for failing components
- Graceful degradation
- Health monitoring

Usage:
    from src.core.utils.error_recovery import CircuitBreaker, with_retry
    
    @with_retry(max_attempts=3)
    def flaky_operation():
        pass
    
    breaker = CircuitBreaker(failure_threshold=5)
    result = breaker.call(unreliable_function)
"""

import time
import logging
import threading
from enum import Enum
from typing import Callable, Any, Optional, TypeVar, List
from functools import wraps
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class HealthStatus(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: HealthStatus
    message: str = ""
    last_check_time: float = field(default_factory=time.time)
    response_time_ms: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker pattern for resilient error handling.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Failing fast, calls return fallback immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.name = name
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.RLock()
        
    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state
    
    def call(self, func: Callable[[], T], fallback: Optional[Callable[[], T]] = None) -> T:
        """
        Call a function through the circuit breaker.
        
        Args:
            func: The function to call
            fallback: Optional fallback function if circuit is open
            
        Returns:
            Result from func or fallback
            
        Raises:
            CircuitBreakerOpen: If circuit is open and no fallback provided
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and \
                   (time.time() - self._last_failure_time) >= self.recovery_timeout:
                    logger.info(f"Circuit {self.name}: Transitioning OPEN -> HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    if fallback:
                        logger.debug(f"Circuit {self.name}: OPEN, using fallback")
                        return fallback()
                    raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
        
        # Execute the call
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    logger.info(f"Circuit {self.name}: Transitioning HALF_OPEN -> CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            else:
                self._failure_count = 0
    
    def _on_failure(self):
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit {self.name}: Transitioning HALF_OPEN -> OPEN")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                logger.warning(f"Circuit {self.name}: Transitioning CLOSED -> OPEN")
                self._state = CircuitState.OPEN
    
    def force_open(self):
        """Manually open the circuit."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
    
    def force_close(self):
        """Manually close the circuit."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'last_failure_time': self._last_failure_time
            }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RetryExhausted(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        retryable_exceptions: Exceptions that trigger retry
        on_retry: Optional callback on retry (exception, attempt_number)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(f"Retry exhausted for {func.__name__}: {e}")
                        raise RetryExhausted(f"Failed after {max_attempts} attempts: {e}") from e
                    
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    logger.warning(f"Retry {attempt}/{max_attempts} for {func.__name__} in {delay:.1f}s: {e}")
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


class HealthMonitor:
    """
    Health monitoring for all pipeline components.
    
    Provides:
    - Periodic health checks
    - Status aggregation
    - Alert callbacks
    """
    
    def __init__(self, check_interval_sec: float = 30.0):
        self.check_interval = check_interval_sec
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._results: Dict[str, HealthCheck] = {}
        self._alert_callbacks: List[Callable[[HealthCheck], None]] = []
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def register_check(self, name: str, check_func: Callable[[], HealthCheck]):
        """Register a health check function."""
        with self._lock:
            self._checks[name] = check_func
            logger.info(f"Registered health check: {name}")
    
    def register_alert(self, callback: Callable[[HealthCheck], None]):
        """Register an alert callback."""
        with self._lock:
            self._alert_callbacks.append(callback)
    
    def check_health(self, component: Optional[str] = None) -> Dict[str, HealthCheck]:
        """Run health checks."""
        results = {}
        
        with self._lock:
            checks_to_run = {component: self._checks[component]} if component else self._checks
            
            for name, check_func in checks_to_run.items():
                start = time.time()
                try:
                    result = check_func()
                    result.response_time_ms = (time.time() - start) * 1000
                except Exception as e:
                    result = HealthCheck(
                        component=name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed: {e}"
                    )
                
                # Check for status changes
                prev_result = self._results.get(name)
                if prev_result and prev_result.status != result.status:
                    logger.warning(f"Health status change for {name}: {prev_result.status.value} -> {result.status.value}")
                    for callback in self._alert_callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.error(f"Alert callback failed: {e}")
                
                results[name] = result
                self._results[name] = result
        
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """Get aggregated health status."""
        with self._lock:
            if not self._results:
                return HealthStatus.UNKNOWN
            
            statuses = [r.status for r in self._results.values()]
            
            if any(s == HealthStatus.UNHEALTHY for s in statuses):
                return HealthStatus.UNHEALTHY
            if any(s == HealthStatus.DEGRADED for s in statuses):
                return HealthStatus.DEGRADED
            if all(s == HealthStatus.HEALTHY for s in statuses):
                return HealthStatus.HEALTHY
            
            return HealthStatus.UNKNOWN
    
    def start_monitoring(self):
        """Start background health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Health monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                self.check_health()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def get_report(self) -> Dict[str, Any]:
        """Get full health report."""
        with self._lock:
            return {
                'overall_status': self.get_overall_status().value,
                'components': {
                    name: {
                        'status': check.status.value,
                        'message': check.message,
                        'last_check': check.last_check_time,
                        'response_time_ms': check.response_time_ms
                    }
                    for name, check in self._results.items()
                }
            }


class GracefulDegradation:
    """
    Graceful degradation manager.
    
    Automatically reduces quality under load to maintain responsiveness.
    """
    
    def __init__(self):
        self._strategies: List[Callable[[], None]] = []
        self._current_level = 0
        self._lock = threading.Lock()
    
    def register_strategy(self, strategy: Callable[[], None]):
        """Register a degradation strategy (called in order)."""
        self._strategies.append(strategy)
    
    def degrade(self) -> bool:
        """
        Trigger next degradation level.
        
        Returns:
            True if degradation was applied, False if at max level
        """
        with self._lock:
            if self._current_level >= len(self._strategies):
                return False
            
            logger.warning(f"Applying degradation level {self._current_level + 1}")
            try:
                self._strategies[self._current_level]()
                self._current_level += 1
                return True
            except Exception as e:
                logger.error(f"Degradation failed: {e}")
                return False
    
    def restore(self) -> bool:
        """
        Restore one level of degradation.
        
        Returns:
            True if restoration was applied, False if at base level
        """
        with self._lock:
            if self._current_level <= 0:
                return False
            
            self._current_level -= 1
            logger.info(f"Restored from degradation level {self._current_level + 1}")
            return True
    
    def get_level(self) -> int:
        """Get current degradation level."""
        with self._lock:
            return self._current_level


# Global health monitor instance
_global_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance."""
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = HealthMonitor()
    return _global_health_monitor


# Example usage patterns
if __name__ == '__main__':
    # Circuit breaker example
    breaker = CircuitBreaker(failure_threshold=3, name="test")
    
    def flaky_function():
        import random
        if random.random() < 0.7:
            raise ValueError("Random failure")
        return "success"
    
    def fallback():
        return "fallback result"
    
    # Retry example
    @with_retry(max_attempts=3, base_delay=0.1)
    def retryable_function():
        import random
        if random.random() < 0.5:
            raise ValueError("Random failure")
        return "success"
    
    # Health check example
    monitor = HealthMonitor()
    
    def asr_health_check() -> HealthCheck:
        return HealthCheck(
            component="asr",
            status=HealthStatus.HEALTHY,
            message="ASR responding normally"
        )
    
    monitor.register_check("asr", asr_health_check)
    print(monitor.check_health())
