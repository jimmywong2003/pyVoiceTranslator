"""
Adaptive Draft Controller - Phase 1.1

Decides when to trigger draft ASR/translation based on:
- Time since last draft (every 2 seconds)
- Speech pause detection (skip if paused > 500ms)
- Compute queue depth (skip if backed up)
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VADState:
    """Current VAD state for adaptive decisions."""
    is_speaking: bool = False
    recent_pause_ms: float = 0.0
    speech_duration_ms: float = 0.0
    silence_duration_ms: float = 0.0


class AdaptiveDraftController:
    """
    Controls when to generate drafts based on context.
    
    Phase 1.1: Adaptive draft triggering to manage compute overhead.
    """
    
    # Configuration
    DEFAULT_DRAFT_INTERVAL_MS = 2000  # Draft every 2 seconds
    PAUSE_THRESHOLD_MS = 500          # Skip if paused > 500ms
    MAX_QUEUE_DEPTH = 2               # Skip if > 2 segments in queue
    
    def __init__(self, 
                 draft_interval_ms: float = DEFAULT_DRAFT_INTERVAL_MS,
                 pause_threshold_ms: float = PAUSE_THRESHOLD_MS,
                 max_queue_depth: int = MAX_QUEUE_DEPTH):
        """
        Initialize adaptive controller.
        
        Args:
            draft_interval_ms: Minimum time between drafts
            pause_threshold_ms: Skip draft if speech paused longer than this
            max_queue_depth: Skip draft if compute queue deeper than this
        """
        self.draft_interval_ms = draft_interval_ms
        self.pause_threshold_ms = pause_threshold_ms
        self.max_queue_depth = max_queue_depth
        
        # State tracking
        self._last_draft_time: Optional[float] = None
        self._segment_start_time: Optional[float] = None
        
        # Statistics
        self._drafts_triggered = 0
        self._drafts_skipped_time = 0
        self._drafts_skipped_pause = 0
        self._drafts_skipped_queue = 0
        
        logger.info(
            f"AdaptiveDraftController initialized ("
            f"interval={draft_interval_ms}ms, "
            f"pause_threshold={pause_threshold_ms}ms, "
            f"max_queue={max_queue_depth})"
        )
    
    def start_segment(self, start_time: Optional[float] = None):
        """Called when a new speech segment starts."""
        if start_time is None:
            start_time = time.time()
        
        self._segment_start_time = start_time
        self._last_draft_time = None  # Reset for new segment
        
        logger.debug(f"Segment started at {start_time}")
    
    def should_trigger_draft(self, 
                           buffer_duration_ms: float,
                           vad_state: VADState,
                           compute_queue_depth: int = 0) -> bool:
        """
        Decide whether to trigger a draft.
        
        Args:
            buffer_duration_ms: How much audio is buffered (since segment start)
            vad_state: Current VAD state
            compute_queue_depth: Current depth of compute queue
            
        Returns:
            True if draft should be triggered, False otherwise
        """
        now = time.time()
        
        # Check 1: Minimum interval between drafts
        if self._last_draft_time is not None:
            time_since_last_draft = (now - self._last_draft_time) * 1000
            if time_since_last_draft < self.draft_interval_ms:
                # Too soon since last draft
                self._drafts_skipped_time += 1
                logger.debug(
                    f"Skipping draft: {time_since_last_draft:.0f}ms since last "
                    f"(need {self.draft_interval_ms}ms)"
                )
                return False
        
        # Check 2: Speech pause detection
        if vad_state.recent_pause_ms > self.pause_threshold_ms:
            # Speech has paused, likely end of thought
            self._drafts_skipped_pause += 1
            logger.debug(
                f"Skipping draft: pause of {vad_state.recent_pause_ms:.0f}ms detected "
                f"(threshold {self.pause_threshold_ms}ms)"
            )
            return False
        
        # Check 3: Compute queue depth
        if compute_queue_depth > self.max_queue_depth:
            # Compute is backed up, don't add more work
            self._drafts_skipped_queue += 1
            logger.debug(
                f"Skipping draft: queue depth {compute_queue_depth} "
                f"> {self.max_queue_depth}"
            )
            return False
        
        # All checks passed, trigger draft
        self._last_draft_time = now
        self._drafts_triggered += 1
        
        logger.debug(
            f"Triggering draft: buffer={buffer_duration_ms:.0f}ms, "
            f"pause={vad_state.recent_pause_ms:.0f}ms, "
            f"queue={compute_queue_depth}"
        )
        return True
    
    def get_stats(self) -> dict:
        """Get controller statistics."""
        total_decisions = (
            self._drafts_triggered + 
            self._drafts_skipped_time + 
            self._drafts_skipped_pause + 
            self._drafts_skipped_queue
        )
        
        return {
            'drafts_triggered': self._drafts_triggered,
            'drafts_skipped_time': self._drafts_skipped_time,
            'drafts_skipped_pause': self._drafts_skipped_pause,
            'drafts_skipped_queue': self._drafts_skipped_queue,
            'total_decisions': total_decisions,
            'trigger_rate': (
                self._drafts_triggered / total_decisions * 100 
                if total_decisions > 0 else 0
            ),
        }
    
    def print_stats(self):
        """Print controller statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 ADAPTIVE DRAFT CONTROLLER STATS (Phase 1.1)")
        print("=" * 60)
        
        print(f"\n  Drafts Triggered:     {stats['drafts_triggered']}")
        print(f"  Skipped (time):       {stats['drafts_skipped_time']}")
        print(f"  Skipped (pause):      {stats['drafts_skipped_pause']}")
        print(f"  Skipped (queue):      {stats['drafts_skipped_queue']}")
        
        if stats['total_decisions'] > 0:
            print(f"\n  Trigger Rate:         {stats['trigger_rate']:.1f}%")
            print(f"  Skip Rate:            {100 - stats['trigger_rate']:.1f}%")
        
        print("=" * 60)


class SimpleDraftController:
    """
    Simple draft controller that triggers every N seconds.
    
    Use this for testing or when adaptive behavior is not needed.
    """
    
    def __init__(self, draft_interval_ms: float = 2000):
        self.draft_interval_ms = draft_interval_ms
        self._last_draft_time: Optional[float] = None
        self._draft_count = 0
    
    def start_segment(self, start_time: Optional[float] = None):
        """Called when a new speech segment starts."""
        self._last_draft_time = None
    
    def should_trigger_draft(self, 
                           buffer_duration_ms: float,
                           vad_state: Optional[VADState] = None,
                           compute_queue_depth: int = 0) -> bool:
        """Simple time-based draft triggering."""
        now = time.time()
        
        if self._last_draft_time is None:
            # First draft
            self._last_draft_time = now
            self._draft_count += 1
            return True
        
        time_since_last = (now - self._last_draft_time) * 1000
        if time_since_last >= self.draft_interval_ms:
            self._last_draft_time = now
            self._draft_count += 1
            return True
        
        return False
    
    def get_stats(self) -> dict:
        """Get controller statistics."""
        return {
            'draft_count': self._draft_count,
            'interval_ms': self.draft_interval_ms,
        }
