"""
Timestamped Logging Utility

Provides logging with millisecond-precision timestamps for evaluating
speech loss, latency analysis, and performance monitoring.

Usage:
    from src.core.utils.timestamped_logging import setup_timestamped_logging
    
    setup_timestamped_logging()
    logger = logging.getLogger(__name__)
    logger.info("Translation started")
    # Output: 2026-02-19 23:45:12.345 | INFO | Translation started
"""

import logging
import sys
from datetime import datetime
from typing import Optional


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


def setup_timestamped_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup logging with timestamps.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to log to file
        format_string: Custom format string
        
    Returns:
        Root logger
    """
    # Create formatter
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
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


# Convenience function for segment timing logs
def log_segment_timing(
    logger: logging.Logger,
    segment_id: str,
    event: str,
    timestamp: Optional[float] = None,
    extra_data: Optional[dict] = None
):
    """
    Log segment timing event with precise timestamp.
    
    Args:
        logger: Logger instance
        segment_id: Unique segment identifier
        event: Event name (e.g., "speech_start", "asr_complete", "translation_complete")
        timestamp: Optional Unix timestamp (default: now)
        extra_data: Optional dict of additional data
    """
    if timestamp is None:
        timestamp = datetime.now().timestamp()
    
    ts_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    message = f"[SEGMENT:{segment_id}] {event} at {ts_str}"
    
    if extra_data:
        extra_str = " | ".join(f"{k}={v}" for k, v in extra_data.items())
        message += f" | {extra_str}"
    
    logger.info(message)


def log_latency_metric(
    logger: logging.Logger,
    metric_name: str,
    latency_ms: float,
    segment_id: Optional[str] = None,
    threshold_ms: Optional[float] = None
):
    """
    Log latency metric with threshold check.
    
    Args:
        logger: Logger instance
        metric_name: Name of metric (e.g., "TTFT", "ASR_TIME", "TRANSLATION_TIME")
        latency_ms: Latency in milliseconds
        segment_id: Optional segment ID
        threshold_ms: Optional threshold for warning
    """
    message = f"[LATENCY] {metric_name}: {latency_ms:.1f}ms"
    
    if segment_id:
        message = f"[SEGMENT:{segment_id}] {message}"
    
    if threshold_ms and latency_ms > threshold_ms:
        logger.warning(f"{message} (EXCEEDS {threshold_ms}ms threshold)")
    else:
        logger.info(message)
