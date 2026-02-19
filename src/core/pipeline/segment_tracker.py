"""
Segment Tracker - Week 0 Critical Fix

Tracks segments through the entire pipeline to detect and prevent data loss.
Provides end-to-end tracing with UUIDs and comprehensive logging.
"""

import uuid
import time
import logging
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class SegmentStage(Enum):
    """Pipeline stages for segment tracking."""
    CAPTURED = "captured"      # Audio captured
    VAD_QUEUED = "vad_queued"  # In VAD queue
    VAD_PROCESSED = "vad_processed"  # VAD detection complete
    ASR_QUEUED = "asr_queued"  # In ASR queue
    ASR_PROCESSING = "asr_processing"  # ASR worker picked up
    ASR_COMPLETE = "asr_complete"  # ASR done
    TRANSLATION_QUEUED = "translation_queued"  # In translation queue
    TRANSLATION_PROCESSING = "translation_processing"  # Translation worker picked up
    TRANSLATION_COMPLETE = "translation_complete"  # Translation done
    OUTPUT_QUEUED = "output_queued"  # In output queue
    OUTPUT_EMITTED = "output_emitted"  # Output callback called
    DROPPED = "dropped"  # Segment was dropped (error/queue full)
    ERROR = "error"  # Error occurred


@dataclass
class SegmentTrace:
    """Complete trace of a segment through the pipeline."""
    segment_id: int
    uuid: str
    created_at: float
    stage_timestamps: Dict[SegmentStage, float] = field(default_factory=dict)
    current_stage: SegmentStage = SegmentStage.CAPTURED
    error_message: Optional[str] = None
    dropped_reason: Optional[str] = None
    audio_duration_ms: float = 0.0
    asr_text: Optional[str] = None
    translation_text: Optional[str] = None
    
    def record_stage(self, stage: SegmentStage, timestamp: Optional[float] = None):
        """Record segment entering a new stage."""
        if timestamp is None:
            timestamp = time.time()
        self.stage_timestamps[stage] = timestamp
        self.current_stage = stage
    
    def get_stage_duration(self, from_stage: SegmentStage, to_stage: SegmentStage) -> float:
        """Get duration between two stages in milliseconds."""
        if from_stage not in self.stage_timestamps or to_stage not in self.stage_timestamps:
            return -1.0
        return (self.stage_timestamps[to_stage] - self.stage_timestamps[from_stage]) * 1000
    
    def get_total_duration_ms(self) -> float:
        """Get total pipeline duration in milliseconds."""
        if SegmentStage.OUTPUT_EMITTED not in self.stage_timestamps:
            return -1.0
        return (self.stage_timestamps[SegmentStage.OUTPUT_EMITTED] - self.created_at) * 1000
    
    def get_queue_wait_times(self) -> Dict[str, float]:
        """Get time spent in each queue."""
        waits = {}
        
        # VAD queue wait
        if SegmentStage.VAD_QUEUED in self.stage_timestamps and \
           SegmentStage.VAD_PROCESSED in self.stage_timestamps:
            waits['vad_queue_ms'] = self.get_stage_duration(
                SegmentStage.VAD_QUEUED, SegmentStage.VAD_PROCESSED
            )
        
        # ASR queue wait
        if SegmentStage.ASR_QUEUED in self.stage_timestamps and \
           SegmentStage.ASR_PROCESSING in self.stage_timestamps:
            waits['asr_queue_ms'] = self.get_stage_duration(
                SegmentStage.ASR_QUEUED, SegmentStage.ASR_PROCESSING
            )
        
        # Translation queue wait
        if SegmentStage.TRANSLATION_QUEUED in self.stage_timestamps and \
           SegmentStage.TRANSLATION_PROCESSING in self.stage_timestamps:
            waits['translation_queue_ms'] = self.get_stage_duration(
                SegmentStage.TRANSLATION_QUEUED, SegmentStage.TRANSLATION_PROCESSING
            )
        
        return waits


class SegmentTracker:
    """
    Tracks all segments through the pipeline to detect loss.
    
    Week 0 Critical Fix: Ensures no segments are silently lost.
    """
    
    def __init__(self, alert_on_drop: bool = True):
        self._traces: Dict[str, SegmentTrace] = {}
        self._segment_id_to_uuid: Dict[int, str] = {}
        self._lock = threading.Lock()
        self._alert_on_drop = alert_on_drop
        
        # Statistics
        self._stats = {
            'total_created': 0,
            'total_emitted': 0,
            'total_dropped': 0,
            'total_errors': 0,
            'current_in_flight': 0,
        }
        
        # Callbacks for alerts
        self._drop_callbacks: List[Callable[[SegmentTrace], None]] = []
        self._error_callbacks: List[Callable[[SegmentTrace], None]] = []
        
        logger.info("SegmentTracker initialized (Week 0 Critical Fix)")
    
    def create_segment(self, segment_id: int, audio_duration_ms: float = 0.0) -> str:
        """
        Create a new segment trace.
        
        Args:
            segment_id: The sequential segment ID
            audio_duration_ms: Duration of audio in milliseconds
            
        Returns:
            UUID for the segment
        """
        segment_uuid = str(uuid.uuid4())
        now = time.time()
        
        trace = SegmentTrace(
            segment_id=segment_id,
            uuid=segment_uuid,
            created_at=now,
            audio_duration_ms=audio_duration_ms
        )
        trace.record_stage(SegmentStage.CAPTURED, now)
        
        with self._lock:
            self._traces[segment_uuid] = trace
            self._segment_id_to_uuid[segment_id] = segment_uuid
            self._stats['total_created'] += 1
            self._stats['current_in_flight'] += 1
        
        logger.debug(f"Segment {segment_id} created with UUID {segment_uuid[:8]}")
        return segment_uuid
    
    def record_stage(self, segment_uuid: str, stage: SegmentStage, 
                     error_message: Optional[str] = None):
        """Record a segment entering a new stage."""
        with self._lock:
            if segment_uuid not in self._traces:
                logger.warning(f"Unknown segment UUID: {segment_uuid[:8]}")
                return
            
            trace = self._traces[segment_uuid]
            trace.record_stage(stage)
            
            if error_message:
                trace.error_message = error_message
                self._stats['total_errors'] += 1
                
                # Alert on error
                for callback in self._error_callbacks:
                    try:
                        callback(trace)
                    except Exception as e:
                        logger.error(f"Error callback failed: {e}")
            
            if stage == SegmentStage.OUTPUT_EMITTED:
                self._stats['total_emitted'] += 1
                self._stats['current_in_flight'] -= 1
            elif stage == SegmentStage.DROPPED:
                self._stats['total_dropped'] += 1
                self._stats['current_in_flight'] -= 1
                
                # Alert on drop
                if self._alert_on_drop:
                    logger.error(
                        f"🚨 SEGMENT DROPPED: ID={trace.segment_id}, "
                        f"Reason={trace.dropped_reason}, "
                        f"UUID={segment_uuid[:8]}"
                    )
                    for callback in self._drop_callbacks:
                        try:
                            callback(trace)
                        except Exception as e:
                            logger.error(f"Drop callback failed: {e}")
    
    def record_drop(self, segment_uuid: str, reason: str):
        """Record a segment being dropped."""
        with self._lock:
            if segment_uuid in self._traces:
                self._traces[segment_uuid].dropped_reason = reason
        
        self.record_stage(segment_uuid, SegmentStage.DROPPED)
    
    def record_error(self, segment_uuid: str, error: str):
        """Record an error for a segment."""
        self.record_stage(segment_uuid, SegmentStage.ERROR, error)
    
    def update_asr_result(self, segment_uuid: str, asr_text: str):
        """Update ASR result for a segment."""
        with self._lock:
            if segment_uuid in self._traces:
                self._traces[segment_uuid].asr_text = asr_text
    
    def update_translation_result(self, segment_uuid: str, translation_text: str):
        """Update translation result for a segment."""
        with self._lock:
            if segment_uuid in self._traces:
                self._traces[segment_uuid].translation_text = translation_text
    
    def get_trace(self, segment_uuid: str) -> Optional[SegmentTrace]:
        """Get trace for a segment."""
        with self._lock:
            return self._traces.get(segment_uuid)
    
    def get_trace_by_id(self, segment_id: int) -> Optional[SegmentTrace]:
        """Get trace by segment ID."""
        with self._lock:
            uuid = self._segment_id_to_uuid.get(segment_id)
            if uuid:
                return self._traces.get(uuid)
            return None
    
    def get_all_traces(self) -> List[SegmentTrace]:
        """Get all traces."""
        with self._lock:
            return list(self._traces.values())
    
    def get_incomplete_traces(self) -> List[SegmentTrace]:
        """Get traces that haven't reached OUTPUT_EMITTED or DROPPED."""
        with self._lock:
            return [
                trace for trace in self._traces.values()
                if trace.current_stage not in [SegmentStage.OUTPUT_EMITTED, SegmentStage.DROPPED]
            ]
    
    def get_dropped_traces(self) -> List[SegmentTrace]:
        """Get all dropped segments."""
        with self._lock:
            return [
                trace for trace in self._traces.values()
                if trace.current_stage == SegmentStage.DROPPED
            ]
    
    def get_stats(self) -> Dict:
        """Get tracking statistics."""
        with self._lock:
            stats = self._stats.copy()
            
            # Calculate loss rate
            if stats['total_created'] > 0:
                accounted = stats['total_emitted'] + stats['total_dropped'] + stats['total_errors']
                stats['unaccounted'] = stats['total_created'] - accounted
                stats['loss_rate_percent'] = (
                    (stats['total_dropped'] + stats['total_errors'] + stats['unaccounted']) /
                    stats['total_created'] * 100
                )
            else:
                stats['loss_rate_percent'] = 0.0
                stats['unaccounted'] = 0
            
            return stats
    
    def reset_stats(self):
        """Reset statistics (for testing)."""
        with self._lock:
            self._stats = {
                'total_created': 0,
                'total_emitted': 0,
                'total_dropped': 0,
                'total_errors': 0,
                'current_in_flight': 0,
            }
            self._traces.clear()
            self._segment_id_to_uuid.clear()
    
    def on_drop(self, callback: Callable[[SegmentTrace], None]):
        """Register a callback for when segments are dropped."""
        self._drop_callbacks.append(callback)
    
    def on_error(self, callback: Callable[[SegmentTrace], None]):
        """Register a callback for when segments have errors."""
        self._error_callbacks.append(callback)
    
    def print_summary(self):
        """Print a summary of tracking statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 SEGMENT TRACKER SUMMARY (Week 0 Critical Fix)")
        print("=" * 60)
        print(f"   Total Created:   {stats['total_created']}")
        print(f"   Total Emitted:   {stats['total_emitted']}")
        print(f"   Total Dropped:   {stats['total_dropped']}")
        print(f"   Total Errors:    {stats['total_errors']}")
        print(f"   Unaccounted:     {stats['unaccounted']}")
        print(f"   In Flight:       {stats['current_in_flight']}")
        print("-" * 60)
        
        loss_rate = stats['loss_rate_percent']
        if loss_rate == 0:
            print(f"   ✅ LOSS RATE:    {loss_rate:.2f}% (PERFECT)")
        elif loss_rate < 1:
            print(f"   ⚠️  LOSS RATE:    {loss_rate:.2f}% (ACCEPTABLE)")
        else:
            print(f"   🚨 LOSS RATE:    {loss_rate:.2f}% (CRITICAL - BUG!)")
        
        print("=" * 60)
        
        # Show dropped segments if any
        dropped = self.get_dropped_traces()
        if dropped:
            print("\n🚨 DROPPED SEGMENTS:")
            for trace in dropped[:10]:  # Show first 10
                print(f"   Segment {trace.segment_id}: {trace.dropped_reason}")
            if len(dropped) > 10:
                print(f"   ... and {len(dropped) - 10} more")
        
        # Show incomplete segments if any
        incomplete = self.get_incomplete_traces()
        if incomplete:
            print(f"\n⏳ INCOMPLETE SEGMENTS ({len(incomplete)}):")
            for trace in incomplete[:5]:
                age_sec = time.time() - trace.created_at
                print(f"   Segment {trace.segment_id}: {trace.current_stage.value} ({age_sec:.1f}s old)")
        
        return stats


# Global tracker instance (for ease of use)
_global_tracker: Optional[SegmentTracker] = None


def get_global_tracker() -> SegmentTracker:
    """Get or create the global segment tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = SegmentTracker()
    return _global_tracker


def reset_global_tracker():
    """Reset the global tracker (for testing)."""
    global _global_tracker
    _global_tracker = SegmentTracker()
