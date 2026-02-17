"""
Latency Analysis and Debugging Framework for Voice Translation

This module provides comprehensive latency measurement, buffer optimization,
and real-time performance analysis for the translation pipeline.
"""

import time
import json
import logging
import statistics
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable
from collections import deque
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Detailed latency metrics for a single translation segment."""
    segment_id: int
    timestamp: float
    
    # Audio capture latency
    audio_capture_start: float = 0.0
    audio_capture_end: float = 0.0
    audio_duration_ms: float = 0.0
    
    # VAD processing
    vad_start: float = 0.0
    vad_end: float = 0.0
    vad_latency_ms: float = 0.0
    
    # ASR processing
    asr_start: float = 0.0
    asr_end: float = 0.0
    asr_latency_ms: float = 0.0
    asr_audio_duration_ms: float = 0.0  # Duration of audio processed
    
    # Translation processing
    translation_start: float = 0.0
    translation_end: float = 0.0
    translation_latency_ms: float = 0.0
    source_text_length: int = 0
    translated_text_length: int = 0
    
    # Total end-to-end
    total_latency_ms: float = 0.0
    
    # Buffer state at processing time
    buffer_size_ms: float = 0.0
    queue_depth: int = 0
    
    # Additional info
    is_partial: bool = False
    model_size: str = "base"
    source_lang: str = ""
    target_lang: str = ""


@dataclass
class PipelineStatistics:
    """Aggregated pipeline statistics."""
    session_start: float = field(default_factory=time.time)
    total_segments: int = 0
    
    # Latency statistics (ms)
    vad_latencies: List[float] = field(default_factory=list)
    asr_latencies: List[float] = field(default_factory=list)
    translation_latencies: List[float] = field(default_factory=list)
    total_latencies: List[float] = field(default_factory=list)
    
    # Audio duration tracking
    audio_durations: List[float] = field(default_factory=list)
    
    # Buffer statistics
    buffer_sizes: List[float] = field(default_factory=list)
    queue_depths: List[int] = field(default_factory=list)
    
    # Real-time factor (RTF) - processing_time / audio_duration
    rtfs: List[float] = field(default_factory=list)
    
    def add_metrics(self, metrics: LatencyMetrics):
        """Add a metrics entry to statistics."""
        self.total_segments += 1
        
        if metrics.vad_latency_ms > 0:
            self.vad_latencies.append(metrics.vad_latency_ms)
        if metrics.asr_latency_ms > 0:
            self.asr_latencies.append(metrics.asr_latency_ms)
        if metrics.translation_latency_ms > 0:
            self.translation_latencies.append(metrics.translation_latency_ms)
        if metrics.total_latency_ms > 0:
            self.total_latencies.append(metrics.total_latency_ms)
        
        if metrics.audio_duration_ms > 0:
            self.audio_durations.append(metrics.audio_duration_ms)
        
        if metrics.buffer_size_ms > 0:
            self.buffer_sizes.append(metrics.buffer_size_ms)
        if metrics.queue_depth > 0:
            self.queue_depths.append(metrics.queue_depth)
        
        # Calculate RTF
        if metrics.asr_latency_ms > 0 and metrics.asr_audio_duration_ms > 0:
            rtf = metrics.asr_latency_ms / metrics.asr_audio_duration_ms
            self.rtfs.append(rtf)
    
    def get_summary(self) -> Dict:
        """Get statistical summary."""
        def safe_stats(data: List[float]) -> Dict:
            if not data:
                return {"count": 0, "mean": 0, "min": 0, "max": 0, "p95": 0}
            sorted_data = sorted(data)
            p95_idx = int(len(sorted_data) * 0.95)
            return {
                "count": len(data),
                "mean": statistics.mean(data),
                "min": min(data),
                "max": max(data),
                "p95": sorted_data[min(p95_idx, len(sorted_data)-1)],
                "stdev": statistics.stdev(data) if len(data) > 1 else 0
            }
        
        runtime = time.time() - self.session_start
        
        return {
            "runtime_seconds": runtime,
            "total_segments": self.total_segments,
            "segments_per_minute": (self.total_segments / runtime * 60) if runtime > 0 else 0,
            "vad_latency_ms": safe_stats(self.vad_latencies),
            "asr_latency_ms": safe_stats(self.asr_latencies),
            "translation_latency_ms": safe_stats(self.translation_latencies),
            "total_latency_ms": safe_stats(self.total_latencies),
            "audio_duration_ms": safe_stats(self.audio_durations),
            "buffer_size_ms": safe_stats(self.buffer_sizes),
            "queue_depth": safe_stats(self.queue_depths),
            "real_time_factor": safe_stats(self.rtfs),
        }
    
    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 70)
        print("📊 LATENCY ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Runtime: {summary['runtime_seconds']:.1f}s")
        print(f"Total Segments: {summary['total_segments']}")
        print(f"Throughput: {summary['segments_per_minute']:.1f} segments/min")
        
        print("\n--- Component Latencies ---")
        for component in ['vad', 'asr', 'translation']:
            key = f"{component}_latency_ms"
            stats = summary[key]
            if stats['count'] > 0:
                print(f"{component.upper():15s}: mean={stats['mean']:6.1f}ms, "
                      f"p95={stats['p95']:6.1f}ms, "
                      f"min={stats['min']:6.1f}ms, "
                      f"max={stats['max']:6.1f}ms")
        
        total = summary['total_latency_ms']
        if total['count'] > 0:
            print(f"\n{'END-TO-END':15s}: mean={total['mean']:6.1f}ms, "
                  f"p95={total['p95']:6.1f}ms, "
                  f"min={total['min']:6.1f}ms, "
                  f"max={total['max']:6.1f}ms")
        
        rtf = summary['real_time_factor']
        if rtf['count'] > 0:
            print(f"\nReal-Time Factor (RTF): {rtf['mean']:.2f}x")
            print(f"  (RTF < 1.0 = real-time capable, RTF > 1.0 = slower than real-time)")
            if rtf['mean'] > 1.0:
                print(f"  ⚠️  WARNING: System is slower than real-time!")
                print(f"     Consider: smaller model, faster hardware, or longer buffers")
        
        audio = summary['audio_duration_ms']
        if audio['count'] > 0:
            print(f"\nAudio Duration: mean={audio['mean']/1000:.1f}s, "
                  f"max={audio['max']/1000:.1f}s")
        
        print("=" * 70)


class LatencyAnalyzer:
    """
    Real-time latency analyzer for the translation pipeline.
    
    Usage:
        analyzer = LatencyAnalyzer()
        
        # Mark events during processing
        analyzer.mark_audio_start(segment_id)
        analyzer.mark_vad_start(segment_id)
        analyzer.mark_vad_end(segment_id)
        ...
        
        # Get metrics
        metrics = analyzer.get_metrics(segment_id)
        
        # Print summary
        analyzer.print_summary()
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize the latency analyzer.
        
        Args:
            max_history: Maximum number of metrics entries to keep
        """
        self._metrics: Dict[int, LatencyMetrics] = {}
        self._history: deque = deque(maxlen=max_history)
        self._stats = PipelineStatistics()
        self._lock = threading.Lock()
        self._current_segment_id: Optional[int] = None
        
        logger.info("Latency analyzer initialized")
    
    def start_segment(self, segment_id: int, audio_duration_ms: float = 0.0) -> LatencyMetrics:
        """Start tracking a new segment."""
        with self._lock:
            metrics = LatencyMetrics(
                segment_id=segment_id,
                timestamp=time.time(),
                audio_duration_ms=audio_duration_ms,
                audio_capture_start=time.time()
            )
            self._metrics[segment_id] = metrics
            self._current_segment_id = segment_id
            return metrics
    
    def mark_event(self, segment_id: int, event_name: str):
        """Mark a timestamp event for a segment."""
        with self._lock:
            if segment_id not in self._metrics:
                logger.warning(f"Segment {segment_id} not found for event {event_name}")
                return
            
            metrics = self._metrics[segment_id]
            now = time.time()
            
            if event_name == "vad_start":
                metrics.vad_start = now
            elif event_name == "vad_end":
                metrics.vad_end = now
                metrics.vad_latency_ms = (now - metrics.vad_start) * 1000
            elif event_name == "asr_start":
                metrics.asr_start = now
            elif event_name == "asr_end":
                metrics.asr_end = now
                metrics.asr_latency_ms = (now - metrics.asr_start) * 1000
            elif event_name == "translation_start":
                metrics.translation_start = now
            elif event_name == "translation_end":
                metrics.translation_end = now
                metrics.translation_latency_ms = (now - metrics.translation_start) * 1000
            elif event_name == "complete":
                metrics.total_latency_ms = (now - metrics.timestamp) * 1000
    
    def update_metrics(self, segment_id: int, **kwargs):
        """Update metrics with additional data."""
        with self._lock:
            if segment_id in self._metrics:
                for key, value in kwargs.items():
                    setattr(self._metrics[segment_id], key, value)
    
    def finalize_segment(self, segment_id: int) -> Optional[LatencyMetrics]:
        """Finalize a segment and add to statistics."""
        with self._lock:
            if segment_id not in self._metrics:
                return None
            
            metrics = self._metrics[segment_id]
            
            # Ensure total latency is set
            if metrics.total_latency_ms == 0:
                metrics.total_latency_ms = (time.time() - metrics.timestamp) * 1000
            
            # Add to history and stats
            self._history.append(metrics)
            self._stats.add_metrics(metrics)
            
            # Remove from active metrics
            del self._metrics[segment_id]
            
            return metrics
    
    def get_metrics(self, segment_id: int) -> Optional[LatencyMetrics]:
        """Get metrics for a specific segment."""
        with self._lock:
            return self._metrics.get(segment_id)
    
    def get_current_metrics(self) -> Optional[LatencyMetrics]:
        """Get metrics for the current segment."""
        if self._current_segment_id is not None:
            return self.get_metrics(self._current_segment_id)
        return None
    
    def get_summary(self) -> Dict:
        """Get statistical summary."""
        return self._stats.get_summary()
    
    def print_summary(self):
        """Print formatted summary."""
        self._stats.print_summary()
    
    def export_json(self, filepath: str):
        """Export all metrics to JSON file."""
        with self._lock:
            data = {
                "summary": self._stats.get_summary(),
                "segments": [asdict(m) for m in self._history]
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        logger.info(f"Latency metrics exported to {filepath}")
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._history.clear()
            self._stats = PipelineStatistics()
            self._current_segment_id = None
        logger.info("Latency analyzer reset")


class BufferOptimizer:
    """
    Optimizes buffer sizes based on measured latency.
    
    Strategy:
    - Measure actual processing latency
    - Calculate required buffer size
    - Adjust dynamically based on performance
    """
    
    def __init__(self, 
                 target_latency_ms: float = 1000.0,
                 max_buffer_ms: float = 5000.0,
                 min_buffer_ms: float = 500.0):
        """
        Initialize buffer optimizer.
        
        Args:
            target_latency_ms: Target end-to-end latency
            max_buffer_ms: Maximum allowed buffer size
            min_buffer_ms: Minimum required buffer size
        """
        self.target_latency_ms = target_latency_ms
        self.max_buffer_ms = max_buffer_ms
        self.min_buffer_ms = min_buffer_ms
        
        self._measured_latencies: deque = deque(maxlen=50)
        self._current_buffer_ms = min_buffer_ms
        
        logger.info(f"Buffer optimizer initialized: target={target_latency_ms}ms, "
                   f"buffer={self._current_buffer_ms}ms")
    
    def report_latency(self, latency_ms: float):
        """Report a measured latency."""
        self._measured_latencies.append(latency_ms)
    
    def get_recommended_buffer_ms(self) -> float:
        """
        Calculate recommended buffer size based on recent latencies.
        
        Returns:
            Recommended buffer size in milliseconds
        """
        if len(self._measured_latencies) < 5:
            return self._current_buffer_ms
        
        # Use 95th percentile of recent latencies
        sorted_latencies = sorted(self._measured_latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies)-1)]
        
        # Calculate required buffer: p95_latency + safety_margin
        safety_margin = 200  # 200ms safety margin
        required_buffer = p95_latency + safety_margin
        
        # Constrain to valid range
        recommended = max(self.min_buffer_ms, 
                         min(required_buffer, self.max_buffer_ms))
        
        # Smooth transitions (don't change too quickly)
        alpha = 0.3  # Smoothing factor
        self._current_buffer_ms = (alpha * recommended + 
                                   (1 - alpha) * self._current_buffer_ms)
        
        return self._current_buffer_ms
    
    def get_status(self) -> Dict:
        """Get current optimization status."""
        if len(self._measured_latencies) < 5:
            return {
                "status": "calibrating",
                "current_buffer_ms": self._current_buffer_ms,
                "samples_collected": len(self._measured_latencies)
            }
        
        sorted_latencies = sorted(self._measured_latencies)
        return {
            "status": "optimized" if sorted_latencies[-1] < self.target_latency_ms else "degraded",
            "current_buffer_ms": self._current_buffer_ms,
            "p50_latency_ms": sorted_latencies[len(sorted_latencies)//2],
            "p95_latency_ms": sorted_latencies[int(len(sorted_latencies)*0.95)],
            "max_latency_ms": sorted_latencies[-1],
            "target_latency_ms": self.target_latency_ms
        }


def create_debug_callback(analyzer: LatencyAnalyzer) -> Callable:
    """
    Create a callback function for pipeline debugging.
    
    Usage:
        analyzer = LatencyAnalyzer()
        callback = create_debug_callback(analyzer)
        
        # In pipeline
        callback("vad_start", segment_id)
        callback("asr_end", segment_id, latency_ms=500)
    """
    def debug_callback(event: str, segment_id: int, **kwargs):
        if event == "segment_start":
            analyzer.start_segment(segment_id, kwargs.get('audio_duration_ms', 0))
        elif event in ["vad_start", "vad_end", "asr_start", "asr_end", 
                       "translation_start", "translation_end", "complete"]:
            analyzer.mark_event(segment_id, event)
        elif event == "segment_complete":
            # Update any additional fields
            analyzer.update_metrics(segment_id, **kwargs)
            metrics = analyzer.finalize_segment(segment_id)
            if metrics and metrics.total_latency_ms > 2000:
                logger.warning(f"High latency detected: {metrics.total_latency_ms:.0f}ms "
                              f"for segment {segment_id}")
        elif event == "print_summary":
            analyzer.print_summary()
    
    return debug_callback


# Convenience function for quick analysis
def analyze_pipeline_performance(json_file: str):
    """
    Analyze pipeline performance from exported JSON file.
    
    Args:
        json_file: Path to exported metrics JSON file
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    print("\n" + "=" * 70)
    print("📊 PIPELINE PERFORMANCE ANALYSIS")
    print("=" * 70)
    
    summary = data.get('summary', {})
    print(f"\nSession Runtime: {summary.get('runtime_seconds', 0):.1f}s")
    print(f"Total Segments Processed: {summary.get('total_segments', 0)}")
    
    # RTF analysis
    rtf = summary.get('real_time_factor', {})
    if rtf.get('count', 0) > 0:
        print(f"\n🎯 Real-Time Factor: {rtf.get('mean', 0):.3f}x")
        if rtf.get('mean', 0) > 1.0:
            print("   ⚠️  System is NOT real-time capable")
            print("   💡 Recommendations:")
            print("      - Use smaller ASR model (tiny/base instead of small/medium)")
            print("      - Enable GPU acceleration (CUDA/MPS)")
            print("      - Reduce VAD sensitivity to process longer segments")
            print("      - Increase buffer size to compensate")
        else:
            print("   ✅ System is real-time capable")
    
    # Latency breakdown
    print("\n⏱️  Latency Breakdown:")
    for component in ['vad', 'asr', 'translation', 'total']:
        key = f"{component}_latency_ms"
        stats = summary.get(key, {})
        if stats.get('count', 0) > 0:
            print(f"   {component.upper():12s}: {stats.get('mean', 0):6.1f}ms "
                  f"(p95: {stats.get('p95', 0):6.1f}ms, max: {stats.get('max', 0):6.1f}ms)")
    
    # Audio duration analysis
    audio = summary.get('audio_duration_ms', {})
    if audio.get('count', 0) > 0:
        print(f"\n🎵 Audio Segment Duration:")
        print(f"   Mean: {audio.get('mean', 0)/1000:.2f}s")
        print(f"   Max:  {audio.get('max', 0)/1000:.2f}s")
        if audio.get('max', 0) > 10000:
            print("   ⚠️  Some segments are very long (>10s)")
            print("   💡 Consider reducing max_segment_duration_ms")
    
    # Buffer recommendations
    total = summary.get('total_latency_ms', {})
    if total.get('mean', 0) > 0:
        recommended_buffer = total.get('p95', 0) + 200
        print(f"\n📦 Recommended Buffer Size: {recommended_buffer:.0f}ms")
        print(f"   (Based on p95 latency + 200ms safety margin)")
    
    print("=" * 70)


if __name__ == "__main__":
    # Example usage
    analyzer = LatencyAnalyzer()
    
    # Simulate some segments
    for i in range(10):
        metrics = analyzer.start_segment(i, audio_duration_ms=3000)
        time.sleep(0.01)  # Simulate processing
        analyzer.mark_event(i, "vad_end")
        time.sleep(0.05)
        analyzer.mark_event(i, "asr_end")
        time.sleep(0.1)
        analyzer.mark_event(i, "translation_end")
        time.sleep(0.01)
        analyzer.mark_event(i, "complete")
        analyzer.finalize_segment(i)
    
    analyzer.print_summary()
