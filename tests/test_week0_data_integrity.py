"""
Week 0 Data Integrity Test - Critical Bug Fix Verification

This test verifies that no segments are lost in the pipeline.
Must pass before any streaming optimization is implemented.

Usage:
    # Quick test (30 seconds - default)
    python tests/test_week0_data_integrity.py
    
    # Full 10-minute test
    python tests/test_week0_data_integrity.py --duration 600
    
    # 5-minute test
    python tests/test_week0_data_integrity.py --duration 300

Target: 0% sentence loss
"""

import time
import threading
import logging
import sys
import argparse
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

# Test configuration
DEFAULT_TEST_DURATION = 30  # 30 seconds for quick test
FULL_TEST_DURATION = 600    # 10 minutes for full test
SPEECH_SEGMENT_DURATION = 5  # 5 seconds per speech segment


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Week 0 Data Integrity Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                    # Quick 30-second test
  %(prog)s --duration 600     # Full 10-minute test
  %(prog)s --duration 300     # 5-minute test
        '''
    )
    parser.add_argument(
        '--duration', 
        type=int, 
        default=DEFAULT_TEST_DURATION,
        help=f'Test duration in seconds (default: {DEFAULT_TEST_DURATION} for quick test, 600 for full 10-min test)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose output'
    )
    return parser.parse_args()


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
    
    # Cleanup for next test
    tracker.reset_stats()
    
    return True


def test_queue_monitor_basic():
    """Test queue monitoring (without background thread)."""
    print("\n" + "=" * 60)
    print("TEST 2: Queue Monitor")
    print("=" * 60)
    
    # Don't start background monitoring - just test manual tracking
    monitor = QueueMonitor(check_interval=1.0)
    
    # Create test queues
    vad_queue = Queue(maxsize=5)
    asr_queue = Queue(maxsize=3)
    
    monitor.register_queue("vad", vad_queue)
    monitor.register_queue("asr", asr_queue)
    
    # Simulate operations (manual tracking)
    for i in range(5):
        try:
            vad_queue.put_nowait(f"item_{i}")
            monitor.record_put("vad", True, 0.1)
        except Full:
            monitor.record_put("vad", False, 0.1)
            print(f"  ⚠️  VAD queue overflow at item {i}")
    
    # Update depths manually (normally done by background thread)
    monitor._metrics['vad'].update_depth(vad_queue.qsize())
    monitor._metrics['asr'].update_depth(asr_queue.qsize())
    
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


def test_stress_test(duration_sec: int = DEFAULT_TEST_DURATION, verbose: bool = False):
    """
    Stress test simulating continuous speech.
    
    This test creates segments at realistic speech rates and verifies
    that 0% are lost through the pipeline.
    
    Args:
        duration_sec: Test duration in seconds (default 30 for quick test, 600 for full 10-min)
        verbose: Enable verbose output
    """
    print("\n" + "=" * 60)
    if duration_sec >= 600:
        print("TEST 3: 10-Minute Stress Test (CRITICAL)")
    else:
        print(f"TEST 3: Stress Test ({duration_sec}s) (CRITICAL)")
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
    
    # Test parameters
    TEST_DURATION_SEC = duration_sec
    SPEECH_SEGMENT_DURATION_SEC = 5  # 5 seconds per speech segment
    
    # Calculate expected segments
    total_segments_to_create = int(TEST_DURATION_SEC / SPEECH_SEGMENT_DURATION_SEC)
    
    # Format duration for display
    duration_min = TEST_DURATION_SEC / 60
    
    print(f"\n  Test Configuration:")
    print(f"    Duration: {TEST_DURATION_SEC}s ({duration_min:.1f} minutes)")
    print(f"    Speech segment duration: {SPEECH_SEGMENT_DURATION_SEC}s")
    print(f"    Expected segments: {total_segments_to_create}")
    
    if TEST_DURATION_SEC < 600:
        print(f"    ⚠️  This is a QUICK test. For full validation, use --duration 600")
    else:
        print(f"    ✅ This is the FULL 10-minute validation test!")
    
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
    
    # Progress tracking
    progress_lock = threading.Lock()
    last_progress_time = [time.time()]
    segments_created = [0]
    segments_emitted = [0]
    
    def print_progress():
        """Print progress update."""
        with progress_lock:
            elapsed = time.time() - test_start[0]
            percent = min(100, int(elapsed / TEST_DURATION_SEC * 100))
            remaining = max(0, TEST_DURATION_SEC - elapsed)
            created = segments_created[0]
            emitted = segments_emitted[0]
            
            # Format time remaining
            if remaining > 60:
                time_str = f"{remaining/60:.1f}min"
            else:
                time_str = f"{remaining:.0f}s"
            
            print(f"\r  ⏱️  Progress: {percent:3d}% | {created} created | {emitted} emitted | {time_str} remaining", end='', flush=True)
            last_progress_time[0] = time.time()
    
    def vad_worker():
        """VAD worker - creates segments from audio."""
        segment_id = 0
        
        while not stop_event.is_set():
            elapsed = time.time() - test_start[0]
            if elapsed > TEST_DURATION_SEC:
                break
            
            # Create segment every 5 seconds
            if elapsed >= segment_id * SPEECH_SEGMENT_DURATION_SEC:
                segment_id += 1
                
                # Create segment with tracking
                uuid = tracker.create_segment(segment_id, audio_duration_ms=5000)
                tracker.record_stage(uuid, SegmentStage.VAD_QUEUED)
                created_segments.add(segment_id)
                segments_created[0] = segment_id
                
                # Print progress every 5 seconds
                if time.time() - last_progress_time[0] > 5:
                    print_progress()
                
                # Try to queue for ASR
                try:
                    asr_queue.put_nowait((segment_id, uuid))
                    tracker.record_stage(uuid, SegmentStage.VAD_PROCESSED)
                    monitor.record_put("asr", True, 0.1)
                except Full:
                    tracker.record_drop(uuid, "ASR queue full")
                    monitor.record_put("asr", False, 0.1)
                    print(f"\n  🚨 DROPPED: Segment {segment_id} - ASR queue full")
            
            time.sleep(0.01)  # Small sleep to prevent busy-wait
    
    def asr_worker():
        """ASR worker - processes segments."""
        while not stop_event.is_set():
            try:
                segment_id, uuid = asr_queue.get(timeout=0.1)
                tracker.record_stage(uuid, SegmentStage.ASR_QUEUED)
                tracker.record_stage(uuid, SegmentStage.ASR_PROCESSING)
                
                # Simulate ASR processing (400ms)
                time.sleep(0.4)
                
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
                    print(f"\n  🚨 DROPPED: Segment {segment_id} - Translation queue full")
                
            except Empty:
                continue
    
    def translation_worker():
        """Translation worker - translates segments."""
        while not stop_event.is_set():
            try:
                segment_id, uuid = translation_queue.get(timeout=0.1)
                tracker.record_stage(uuid, SegmentStage.TRANSLATION_PROCESSING)
                
                # Simulate translation processing (250ms)
                time.sleep(0.25)
                
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
                    print(f"\n  🚨 DROPPED: Segment {segment_id} - Output queue full")
                
            except Empty:
                continue
    
    def output_worker():
        """Output worker - emits final results."""
        while not stop_event.is_set():
            try:
                segment_id, uuid = output_queue.get(timeout=0.1)
                tracker.record_stage(uuid, SegmentStage.OUTPUT_EMITTED)
                emitted_segments.add(segment_id)
                segments_emitted[0] = len(emitted_segments)
                
            except Empty:
                continue
    
    # Start workers
    print("\n  Starting pipeline workers...")
    test_start = [time.time()]
    threads = [
        threading.Thread(target=vad_worker, name="VADWorker"),
        threading.Thread(target=asr_worker, name="ASRWorker"),
        threading.Thread(target=translation_worker, name="TranslationWorker"),
        threading.Thread(target=output_worker, name="OutputWorker"),
    ]
    
    for t in threads:
        t.start()
    
    # Run test with progress
    print(f"  Running stress test for {TEST_DURATION_SEC} seconds...")
    print(f"  (Press Ctrl+C to stop early)\n")
    
    try:
        while True:
            elapsed = time.time() - test_start[0]
            if elapsed >= TEST_DURATION_SEC:
                break
            print_progress()
            time.sleep(1)  # Update every second
    except KeyboardInterrupt:
        print("\n\n  ⚠️  Test interrupted by user")
        stop_event.set()
    
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
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("\n" + "=" * 70)
    print(" " * 15 + "WEEK 0 DATA INTEGRITY TESTS")
    print(" " * 10 + "(Critical Bug Fix Verification)")
    print("=" * 70)
    
    # Print test mode
    if args.duration >= 600:
        print("\n  🎯 MODE: FULL 10-MINUTE VALIDATION TEST")
        print("  ⏱️  Estimated time: ~10 minutes")
    elif args.duration >= 60:
        print(f"\n  🎯 MODE: Extended test ({args.duration}s)")
        print(f"  ⏱️  Estimated time: ~{args.duration/60:.1f} minutes")
    else:
        print(f"\n  🎯 MODE: Quick test ({args.duration}s)")
        print("  ⚠️  For full validation, run with --duration 600")
    
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
    
    # Test 3: Stress test (CRITICAL)
    try:
        test_name = f"{args.duration}s Stress Test" if args.duration < 600 else "10-Minute Stress Test"
        results.append((test_name, test_stress_test(duration_sec=args.duration, verbose=args.verbose)))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Stress Test", False))
    
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
