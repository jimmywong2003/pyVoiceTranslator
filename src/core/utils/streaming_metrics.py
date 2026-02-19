"""
Streaming Metrics - Phase 1.1

Collects and tracks streaming-specific metrics for the translation pipeline:
- TTFT (Time to First Token): Speech start → First draft visible
- Meaning Latency: Speech start → First translated meaning  
- Ear-to-Voice Lag: Silence → Final translation
- Draft Stability: % of draft words matching final
- ASR Call Frequency: Track 3x overhead
"""

import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class SegmentMetrics:
    """Metrics for a single segment."""
    segment_id: int
    segment_uuid: str
    
    # Timing (in milliseconds)
    speech_start_time: float = 0.0  # When speech started
    speech_end_time: float = 0.0    # When silence detected (VAD)
    first_draft_time: float = 0.0   # When first draft was shown
    first_meaning_time: float = 0.0  # When first translation was shown
    final_output_time: float = 0.0  # When final translation was shown
    
    # ASR tracking
    asr_calls: int = 0              # Number of ASR calls for this segment
    draft_count: int = 0            # Number of drafts generated
    
    # Content
    draft_texts: List[str] = field(default_factory=list)
    draft_translations: List[str] = field(default_factory=list)
    final_text: str = ""
    final_translation: str = ""
    
    def calculate_ttft_ms(self) -> Optional[float]:
        """Time to First Token: Speech start → First draft visible."""
        if self.speech_start_time and self.first_draft_time:
            return (self.first_draft_time - self.speech_start_time) * 1000
        return None
    
    def calculate_meaning_latency_ms(self) -> Optional[float]:
        """Meaning Latency: Speech start → First translated meaning."""
        if self.speech_start_time and self.first_meaning_time:
            return (self.first_meaning_time - self.speech_start_time) * 1000
        return None
    
    def calculate_ear_to_voice_lag_ms(self) -> Optional[float]:
        """Ear-to-Voice Lag: Silence → Final translation."""
        if self.speech_end_time and self.final_output_time:
            return (self.final_output_time - self.speech_end_time) * 1000
        return None
    
    def calculate_draft_stability(self) -> float:
        """Calculate draft stability as similarity between last draft and final."""
        if not self.draft_texts or not self.final_text:
            return 0.0
        
        from difflib import SequenceMatcher
        last_draft = self.draft_texts[-1]
        similarity = SequenceMatcher(None, last_draft, self.final_text).ratio()
        return similarity


@dataclass  
class StreamingMetricsSnapshot:
    """Snapshot of streaming metrics at a point in time."""
    timestamp: float
    
    # Latency metrics (ms)
    avg_ttft_ms: float = 0.0
    avg_meaning_latency_ms: float = 0.0
    avg_ear_to_voice_lag_ms: float = 0.0
    
    # Quality metrics
    avg_draft_stability: float = 0.0
    avg_asr_calls_per_segment: float = 0.0
    
    # Throughput
    segments_processed: int = 0
    drafts_generated: int = 0
    
    # Compute overhead
    asr_call_frequency: float = 0.0  # ASR calls per second


class StreamingMetricsCollector:
    """
    Collects and tracks streaming-specific metrics.
    
    Phase 1.1: Metrics collection for streaming optimization.
    """
    
    def __init__(self, history_size: int = 100):
        self._segments: Dict[str, SegmentMetrics] = {}
        self._lock = threading.Lock()
        self._history_size = history_size
        
        # Rolling averages
        self._ttft_history: deque = deque(maxlen=history_size)
        self._meaning_latency_history: deque = deque(maxlen=history_size)
        self._ear_to_voice_history: deque = deque(maxlen=history_size)
        self._stability_history: deque = deque(maxlen=history_size)
        
        # Counters
        self._total_asr_calls = 0
        self._total_segments = 0
        self._total_drafts = 0
        self._start_time = time.time()
        
        logger.info("StreamingMetricsCollector initialized (Phase 1.1)")
    
    def start_segment(self, segment_uuid: str, segment_id: int, 
                      speech_start_time: Optional[float] = None):
        """Record the start of a new speech segment."""
        if speech_start_time is None:
            speech_start_time = time.time()
        
        with self._lock:
            self._segments[segment_uuid] = SegmentMetrics(
                segment_id=segment_id,
                segment_uuid=segment_uuid,
                speech_start_time=speech_start_time
            )
            self._total_segments += 1
        
        logger.debug(f"Segment {segment_id} started at {speech_start_time}")
    
    def record_speech_end(self, segment_uuid: str, 
                          speech_end_time: Optional[float] = None):
        """Record when speech ends (silence detected)."""
        if speech_end_time is None:
            speech_end_time = time.time()
        
        with self._lock:
            if segment_uuid in self._segments:
                self._segments[segment_uuid].speech_end_time = speech_end_time
    
    def record_first_draft(self, segment_uuid: str, draft_text: str,
                          draft_time: Optional[float] = None):
        """Record the first draft output."""
        if draft_time is None:
            draft_time = time.time()
        
        with self._lock:
            if segment_uuid in self._segments:
                metrics = self._segments[segment_uuid]
                if metrics.first_draft_time == 0.0:
                    metrics.first_draft_time = draft_time
                    ttft = (draft_time - metrics.speech_start_time) * 1000
                    self._ttft_history.append(ttft)
                    logger.debug(f"First draft TTFT: {ttft:.0f}ms")
                
                metrics.draft_texts.append(draft_text)
                metrics.draft_count += 1
                self._total_drafts += 1
    
    def record_first_translation(self, segment_uuid: str, 
                                 translation_text: str,
                                 translation_time: Optional[float] = None):
        """Record the first translated meaning."""
        if translation_time is None:
            translation_time = time.time()
        
        with self._lock:
            if segment_uuid in self._segments:
                metrics = self._segments[segment_uuid]
                if metrics.first_meaning_time == 0.0:
                    metrics.first_meaning_time = translation_time
                    meaning_latency = (translation_time - metrics.speech_start_time) * 1000
                    self._meaning_latency_history.append(meaning_latency)
                    logger.debug(f"First meaning latency: {meaning_latency:.0f}ms")
                
                metrics.draft_translations.append(translation_text)
    
    def record_final_output(self, segment_uuid: str,
                           final_text: str,
                           final_translation: str,
                           output_time: Optional[float] = None):
        """Record the final output."""
        if output_time is None:
            output_time = time.time()
        
        with self._lock:
            if segment_uuid in self._segments:
                metrics = self._segments[segment_uuid]
                metrics.final_output_time = output_time
                metrics.final_text = final_text
                metrics.final_translation = final_translation
                
                # Calculate ear-to-voice lag
                if metrics.speech_end_time > 0:
                    lag = (output_time - metrics.speech_end_time) * 1000
                    self._ear_to_voice_history.append(lag)
                
                # Calculate stability
                stability = metrics.calculate_draft_stability()
                self._stability_history.append(stability)
    
    def record_asr_call(self, segment_uuid: str):
        """Record an ASR call for a segment."""
        with self._lock:
            if segment_uuid in self._segments:
                self._segments[segment_uuid].asr_calls += 1
            self._total_asr_calls += 1
    
    def get_segment_metrics(self, segment_uuid: str) -> Optional[SegmentMetrics]:
        """Get metrics for a specific segment."""
        with self._lock:
            return self._segments.get(segment_uuid)
    
    def get_snapshot(self) -> StreamingMetricsSnapshot:
        """Get current metrics snapshot."""
        with self._lock:
            elapsed = time.time() - self._start_time
            
            snapshot = StreamingMetricsSnapshot(
                timestamp=time.time(),
                avg_ttft_ms=sum(self._ttft_history) / len(self._ttft_history) if self._ttft_history else 0,
                avg_meaning_latency_ms=sum(self._meaning_latency_history) / len(self._meaning_latency_history) if self._meaning_latency_history else 0,
                avg_ear_to_voice_lag_ms=sum(self._ear_to_voice_history) / len(self._ear_to_voice_history) if self._ear_to_voice_history else 0,
                avg_draft_stability=sum(self._stability_history) / len(self._stability_history) if self._stability_history else 0,
                segments_processed=self._total_segments,
                drafts_generated=self._total_drafts,
            )
            
            # Calculate ASR call frequency
            if elapsed > 0:
                snapshot.asr_call_frequency = self._total_asr_calls / elapsed
            
            # Calculate average ASR calls per segment
            if self._total_segments > 0:
                snapshot.avg_asr_calls_per_segment = self._total_asr_calls / self._total_segments
            
            return snapshot
    
    def print_summary(self):
        """Print a summary of streaming metrics."""
        snapshot = self.get_snapshot()
        
        print("\n" + "=" * 60)
        print("📊 STREAMING METRICS SUMMARY (Phase 1.1)")
        print("=" * 60)
        
        print(f"\n  Latency Metrics:")
        print(f"    TTFT (Time to First Token):      {snapshot.avg_ttft_ms:.0f}ms (target: <2000ms)")
        print(f"    Meaning Latency:                  {snapshot.avg_meaning_latency_ms:.0f}ms (target: <2000ms)")
        print(f"    Ear-to-Voice Lag:                 {snapshot.avg_ear_to_voice_lag_ms:.0f}ms (target: <500ms)")
        
        print(f"\n  Quality Metrics:")
        print(f"    Draft Stability:                  {snapshot.avg_draft_stability*100:.1f}% (target: >70%)")
        
        print(f"\n  Compute Metrics:")
        print(f"    ASR Calls per Segment:            {snapshot.avg_asr_calls_per_segment:.2f}")
        print(f"    ASR Call Frequency:               {snapshot.asr_call_frequency:.2f}/sec")
        print(f"    Total Segments:                   {snapshot.segments_processed}")
        print(f"    Total Drafts:                     {snapshot.drafts_generated}")
        
        # Check targets
        print(f"\n  Target Status:")
        targets_met = 0
        targets_total = 4
        
        if snapshot.avg_ttft_ms < 2000:
            print(f"    ✅ TTFT: {snapshot.avg_ttft_ms:.0f}ms < 2000ms")
            targets_met += 1
        else:
            print(f"    ❌ TTFT: {snapshot.avg_ttft_ms:.0f}ms > 2000ms")
        
        if snapshot.avg_meaning_latency_ms < 2000:
            print(f"    ✅ Meaning Latency: {snapshot.avg_meaning_latency_ms:.0f}ms < 2000ms")
            targets_met += 1
        else:
            print(f"    ❌ Meaning Latency: {snapshot.avg_meaning_latency_ms:.0f}ms > 2000ms")
        
        if snapshot.avg_ear_to_voice_lag_ms < 500:
            print(f"    ✅ Ear-to-Voice: {snapshot.avg_ear_to_voice_lag_ms:.0f}ms < 500ms")
            targets_met += 1
        else:
            print(f"    ❌ Ear-to-Voice: {snapshot.avg_ear_to_voice_lag_ms:.0f}ms > 500ms")
        
        if snapshot.avg_draft_stability > 0.7:
            print(f"    ✅ Stability: {snapshot.avg_draft_stability*100:.1f}% > 70%")
            targets_met += 1
        else:
            print(f"    ❌ Stability: {snapshot.avg_draft_stability*100:.1f}% < 70%")
        
        print(f"\n  Overall: {targets_met}/{targets_total} targets met")
        print("=" * 60)
        
        return snapshot


# Global collector instance
_global_collector: Optional[StreamingMetricsCollector] = None


def get_global_collector() -> StreamingMetricsCollector:
    """Get or create the global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = StreamingMetricsCollector()
    return _global_collector


def reset_global_collector():
    """Reset the global collector (for testing)."""
    global _global_collector
    _global_collector = StreamingMetricsCollector()
