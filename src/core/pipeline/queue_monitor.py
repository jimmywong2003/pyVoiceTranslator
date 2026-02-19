"""
Queue Monitor - Week 0 Critical Fix

Monitors queue depths and alerts on overflow conditions.
Prevents silent data loss from queue overflows.
"""

import time
import logging
import threading
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from queue import Queue
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class QueueAlert:
    """Alert for a queue condition."""
    queue_name: str
    alert_type: str  # 'overflow', 'high_depth', 'empty_drain'
    depth: int
    max_size: int
    timestamp: float
    severity: str  # 'warning', 'critical'


@dataclass
class QueueMetrics:
    """Metrics for a single queue."""
    name: str
    max_size: int
    current_depth: int = 0
    peak_depth: int = 0
    total_puts: int = 0
    total_gets: int = 0
    total_put_failures: int = 0
    total_get_failures: int = 0
    overflow_count: int = 0
    
    # Timing
    put_times_ms: deque = field(default_factory=lambda: deque(maxlen=100))
    get_times_ms: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record_put(self, success: bool, duration_ms: float):
        """Record a put operation."""
        self.total_puts += 1
        self.put_times_ms.append(duration_ms)
        if not success:
            self.total_put_failures += 1
            self.overflow_count += 1
    
    def record_get(self, success: bool, duration_ms: float):
        """Record a get operation."""
        self.total_gets += 1
        self.get_times_ms.append(duration_ms)
        if not success:
            self.total_get_failures += 1
    
    def update_depth(self, depth: int):
        """Update current depth and track peak."""
        self.current_depth = depth
        self.peak_depth = max(self.peak_depth, depth)
    
    def get_avg_put_time_ms(self) -> float:
        """Get average put time."""
        if not self.put_times_ms:
            return 0.0
        return sum(self.put_times_ms) / len(self.put_times_ms)
    
    def get_avg_get_time_ms(self) -> float:
        """Get average get time."""
        if not self.get_times_ms:
            return 0.0
        return sum(self.get_times_ms) / len(self.get_times_ms)


class QueueMonitor:
    """
    Monitors all pipeline queues and alerts on issues.
    
    Week 0 Critical Fix: Detects queue overflows that cause data loss.
    """
    
    # Thresholds
    HIGH_DEPTH_THRESHOLD = 0.7  # 70% of max capacity
    CRITICAL_DEPTH_THRESHOLD = 0.9  # 90% of max capacity
    OVERFLOW_ALERT_COOLDOWN = 5.0  # Seconds between overflow alerts
    
    def __init__(self, check_interval: float = 1.0):
        self._queues: Dict[str, Queue] = {}
        self._metrics: Dict[str, QueueMetrics] = {}
        self._lock = threading.Lock()
        self._check_interval = check_interval
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Alert tracking
        self._alerts: List[QueueAlert] = []
        self._last_overflow_alert: Dict[str, float] = {}
        self._alert_callbacks: List[Callable[[QueueAlert], None]] = []
        
        # Statistics
        self._stats = {
            'total_overflows': 0,
            'total_high_depth_warnings': 0,
            'total_critical_depth_alerts': 0,
        }
        
        logger.info("QueueMonitor initialized (Week 0 Critical Fix)")
    
    def register_queue(self, name: str, queue: Queue):
        """Register a queue for monitoring."""
        with self._lock:
            self._queues[name] = queue
            self._metrics[name] = QueueMetrics(
                name=name,
                max_size=queue.maxsize if queue.maxsize > 0 else float('inf')
            )
            self._last_overflow_alert[name] = 0.0
        
        logger.info(f"Registered queue '{name}' (maxsize={queue.maxsize})")
    
    def unregister_queue(self, name: str):
        """Unregister a queue."""
        with self._lock:
            if name in self._queues:
                del self._queues[name]
                del self._metrics[name]
                del self._last_overflow_alert[name]
    
    def record_put(self, queue_name: str, success: bool, duration_ms: float):
        """Record a put operation on a queue."""
        with self._lock:
            if queue_name in self._metrics:
                self._metrics[queue_name].record_put(success, duration_ms)
                
                if not success:
                    self._stats['total_overflows'] += 1
                    self._trigger_overflow_alert(queue_name)
    
    def record_get(self, queue_name: str, success: bool, duration_ms: float):
        """Record a get operation on a queue."""
        with self._lock:
            if queue_name in self._metrics:
                self._metrics[queue_name].record_get(success, duration_ms)
    
    def _trigger_overflow_alert(self, queue_name: str):
        """Trigger an overflow alert with cooldown."""
        now = time.time()
        last_alert = self._last_overflow_alert.get(queue_name, 0)
        
        if now - last_alert >= self.OVERFLOW_ALERT_COOLDOWN:
            self._last_overflow_alert[queue_name] = now
            
            metrics = self._metrics.get(queue_name)
            if metrics:
                alert = QueueAlert(
                    queue_name=queue_name,
                    alert_type='overflow',
                    depth=metrics.current_depth,
                    max_size=metrics.max_size,
                    timestamp=now,
                    severity='critical'
                )
                self._alerts.append(alert)
                
                # Log critical alert
                logger.error(
                    f"🚨 QUEUE OVERFLOW: '{queue_name}' is FULL! "
                    f"({metrics.current_depth}/{metrics.max_size}). "
                    f"Segments will be DROPPED!"
                )
                
                # Trigger callbacks
                for callback in self._alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")
    
    def _check_queue_depths(self):
        """Check queue depths and alert on high usage."""
        with self._lock:
            for name, queue in self._queues.items():
                metrics = self._metrics[name]
                depth = queue.qsize()
                metrics.update_depth(depth)
                
                if metrics.max_size == float('inf'):
                    continue  # Unbounded queue
                
                utilization = depth / metrics.max_size
                
                # Critical depth alert
                if utilization >= self.CRITICAL_DEPTH_THRESHOLD:
                    self._stats['total_critical_depth_alerts'] += 1
                    logger.error(
                        f"🚨 QUEUE CRITICAL: '{name}' at {utilization*100:.0f}% capacity "
                        f"({depth}/{metrics.max_size}). Risk of overflow!"
                    )
                
                # High depth warning
                elif utilization >= self.HIGH_DEPTH_THRESHOLD:
                    self._stats['total_high_depth_warnings'] += 1
                    logger.warning(
                        f"⚠️  QUEUE WARNING: '{name}' at {utilization*100:.0f}% capacity "
                        f"({depth}/{metrics.max_size})"
                    )
    
    def start_monitoring(self):
        """Start the background monitoring thread."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, name="QueueMonitor")
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
        logger.info("QueueMonitor started")
    
    def stop_monitoring(self):
        """Stop the background monitoring thread."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        logger.info("QueueMonitor stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                self._check_queue_depths()
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Queue monitor error: {e}")
    
    def get_metrics(self, queue_name: Optional[str] = None) -> Dict:
        """Get metrics for a queue or all queues."""
        with self._lock:
            if queue_name:
                if queue_name in self._metrics:
                    m = self._metrics[queue_name]
                    return {
                        'name': m.name,
                        'max_size': m.max_size,
                        'current_depth': m.current_depth,
                        'peak_depth': m.peak_depth,
                        'utilization': m.current_depth / m.max_size if m.max_size != float('inf') else 0,
                        'total_puts': m.total_puts,
                        'total_gets': m.total_gets,
                        'put_failures': m.total_put_failures,
                        'overflow_count': m.overflow_count,
                        'avg_put_time_ms': m.get_avg_put_time_ms(),
                        'avg_get_time_ms': m.get_avg_get_time_ms(),
                    }
                return {}
            else:
                return {name: self.get_metrics(name) for name in self._metrics}
    
    def get_stats(self) -> Dict:
        """Get overall statistics."""
        with self._lock:
            return self._stats.copy()
    
    def get_alerts(self, clear: bool = False) -> List[QueueAlert]:
        """Get all alerts."""
        with self._lock:
            alerts = self._alerts.copy()
            if clear:
                self._alerts.clear()
            return alerts
    
    def on_alert(self, callback: Callable[[QueueAlert], None]):
        """Register an alert callback."""
        self._alert_callbacks.append(callback)
    
    def print_summary(self):
        """Print a summary of queue metrics."""
        print("\n" + "=" * 60)
        print("📊 QUEUE MONITOR SUMMARY (Week 0 Critical Fix)")
        print("=" * 60)
        
        metrics = self.get_metrics()
        stats = self.get_stats()
        
        for name, m in metrics.items():
            status = "✅" if m['utilization'] < 0.5 else "⚠️" if m['utilization'] < 0.8 else "🚨"
            print(f"\n   {status} {name}:")
            print(f"      Depth: {m['current_depth']}/{m['max_size']} ({m['utilization']*100:.0f}%)")
            print(f"      Peak:  {m['peak_depth']}")
            print(f"      Puts:  {m['total_puts']} (fails: {m['put_failures']})")
            print(f"      Gets:  {m['total_gets']}")
            print(f"      Avg put time: {m['avg_put_time_ms']:.2f}ms")
        
        print("-" * 60)
        print(f"   Total Overflows: {stats['total_overflows']}")
        print(f"   High Depth Warnings: {stats['total_high_depth_warnings']}")
        print(f"   Critical Alerts: {stats['total_critical_depth_alerts']}")
        
        if stats['total_overflows'] == 0:
            print("\n   ✅ NO OVERFLOWS - All segments preserved!")
        else:
            print(f"\n   🚨 {stats['total_overflows']} OVERFLOWS - SEGMENTS WERE LOST!")
        
        print("=" * 60)


# Convenience functions for instrumented queue operations
class InstrumentedQueue:
    """Wrapper around Queue that automatically tracks metrics."""
    
    def __init__(self, queue: Queue, name: str, monitor: Optional[QueueMonitor] = None):
        self._queue = queue
        self._name = name
        self._monitor = monitor
    
    def put(self, item, block=True, timeout=None):
        """Put item with monitoring."""
        start = time.time()
        try:
            self._queue.put(item, block, timeout)
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_put(self._name, True, duration_ms)
            return True
        except Exception:
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_put(self._name, False, duration_ms)
            raise
    
    def put_nowait(self, item):
        """Put item without blocking, with monitoring."""
        start = time.time()
        try:
            self._queue.put_nowait(item)
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_put(self._name, True, duration_ms)
            return True
        except Exception:
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_put(self._name, False, duration_ms)
            raise
    
    def get(self, block=True, timeout=None):
        """Get item with monitoring."""
        start = time.time()
        try:
            item = self._queue.get(block, timeout)
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_get(self._name, True, duration_ms)
            return item
        except Exception:
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_get(self._name, False, duration_ms)
            raise
    
    def get_nowait(self):
        """Get item without blocking, with monitoring."""
        start = time.time()
        try:
            item = self._queue.get_nowait()
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_get(self._name, True, duration_ms)
            return item
        except Exception:
            duration_ms = (time.time() - start) * 1000
            if self._monitor:
                self._monitor.record_get(self._name, False, duration_ms)
            raise
    
    def qsize(self):
        return self._queue.qsize()
    
    def empty(self):
        return self._queue.empty()
    
    def full(self):
        return self._queue.full()
    
    @property
    def maxsize(self):
        return self._queue.maxsize


# Global monitor instance
_global_monitor: Optional[QueueMonitor] = None


def get_global_monitor() -> QueueMonitor:
    """Get or create the global queue monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = QueueMonitor()
    return _global_monitor


def reset_global_monitor():
    """Reset the global monitor (for testing)."""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop_monitoring()
    _global_monitor = QueueMonitor()
