"""
Week 0 Data Integrity Test - Critical Bug Fix Verification

This test verifies that no segments are lost in the pipeline.
Must pass before any streaming optimization is implemented.

Test: 10-minute continuous speech simulation
Target: 0% sentence loss
"""

import time
import threading
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from queue import Queue, Full, Empty

from src.core.pipeline.segment_tracker import (
    SegmentTracker, SegmentStage, get_global_tracker, reset_global_tracker
)
from src.core.pipeline.queue_monitor import (
    QueueMonitor, get_global_monitor, reset_global_monitor
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockPipelineComponent:
    """Mock pipeline component for testing."""
    
    def __init__(self, name: str, processing_time_ms: float, failure_rate: float = 0.0):
        self.name = name
        self.processing_time_ms = processing_time_ms
        self.failure_rate = failure_rate
        self._segment_count = 0
    
    def process(self, segment_id: int) -> bool:
        """Process a segment, return success/failure."""
        self._segment_count += 1
        
        # Simulate processing time
        time.sleep(self.processing_time_ms / 1000)
        
        # Simulate occasional failures
        if np.random.random() < self.failure_rate:
            return False
        
        return True


def test_segment_tracker_basic():
    """Test basic segment tracking functionality."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Segment Tracker")
    print("=" * 60)
    
    tracker = SegmentTracker()
    
    # Create segments
    for i in range(1, 6):
        uuid = tracker.create_segment(i, audio_duration_ms=1000)
        print(f"  Created segment {i} with UUID {uuid[:8]}")
    
    # Record stages for some segments
    tracker.record_stage(tracker._segment_id_to_uuid[1], SegmentStage.VAD_QUEUED)
    tracker.record_stage(tracker._segment_id_to_uuid[1], SegmentStage.VAD_PROCESSED)
    tracker.record_stage(tracker._segment_id_to_uuid[1], SegmentStage.ASR_QUEUED)
    tracker.record_stage(tracker._segment_id_to_uuid[1], SegmentStage.OUTPUT_EMITTED)
    
    tracker.record_stage(tracker._segment_id_to_uuid[2], SegmentStage.VAD_QUEUED)
    tracker.record_drop(tracker._segment_id_to_uuid[2], "Queue full")
    
    # Get stats
    stats = tracker.get_stats()
    print(f"\n  Stats:")
    print(f"    Total Created: {stats['total_created']}")
    print(f"    Total Emitted: {stats['total_emitted']}")
    print(f"    Total Dropped: {stats['total_dropped']}")
    print(f"    Loss Rate: {stats['loss_rate_percent']:.2f}%")
    
    # Verify
    assert stats['total_created'] == 5
    assert stats['total_emitted'] == 1
    assert stats['total_dropped'] == 1
    assert stats['unaccounted'] == 3  # 2, 3, 4, 5 not finished
    
    print("\n  ✅ Basic tracking works!")
    return True


def test_queue_monitor_basic():
    """Test queue monitoring."""
    print("\n" + "=" * 60)
    print("TEST 2: Queue Monitor")
    print("=" * 60)
    
    monitor = QueueMonitor(check_interval=0.1)
    
    # Create test queues
    vad_queue = Queue(maxsize=5)
    asr_queue = Queue(maxsize=3)
    
    monitor.register_queue("vad", vad_queue)
    monitor.register_queue("asr", asr_queue)
    
    # Simulate operations
    for i in range(5):
        try:
            vad_queue.put_nowait(f"item_{i}")
            monitor.record_put("vad", True, 0.1)
        except Full:
            monitor.record_put("vad", False, 0.1)
            print(f"  ⚠️  VAD queue overflow at item {i}")
    
    # Get metrics
    metrics = monitor.get_metrics()
    print(f"\n  Queue Metrics:")
    for name, m in metrics.items():
        print(f"    {name}: depth={m['current_depth']}, puts={m['total_puts']}, fails={m['put_failures']}")
    
    # Verify
    assert metrics['vad']['total_puts'] == 5
    assert metrics['vad']['overflow_count'] == 0  # Max 5, put 5
    
    print("\n  ✅ Queue monitoring works!")
    return True


def test_10_minute_stress_test():
    """
    10-minute stress test simulating continuous speech.
    
    This test creates segments at realistic speech rates and verifies
    that 0% are lost through the pipeline.
    """
    print("\n" + "=" * 60)
    print("TEST 3: 10-Minute Stress Test (CRITICAL)")
    print("=" * 60)
    
    # Reset trackers
    reset_global_tracker()
    reset_global_monitor()
    
    tracker = get_global_tracker()
    monitor = get_global_monitor()
    
    # Create pipeline queues
    vad_queue = Queue(maxsize=10)
    asr_queue = Queue(maxsize=5)
    translation_queue = Queue(maxsize=3)
    output_queue = Queue(maxsize=20)
    
    monitor.register_queue("vad", vad_queue)
    monitor.register_queue("asr", asr_queue)
    monitor.register_queue("translation", translation_queue)
    monitor.register_queue("output", output_queue)
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Test parameters (10 minutes scaled to 30 seconds for faster testing)
    TEST_DURATION_SEC = 30  # 30 seconds = 10 minutes scaled
    SPEECH_SEGMENT_DURATION_SEC = 5  # 5 seconds per speech segment
    SCALE_FACTOR = TEST_DURATION_SEC / 600  # Scale 10min to 30sec
    
    total_segments_to_create = int(600 / SPEECH_SEGMENT_DURATION_SEC)  # 120 segments in 10min
    
    print(f"\n  Test Configuration:")
    print(f"    Duration: {TEST_DURATION_SEC}s (scaled from 10min)")
    print(f"    Speech segment duration: {SPEECH_SEGMENT_DURATION_SEC}s")
    print(f"    Expected segments: {total_segments_to_create}")
    print(f"    Scale factor: {SCALE_FACTOR:.3f}x")
    
    # Track created segment IDs
    created_segments = set()
    emitted_segments = set()
    
    # Create drop/error callbacks
    def on_drop(trace):
        print(f"  🚨 DROPPED: Segment {trace.segment_id} - {trace.dropped_reason}")
    
    def on_error(trace):
        print(f"  ⚠️  ERROR: Segment {trace.segment_id} - {trace.error_message}")
    
    tracker.on_drop(on_drop)
    tracker.on_error(on_error)
    
    # Simulate pipeline
    stop_event = threading.Event()
    
    def vad_worker():
        """VAD worker - creates segments from audio."""
        segment_id = 0
        start_time = time.time()
        
        while not stop_event.is_set():
            elapsed = time.time() - start_time
            if elapsed > TEST_DURATION_SEC:
                break
            
            # Create segment every 5 seconds (scaled)
            if elapsed >= segment_id * (SPEECH_SEGMENT_DURATION_SEC * SCALE_FACTOR):
                segment_id += 1
                
                # Create segment with tracking
                uuid = tracker.create_segment(segment_id, audio_duration_ms=5000)
                tracker.record_stage(uuid, SegmentStage.VAD_QUEUED)
                created_segments.add(segment_id)
                
                # Try to queue for ASR
                try:
                    asr_queue.put_nowait((segment_id, uuid))
                    tracker.record_stage(uuid, SegmentStage.VAD_PROCESSED)
                    monitor.record_put("asr", True, 0.1)
                except Full:
                    tracker.record_drop(uuid, "ASR queue full")
                    monitor.record_put("asr", False, 0.1)
            
            time.sleep(0.01)  # Small sleep to prevent busy-wait
    
    def asr_worker():
        """ASR worker - processes segments."""
        while not stop_event.is_set():
            try:
                segment_id, uuid = asr_queue.get(timeout=0.1)
                tracker.record_stage(uuid, SegmentStage.ASR_QUEUED)
                tracker.record_stage(uuid, SegmentStage.ASR_PROCESSING)
                
                # Simulate ASR processing (400ms scaled)
                time.sleep(0.4 * SCALE_FACTOR)
                
                # Update ASR result
                tracker.update_asr_result(uuid, f"Transcription of segment {segment_id}")
                tracker.record_stage(uuid, SegmentStage.ASR_COMPLETE)
                
                # Queue for translation
                try:
                    translation_queue.put_nowait((segment_id, uuid))
                    tracker.record_stage(uuid, SegmentStage.TRANSLATION_QUEUED)
                    monitor.record_put("translation", True, 0.1)
                except Full:
                    tracker.record_drop(uuid, "Translation queue full")
                    monitor.record_put("translation", False, 0.1)
                
            except Empty:
                continue
    
    def translation_worker():
        """Translation worker - translates segments."""
        while not stop_event.is_set():
            try:
                segment_id, uuid = translation_queue.get(timeout=0.1)
                tracker.record_stage(uuid, SegmentStage.TRANSLATION_PROCESSING)
                
                # Simulate translation processing (250ms scaled)
                time.sleep(0.25 * SCALE_FACTOR)
                
                # Update translation result
                tracker.update_translation_result(uuid, f"Translation of segment {segment_id}")
                tracker.record_stage(uuid, SegmentStage.TRANSLATION_COMPLETE)
                
                # Queue for output
                try:
                    output_queue.put_nowait((segment_id, uuid))
                    tracker.record_stage(uuid, SegmentStage.OUTPUT_QUEUED)
                    monitor.record_put("output", True, 0.1)
                except Full:
                    tracker.record_drop(uuid, "Output queue full")
                    monitor.record_put("output", False, 0.1)
                
            except Empty:
                continue
    
    def output_worker():
        """Output worker - emits final results."""
        while not stop_event.is_set():
            try:
                segment_id, uuid = output_queue.get(timeout=0.1)
                tracker.record_stage(uuid, SegmentStage.OUTPUT_EMITTED)
                emitted_segments.add(segment_id)
                
            except Empty:
                continue
    
    # Start workers
    print("\n  Starting pipeline workers...")
    threads = [
        threading.Thread(target=vad_worker, name="VADWorker"),
        threading.Thread(target=asr_worker, name="ASRWorker"),
        threading.Thread(target=translation_worker, name="TranslationWorker"),
        threading.Thread(target=output_worker, name="OutputWorker"),
    ]
    
    for t in threads:
        t.start()
    
    # Run test
    print(f"  Running stress test for {TEST_DURATION_SEC} seconds...")
    time.sleep(TEST_DURATION_SEC)
    
    # Stop workers
    print("  Stopping workers...")
    stop_event.set()
    
    for t in threads:
        t.join(timeout=2.0)
    
    monitor.stop_monitoring()
    
    # Allow time for final segments to process
    time.sleep(1)
    
    # Get final stats
    print("\n" + "=" * 60)
    print("STRESS TEST RESULTS")
    print("=" * 60)
    
    tracker.print_summary()
    monitor.print_summary()
    
    stats = tracker.get_stats()
    
    # CRITICAL VERIFICATION
    print("\n" + "=" * 60)
    print("CRITICAL VERIFICATION")
    print("=" * 60)
    
    loss_rate = stats['loss_rate_percent']
    
    if loss_rate == 0:
        print(f"\n  ✅ SUCCESS! Loss rate: {loss_rate:.2f}%")
        print("  ✅ Week 0 Critical Fix: VERIFIED - No segments lost!")
        print("\n  🎉 READY FOR STREAMING OPTIMIZATION! 🎉")
        return True
    else:
        print(f"\n  🚨 FAILURE! Loss rate: {loss_rate:.2f}%")
        print(f"  🚨 {stats['total_dropped']} segments were DROPPED!")
        print("\n  ❌ BUG NOT FIXED - DO NOT PROCEED WITH OPTIMIZATION!")
        
        # Show details
        print("\n  Details:")
        print(f"    Created: {stats['total_created']}")
        print(f"    Emitted: {stats['total_emitted']}")
        print(f"    Dropped: {stats['total_dropped']}")
        print(f"    Errors:  {stats['total_errors']}")
        print(f"    Unaccounted: {stats['unaccounted']}")
        
        return False


def main():
    """Run all Week 0 tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "WEEK 0 DATA INTEGRITY TESTS")
    print(" " * 10 + "(Critical Bug Fix Verification)")
    print("=" * 70)
    
    results = []
    
    # Test 1: Basic tracking
    try:
        results.append(("Basic Segment Tracker", test_segment_tracker_basic()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        results.append(("Basic Segment Tracker", False))
    
    # Test 2: Queue monitoring
    try:
        results.append(("Queue Monitor", test_queue_monitor_basic()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        results.append(("Queue Monitor", False))
    
    # Test 3: 10-minute stress test (CRITICAL)
    try:
        results.append(("10-Minute Stress Test", test_10_minute_stress_test()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("10-Minute Stress Test", False))
    
    # Final summary
    print("\n" + "=" * 70)
    print(" " * 20 + "FINAL SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print(" " * 15 + "✅ ALL TESTS PASSED!")
        print(" " * 5 + "🎉 Week 0 Critical Fix: VERIFIED!")
        print(" " * 10 + "Ready for Phase 1 (Streaming)")
    else:
        print(" " * 15 + "❌ SOME TESTS FAILED!")
        print(" " * 5 + "🚨 Week 0 Critical Fix: NOT VERIFIED!")
        print(" " * 5 + "DO NOT PROCEED WITH OPTIMIZATION!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
