"""
Performance Monitor - Phase 5
=============================

Real-time performance monitoring for CPU, memory, and audio latency.

Features:
- CPU usage tracking
- Memory usage monitoring
- Audio latency measurement
- Performance alerts

Usage:
    from src.core.utils.performance_monitor import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    monitor.cpu_alert.connect(on_high_cpu)
    monitor.start_monitoring()
"""

import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from collections import deque

import psutil
from PySide6.QtCore import QObject, Signal, QTimer


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    audio_latency_ms: float
    timestamp: float


class PerformanceMonitor(QObject):
    """
    Monitor system performance metrics.
    
    Signals:
        metrics_updated: Emitted with current metrics
        cpu_alert: Emitted when CPU exceeds threshold
        memory_alert: Emitted when memory exceeds threshold
    """
    
    metrics_updated = Signal(object)  # PerformanceMetrics
    cpu_alert = Signal(float)  # current CPU %
    memory_alert = Signal(float)  # current memory %
    
    def __init__(self, 
                 cpu_threshold: float = 80.0,
                 memory_threshold: float = 85.0,
                 history_size: int = 100):
        super().__init__()
        
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.history_size = history_size
        
        # Metrics history
        self._history: deque = deque(maxlen=history_size)
        self._audio_latency_samples: deque = deque(maxlen=10)
        
        # Timer
        self._timer: Optional[QTimer] = None
        self._interval_ms = 1000  # Update every second
        
        # Alert tracking (prevent spam)
        self._last_cpu_alert = 0
        self._last_memory_alert = 0
        self._alert_cooldown = 30  # Seconds between alerts
    
    def start_monitoring(self, interval_ms: int = 1000):
        """Start performance monitoring."""
        self._interval_ms = interval_ms
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_metrics)
        self._timer.start(interval_ms)
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        if self._timer:
            self._timer.stop()
            self._timer = None
    
    def _update_metrics(self):
        """Update and emit current metrics."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Calculate average audio latency
            avg_latency = (sum(self._audio_latency_samples) / len(self._audio_latency_samples)) \
                         if self._audio_latency_samples else 0.0
            
            metrics = PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / (1024 * 1024),
                audio_latency_ms=avg_latency,
                timestamp=time.time()
            )
            
            # Store in history
            self._history.append(metrics)
            
            # Emit metrics
            self.metrics_updated.emit(metrics)
            
            # Check thresholds
            self._check_alerts(cpu_percent, memory.percent)
            
        except Exception as e:
            print(f"Performance monitoring error: {e}")
    
    def _check_alerts(self, cpu: float, memory: float):
        """Check for threshold violations."""
        current_time = time.time()
        
        # CPU alert
        if cpu > self.cpu_threshold:
            if current_time - self._last_cpu_alert > self._alert_cooldown:
                self.cpu_alert.emit(cpu)
                self._last_cpu_alert = current_time
        
        # Memory alert
        if memory > self.memory_threshold:
            if current_time - self._last_memory_alert > self._alert_cooldown:
                self.memory_alert.emit(memory)
                self._last_memory_alert = current_time
    
    def record_audio_latency(self, latency_ms: float):
        """Record an audio latency sample."""
        self._audio_latency_samples.append(latency_ms)
    
    def get_average_metrics(self, seconds: int = 60) -> Optional[PerformanceMetrics]:
        """Get average metrics over specified period."""
        if not self._history:
            return None
        
        cutoff_time = time.time() - seconds
        recent = [m for m in self._history if m.timestamp >= cutoff_time]
        
        if not recent:
            return None
        
        return PerformanceMetrics(
            cpu_percent=sum(m.cpu_percent for m in recent) / len(recent),
            memory_percent=sum(m.memory_percent for m in recent) / len(recent),
            memory_mb=sum(m.memory_mb for m in recent) / len(recent),
            audio_latency_ms=sum(m.audio_latency_ms for m in recent) / len(recent),
            timestamp=time.time()
        )
    
    def get_history(self) -> list:
        """Get metrics history."""
        return list(self._history)


class MemoryLeakDetector:
    """
    Detect potential memory leaks by tracking memory growth over time.
    
    Usage:
        detector = MemoryLeakDetector()
        detector.start_tracking()
        # ... run your code ...
        if detector.detect_leak():
            print("Potential memory leak detected!")
    """
    
    def __init__(self, growth_threshold_mb: float = 100.0, 
                 check_interval_seconds: int = 60):
        self.growth_threshold_mb = growth_threshold_mb
        self.check_interval_seconds = check_interval_seconds
        
        self._baseline_memory: Optional[float] = None
        self._start_time: Optional[float] = None
        self._samples: list = []
    
    def start_tracking(self):
        """Start memory tracking."""
        process = psutil.Process()
        self._baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB
        self._start_time = time.time()
        self._samples = [(0, self._baseline_memory)]
    
    def record_sample(self):
        """Record current memory usage."""
        if self._start_time is None:
            return
        
        process = psutil.Process()
        current_mb = process.memory_info().rss / (1024 * 1024)
        elapsed = time.time() - self._start_time
        
        self._samples.append((elapsed, current_mb))
    
    def detect_leak(self) -> bool:
        """Check if memory leak is detected."""
        if not self._samples or self._baseline_memory is None:
            return False
        
        # Check if memory grew more than threshold
        current_mb = self._samples[-1][1]
        growth_mb = current_mb - self._baseline_memory
        
        return growth_mb > self.growth_threshold_mb
    
    def get_growth_rate(self) -> float:
        """Get memory growth rate in MB/minute."""
        if len(self._samples) < 2:
            return 0.0
        
        first_sample = self._samples[0]
        last_sample = self._samples[-1]
        
        time_diff_minutes = (last_sample[0] - first_sample[0]) / 60
        if time_diff_minutes <= 0:
            return 0.0
        
        memory_diff_mb = last_sample[1] - first_sample[1]
        return memory_diff_mb / time_diff_minutes
