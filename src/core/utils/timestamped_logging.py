"""
Timestamped Logging Utility with Delta Time Tracking

Provides logging with millisecond-precision timestamps and delta time calculation
for evaluating speech loss, latency analysis, and sentence-by-sentence timing.

Usage:
    from src.core.utils.timestamped_logging import setup_timestamped_logging, DeltaTimeTracker
    
    setup_timestamped_logging()
    delta_tracker = DeltaTimeTracker()
    
    logger = logging.getLogger(__name__)
    delta = delta_tracker.get_delta()
    logger.info(f"[Δ{delta:+.3f}s] Event occurred")
    
    # Output: 2026-02-19 23:45:12.345 | INFO | [Δ+2.456s] Event occurred
"""

import logging
import sys
import time
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, field
from threading import Lock


class TimestampedFormatter(logging.Formatter):
    """Custom formatter with millisecond-precision timestamps."""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        # Default format: "2026-02-19 23:45:12.345 | LEVEL | Message"
        if fmt is None:
            fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        super().__init__(fmt=fmt, datefmt=datefmt)
    
    def formatTime(self, record, datefmt=None):
        """Override to provide millisecond precision."""
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            # Format: 2026-02-19 23:45:12.345
            s = ct.strftime("%Y-%m-%d %H:%M:%S") + ".%03d" % record.msecs
        return s


class DeltaTimeFormatter(logging.Formatter):
    """Formatter that includes delta time from previous log entry."""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        # Format: "2026-02-19 23:45:12.345 | Δ+0.456s | LEVEL | Message"
        if fmt is None:
            fmt = "%(asctime)s | %(delta_time)+8s | %(levelname)-8s | %(name)s | %(message)s"
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._last_time = None
        self._lock = Lock()
    
    def formatTime(self, record, datefmt=None):
        """Override to provide millisecond precision."""
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S") + ".%03d" % record.msecs
        return s
    
    def format(self, record):
        """Add delta_time to record."""
        with self._lock:
            current_time = record.created
            if self._last_time is None:
                delta = 0.0
            else:
                delta = current_time - self._last_time
            self._last_time = current_time
            record.delta_time = f"Δ{delta:+.3f}s"
        return super().format(record)


class DeltaTimeTracker:
    """
    Track delta times between events for detailed timing analysis.
    
    Thread-safe tracker that maintains per-event-type timestamps
    for calculating deltas between specific event types.
    """
    
    def __init__(self):
        self._last_times: Dict[str, float] = {}
        self._global_last_time: Optional[float] = None
        self._lock = Lock()
    
    def get_delta(self, event_type: str = "global") -> float:
        """
        Get delta time from previous event of same type.
        
        Args:
            event_type: Type of event (e.g., "segment", "asr", "translation")
            
        Returns:
            Delta time in seconds
        """
        with self._lock:
            current_time = time.time()
            
            if event_type == "global":
                last_time = self._global_last_time
                self._global_last_time = current_time
            else:
                last_time = self._last_times.get(event_type)
                self._last_times[event_type] = current_time
            
            if last_time is None:
                return 0.0
            return current_time - last_time
    
    def get_delta_formatted(self, event_type: str = "global") -> str:
        """Get formatted delta string."""
        delta = self.get_delta(event_type)
        return f"Δ{delta:+.3f}s"
    
    def reset(self):
        """Reset all tracked times."""
        with self._lock:
            self._last_times.clear()
            self._global_last_time = None


# Global tracker instance
_global_delta_tracker = DeltaTimeTracker()


def get_delta_tracker() -> DeltaTimeTracker:
    """Get the global delta time tracker."""
    return _global_delta_tracker


def setup_timestamped_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    include_delta: bool = True
) -> logging.Logger:
    """
    Setup logging with timestamps and optional delta time.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to log to file
        format_string: Custom format string
        include_delta: Whether to include delta time column
        
    Returns:
        Root logger
    """
    # Choose formatter
    if include_delta:
        formatter = DeltaTimeFormatter(fmt=format_string)
    else:
        formatter = TimestampedFormatter(fmt=format_string)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_timestamped_logger(name: str) -> logging.Logger:
    """Get a logger with timestamp formatting already set up."""
    return logging.getLogger(name)


# Convenience function for segment timing logs with delta
def log_segment_timing(
    logger: logging.Logger,
    segment_id: str,
    event: str,
    timestamp: Optional[float] = None,
    extra_data: Optional[dict] = None,
    include_delta: bool = True
):
    """
    Log segment timing event with precise timestamp and delta.
    
    Args:
        logger: Logger instance
        segment_id: Unique segment identifier
        event: Event name (e.g., "speech_start", "asr_complete", "translation_complete")
        timestamp: Optional Unix timestamp (default: now)
        extra_data: Optional dict of additional data
        include_delta: Whether to include delta time
    """
    tracker = get_delta_tracker()
    
    if timestamp is None:
        timestamp = time.time()
    
    ts_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    delta_str = ""
    if include_delta:
        delta = tracker.get_delta(f"segment_{segment_id}")
        delta_str = f" [Δ{delta:+.3f}s]"
    
    message = f"[SEGMENT:{segment_id}] {event} at {ts_str}{delta_str}"
    
    if extra_data:
        extra_str = " | ".join(f"{k}={v}" for k, v in extra_data.items())
        message += f" | {extra_str}"
    
    logger.info(message)


def log_latency_metric(
    logger: logging.Logger,
    metric_name: str,
    latency_ms: float,
    segment_id: Optional[str] = None,
    threshold_ms: Optional[float] = None,
    include_delta: bool = True
):
    """
    Log latency metric with threshold check and delta time.
    
    Args:
        logger: Logger instance
        metric_name: Name of metric (e.g., "TTFT", "ASR_TIME", "TRANSLATION_TIME")
        latency_ms: Latency in milliseconds
        segment_id: Optional segment ID
        threshold_ms: Optional threshold for warning
        include_delta: Whether to include delta from previous metric
    """
    tracker = get_delta_tracker()
    
    delta_str = ""
    if include_delta:
        delta = tracker.get_delta("latency_metric")
        delta_str = f" [Δ{delta:+.3f}s]"
    
    message = f"[LATENCY] {metric_name}: {latency_ms:.1f}ms{delta_str}"
    
    if segment_id:
        message = f"[SEGMENT:{segment_id}] {message}"
    
    if threshold_ms and latency_ms > threshold_ms:
        logger.warning(f"{message} (EXCEEDS {threshold_ms}ms threshold)")
    else:
        logger.info(message)


@dataclass
class TimingEvent:
    """Data class for timing events."""
    event_type: str
    segment_id: int
    timestamp: float
    delta_from_previous: float
    text: str = ""
    duration_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'event_type': self.event_type,
            'segment_id': self.segment_id,
            'timestamp': self.timestamp,
            'delta_from_previous': self.delta_from_previous,
            'text': self.text,
            'duration_ms': self.duration_ms
        }


class TimingAnalyzer:
    """
    Analyze timing events for speech loss and latency evaluation.
    
    Collects timing events and provides analysis methods.
    """
    
    def __init__(self):
        self.events: list = []
        self._lock = Lock()
    
    def add_event(self, event: TimingEvent):
        """Add a timing event."""
        with self._lock:
            self.events.append(event)
    
    def get_segment_timeline(self, segment_id: int) -> list:
        """Get all events for a specific segment."""
        with self._lock:
            return [e for e in self.events if e.segment_id == segment_id]
    
    def calculate_segment_latency(self, segment_id: int) -> Optional[float]:
        """Calculate total latency for a segment (created to emitted)."""
        timeline = self.get_segment_timeline(segment_id)
        
        created = None
        emitted = None
        
        for event in timeline:
            if event.event_type == "created":
                created = event.timestamp
            elif event.event_type == "emitted":
                emitted = event.timestamp
        
        if created and emitted:
            return (emitted - created) * 1000  # Convert to ms
        return None
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        with self._lock:
            segments_created = len([e for e in self.events if e.event_type == "created"])
            segments_emitted = len([e for e in self.events if e.event_type == "emitted"])
            segments_filtered = len([e for e in self.events if e.event_type == "filtered"])
            
            # Calculate latencies
            latencies = []
            for event in self.events:
                if event.event_type == "emitted" and event.duration_ms > 0:
                    latencies.append(event.duration_ms)
            
            return {
                'total_events': len(self.events),
                'segments_created': segments_created,
                'segments_emitted': segments_emitted,
                'segments_filtered': segments_filtered,
                'loss_rate': (segments_created - segments_emitted - segments_filtered) / max(segments_created, 1) * 100,
                'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
                'max_latency_ms': max(latencies) if latencies else 0,
                'min_latency_ms': min(latencies) if latencies else 0
            }
    
    def export_csv(self, filename: str):
        """Export events to CSV for analysis."""
        import csv
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'delta', 'event_type', 'segment_id', 'text', 'duration_ms'])
            
            for event in self.events:
                writer.writerow([
                    datetime.fromtimestamp(event.timestamp).isoformat(),
                    f"{event.delta_from_previous:.3f}",
                    event.event_type,
                    event.segment_id,
                    event.text[:50],  # Truncate for CSV
                    f"{event.duration_ms:.1f}"
                ])


# Global timing analyzer instance
global_timing_analyzer = TimingAnalyzer()


def get_timing_analyzer() -> TimingAnalyzer:
    """Get the global timing analyzer."""
    return global_timing_analyzer
