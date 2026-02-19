"""
Phase 1.1 Test - Metrics and Adaptive Controller

Tests:
1. StreamingMetricsCollector (TTFT, Meaning Latency, etc.)
2. AdaptiveDraftController (skip logic)
3. Max segment duration config (4000ms)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.utils.streaming_metrics import (
    StreamingMetricsCollector, 
    SegmentMetrics,
    get_global_collector,
    reset_global_collector
)
from src.core.pipeline.adaptive_controller import (
    AdaptiveDraftController,
    VADState,
    SimpleDraftController
)


def test_streaming_metrics():
    """Test streaming metrics collection."""
    print("\n" + "=" * 60)
    print("TEST 1: Streaming Metrics Collector")
    print("=" * 60)
    
    collector = StreamingMetricsCollector()
    
    # Simulate a segment
    segment_uuid = "test-segment-1"
    speech_start = time.time()
    
    # Start segment
    collector.start_segment(segment_uuid, 1, speech_start)
    
    # Simulate speech end after 5s
    time.sleep(0.1)  # Shortened for test
    speech_end = time.time()
    collector.record_speech_end(segment_uuid, speech_end)
    
    # Simulate first draft after 2s
    time.sleep(0.05)
    first_draft_time = time.time()
    collector.record_first_draft(segment_uuid, "Hello world", first_draft_time)
    
    # Simulate ASR call
    collector.record_asr_call(segment_uuid)
    collector.record_asr_call(segment_uuid)  # Second call for draft
    
    # Simulate first translation
    time.sleep(0.05)
    first_meaning_time = time.time()
    collector.record_first_translation(segment_uuid, "Hola mundo", first_meaning_time)
    
    # Simulate final output
    time.sleep(0.05)
    final_output_time = time.time()
    collector.record_final_output(
        segment_uuid, 
        "Hello world today",
        "Hola mundo hoy",
        final_output_time
    )
    
    # Get metrics
    metrics = collector.get_segment_metrics(segment_uuid)
    
    print(f"\n  Segment Metrics:")
    print(f"    Speech start:     {metrics.speech_start_time:.3f}")
    print(f"    First draft:      {metrics.first_draft_time:.3f}")
    print(f"    First meaning:    {metrics.first_meaning_time:.3f}")
    print(f"    Final output:     {metrics.final_output_time:.3f}")
    
    ttft = metrics.calculate_ttft_ms()
    meaning_latency = metrics.calculate_meaning_latency_ms()
    lag = metrics.calculate_ear_to_voice_lag_ms()
    
    print(f"\n  Calculated Latencies:")
    print(f"    TTFT:             {ttft:.0f}ms")
    print(f"    Meaning Latency:  {meaning_latency:.0f}ms")
    print(f"    Ear-to-Voice:     {lag:.0f}ms")
    
    print(f"\n  ASR Calls:          {metrics.asr_calls}")
    
    # Get snapshot
    snapshot = collector.get_snapshot()
    print(f"\n  Snapshot:")
    print(f"    Avg TTFT:         {snapshot.avg_ttft_ms:.0f}ms")
    print(f"    Avg Meaning:      {snapshot.avg_meaning_latency_ms:.0f}ms")
    print(f"    Avg Ear-to-Voice: {snapshot.avg_ear_to_voice_lag_ms:.0f}ms")
    print(f"    ASR Calls/Seg:    {snapshot.avg_asr_calls_per_segment:.2f}")
    
    print("\n  ✅ Streaming metrics work!")
    return True


def test_adaptive_controller():
    """Test adaptive draft controller."""
    print("\n" + "=" * 60)
    print("TEST 2: Adaptive Draft Controller")
    print("=" * 60)
    
    controller = AdaptiveDraftController(
        draft_interval_ms=100,  # 100ms for testing
        pause_threshold_ms=50,   # 50ms for testing
        max_queue_depth=2
    )
    
    # Start a segment
    controller.start_segment()
    
    # Test 1: Should trigger first draft immediately
    vad = VADState(is_speaking=True, recent_pause_ms=0)
    result = controller.should_trigger_draft(200, vad, 0)
    print(f"\n  Test 1 - First draft: {result}")
    assert result == True, "First draft should always trigger"
    
    # Test 2: Too soon (time check)
    time.sleep(0.05)  # 50ms < 100ms interval
    result = controller.should_trigger_draft(400, vad, 0)
    print(f"  Test 2 - Too soon: {result} (skipped due to time)")
    assert result == False, "Should skip if too soon"
    
    # Test 3: Wait for interval
    time.sleep(0.1)  # Now 150ms > 100ms interval
    result = controller.should_trigger_draft(600, vad, 0)
    print(f"  Test 3 - After interval: {result}")
    assert result == True, "Should trigger after interval"
    
    # Test 4: Pause detected
    time.sleep(0.15)  # Wait for interval
    vad_pause = VADState(is_speaking=True, recent_pause_ms=100)  # 100ms > 50ms threshold
    result = controller.should_trigger_draft(1000, vad_pause, 0)
    print(f"  Test 4 - Pause detected: {result} (skipped due to pause)")
    assert result == False, "Should skip if pause detected"
    
    # Test 5: Queue depth
    time.sleep(0.15)
    vad_normal = VADState(is_speaking=True, recent_pause_ms=0)
    result = controller.should_trigger_draft(1200, vad_normal, 5)  # queue depth 5 > 2
    print(f"  Test 5 - Queue backed up: {result} (skipped due to queue)")
    assert result == False, "Should skip if queue backed up"
    
    # Test 6: Normal conditions
    time.sleep(0.15)
    result = controller.should_trigger_draft(1400, vad_normal, 1)
    print(f"  Test 6 - Normal conditions: {result}")
    assert result == True, "Should trigger under normal conditions"
    
    # Get stats
    stats = controller.get_stats()
    print(f"\n  Controller Stats:")
    print(f"    Triggered:        {stats['drafts_triggered']}")
    print(f"    Skipped (time):   {stats['drafts_skipped_time']}")
    print(f"    Skipped (pause):  {stats['drafts_skipped_pause']}")
    print(f"    Skipped (queue):  {stats['drafts_skipped_queue']}")
    print(f"    Trigger rate:     {stats['trigger_rate']:.1f}%")
    
    print("\n  ✅ Adaptive controller works!")
    return True


def test_simple_controller():
    """Test simple draft controller."""
    print("\n" + "=" * 60)
    print("TEST 3: Simple Draft Controller")
    print("=" * 60)
    
    controller = SimpleDraftController(draft_interval_ms=100)
    controller.start_segment()
    
    # First draft should trigger
    result = controller.should_trigger_draft(100)
    print(f"\n  First draft: {result}")
    assert result == True
    
    # Too soon
    time.sleep(0.05)
    result = controller.should_trigger_draft(200)
    print(f"  After 50ms: {result}")
    assert result == False
    
    # After interval
    time.sleep(0.1)
    result = controller.should_trigger_draft(300)
    print(f"  After 150ms: {result}")
    assert result == True
    
    stats = controller.get_stats()
    print(f"\n  Draft count: {stats['draft_count']}")
    
    print("\n  ✅ Simple controller works!")
    return True


def test_segment_duration_config():
    """Test that max segment duration is reduced to 4000ms."""
    print("\n" + "=" * 60)
    print("TEST 4: Segment Duration Config (4000ms)")
    print("=" * 60)
    
    from src.core.pipeline.orchestrator import PipelineConfig
    
    config = PipelineConfig()
    
    print(f"\n  Max segment duration: {config.max_segment_duration_ms}ms")
    
    assert config.max_segment_duration_ms == 4000, \
        f"Expected 4000ms, got {config.max_segment_duration_ms}ms"
    
    print("  ✅ Segment duration correctly set to 4000ms!")
    return True


def main():
    """Run all Phase 1.1 tests."""
    print("\n" + "=" * 70)
    print(" " * 20 + "PHASE 1.1 TESTS")
    print(" " * 15 + "(Metrics + Adaptive Config)")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("Streaming Metrics", test_streaming_metrics()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Streaming Metrics", False))
    
    try:
        results.append(("Adaptive Controller", test_adaptive_controller()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Adaptive Controller", False))
    
    try:
        results.append(("Simple Controller", test_simple_controller()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        results.append(("Simple Controller", False))
    
    try:
        results.append(("Segment Duration Config", test_segment_duration_config()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        results.append(("Segment Duration Config", False))
    
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
        print(" " * 10 + "🎉 Phase 1.1 Complete!")
        print(" " * 5 + "Ready for Phase 1.2: StreamingASR")
    else:
        print(" " * 15 + "❌ SOME TESTS FAILED!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
