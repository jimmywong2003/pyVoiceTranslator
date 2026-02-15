"""
Example usage of the Audio Processing Module

This script demonstrates how to use the audio processing subsystem
for real-time voice translation.
"""

import logging
import time
import sys
import os

# Add the audio module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_module import (
    AudioManager,
    AudioConfig,
    AudioSource,
    SileroVADProcessor,
    SegmentationEngine,
    AudioStreamingPipeline,
    AudioDetectionTester,
    VideoAudioExtractor
)
from audio_module.pipeline.streaming import ResampleProcessor, NormalizeProcessor
from audio_module.benchmarking import AudioBenchmark

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_test_audio_sources():
    """Example 1: Test audio input sources"""
    print("\n" + "=" * 60)
    print("Example 1: Testing Audio Sources")
    print("=" * 60 + "\n")
    
    tester = AudioDetectionTester()
    results = tester.run_all_tests()
    tester.print_results(results)
    
    return results


def example_2_microphone_capture_with_vad():
    """Example 2: Capture from microphone with VAD"""
    print("\n" + "=" * 60)
    print("Example 2: Microphone Capture with VAD")
    print("=" * 60 + "\n")
    
    # Configuration
    config = AudioConfig(sample_rate=16000, chunk_duration_ms=30)
    
    # Initialize components
    manager = AudioManager(config)
    vad = SileroVADProcessor(
        sample_rate=16000,
        threshold=0.5,
        min_speech_duration_ms=250
    )
    segmenter = SegmentationEngine()
    
    # Track detected segments
    segments_detected = []
    
    def on_audio(chunk):
        """Process audio chunk"""
        # Process through VAD
        segment = vad.process_chunk(chunk)
        
        if segment:
            segments_detected.append(segment)
            print(f"\n[SPEECH DETECTED]")
            print(f"  Duration: {segment.duration:.2f}s")
            print(f"  Confidence: {segment.confidence:.2f}")
            print(f"  Samples: {len(segment.audio_data)}")
    
    # Start capture
    print("Starting microphone capture (speak for 10 seconds)...")
    success = manager.start_capture(
        source=AudioSource.MICROPHONE,
        callback=on_audio
    )
    
    if not success:
        print("Failed to start capture!")
        return
    
    # Capture for 10 seconds
    time.sleep(10)
    
    # Stop
    manager.stop_capture()
    
    # Force finalize any pending segment
    final_segment = vad.force_finalize()
    if final_segment:
        segments_detected.append(final_segment)
    
    print(f"\nTotal segments detected: {len(segments_detected)}")
    print(f"Total speech time: {sum(s.duration for s in segments_detected):.2f}s")


def example_3_system_audio_capture():
    """Example 3: Capture system audio (loopback)"""
    print("\n" + "=" * 60)
    print("Example 3: System Audio Capture (Loopback)")
    print("=" * 60 + "\n")
    
    config = AudioConfig(sample_rate=16000, chunk_duration_ms=30)
    manager = AudioManager(config)
    vad = SileroVADProcessor(sample_rate=16000)
    
    chunk_count = [0]
    
    def on_audio(chunk):
        chunk_count[0] += 1
        segment = vad.process_chunk(chunk)
        if segment:
            print(f"Speech detected: {segment.duration:.2f}s")
    
    print("Starting system audio capture (play audio for 10 seconds)...")
    success = manager.start_capture(
        source=AudioSource.SYSTEM_AUDIO,
        callback=on_audio
    )
    
    if not success:
        print("Failed to start system audio capture!")
        print("Make sure loopback device is configured:")
        print("  Windows: Enable Stereo Mix or install VB-Cable")
        print("  macOS: Install BlackHole (brew install blackhole-2ch)")
        return
    
    time.sleep(10)
    manager.stop_capture()
    
    print(f"Total chunks processed: {chunk_count[0]}")


def example_4_video_audio_extraction():
    """Example 4: Extract audio from video file"""
    print("\n" + "=" * 60)
    print("Example 4: Video Audio Extraction")
    print("=" * 60 + "\n")
    
    extractor = VideoAudioExtractor(sample_rate=16000)
    
    # For demo, we'll create a test scenario
    print("VideoAudioExtractor initialized successfully")
    print("\nTo extract audio from a video file:")
    print("  extractor = VideoAudioExtractor(sample_rate=16000)")
    print("  audio = extractor.extract_to_numpy('video.mp4')")
    print("  print(f'Extracted {len(audio)} samples')")
    
    # Show video info example
    print("\nTo get video information:")
    print("  info = extractor.get_video_info('video.mp4')")
    print("  print(info)")
    
    # Streaming example
    print("\nTo stream audio from video:")
    print("  for chunk in extractor.extract_streaming('video.mp4', chunk_size=480):")
    print("      process_chunk(chunk)")


def example_5_pipeline_with_processors():
    """Example 5: Audio pipeline with multiple processors"""
    print("\n" + "=" * 60)
    print("Example 5: Audio Pipeline with Processors")
    print("=" * 60 + "\n")
    
    from audio_module.pipeline.streaming import (
        PipelineConfig,
        AudioStreamingPipeline,
        ResampleProcessor,
        NormalizeProcessor,
        GainProcessor
    )
    
    # Create pipeline
    config = PipelineConfig(
        processing_threads=2,
        enable_backpressure=True
    )
    pipeline = AudioStreamingPipeline(config)
    
    # Add processors
    pipeline.add_processor(NormalizeProcessor(target_peak=0.9))
    pipeline.add_processor(GainProcessor(gain_db=3.0))
    
    # Start pipeline
    pipeline.start()
    
    # Generate test audio
    import numpy as np
    test_chunks = [
        (np.random.randn(480) * 1000).astype(np.int16)
        for _ in range(100)
    ]
    
    print("Feeding 100 test chunks through pipeline...")
    
    # Feed audio
    for chunk in test_chunks:
        pipeline.feed(chunk)
    
    # Wait and get output
    time.sleep(1)
    
    # Get metrics
    metrics = pipeline.get_metrics()
    print(f"\nPipeline Metrics:")
    print(f"  Chunks processed: {metrics.chunks_processed}")
    print(f"  Avg processing time: {metrics.avg_processing_time_ms:.3f}ms")
    print(f"  Throughput: {metrics.throughput_chunks_per_sec:.1f} chunks/sec")
    
    # Stop
    pipeline.stop()


def example_6_benchmarking():
    """Example 6: Performance benchmarking"""
    print("\n" + "=" * 60)
    print("Example 6: Performance Benchmarking")
    print("=" * 60 + "\n")
    
    from audio_module.pipeline.streaming import AudioStreamingPipeline, PipelineConfig
    
    # Create components
    vad = SileroVADProcessor(sample_rate=16000)
    
    config = PipelineConfig(processing_threads=2)
    pipeline = AudioStreamingPipeline(config)
    pipeline.add_processor_func(lambda x: x, "passthrough")
    
    # Create benchmark
    benchmark = AudioBenchmark(sample_rate=16000)
    
    # Run benchmarks
    print("Running VAD benchmark...")
    vad_result = benchmark.benchmark_vad(vad, num_chunks=500)
    
    print("\nRunning pipeline benchmark...")
    pipeline_result = benchmark.benchmark_pipeline(pipeline, num_chunks=500)
    
    # Print results
    print("\n" + "-" * 60)
    print("Benchmark Results:")
    print("-" * 60)
    print(f"\nVAD:")
    print(f"  Avg time: {vad_result.avg_time_ms:.3f}ms")
    print(f"  Throughput: {vad_result.throughput_chunks_per_sec:.1f} chunks/sec")
    print(f"  CPU: {vad_result.cpu_percent:.1f}%")
    
    print(f"\nPipeline:")
    print(f"  Avg time: {pipeline_result.avg_time_ms:.3f}ms")
    print(f"  Throughput: {pipeline_result.throughput_chunks_per_sec:.1f} chunks/sec")
    print(f"  CPU: {pipeline_result.cpu_percent:.1f}%")


def example_7_visualization_data():
    """Example 7: Generate visualization data"""
    print("\n" + "=" * 60)
    print("Example 7: Visualization Data Generation")
    print("=" * 60 + "\n")
    
    from audio_module.segmentation import SegmentationConfig
    
    # Create segmentation engine with visualization enabled
    config = SegmentationConfig(
        generate_waveform=True,
        waveform_samples=50
    )
    segmenter = SegmentationEngine(config)
    
    # Simulate some segments
    import numpy as np
    
    # Simulate VAD results
    timestamps = np.arange(0, 10, 0.03)  # 10 seconds at 30ms chunks
    
    for i, ts in enumerate(timestamps):
        # Simulate speech from 2-4s and 6-8s
        is_speech = (2 <= ts <= 4) or (6 <= ts <= 8)
        
        # Generate audio chunk
        if is_speech:
            t = np.linspace(0, 0.03, 480)
            audio = (0.3 * np.sin(2 * np.pi * 200 * t) * 32767).astype(np.int16)
        else:
            audio = (np.random.randn(480) * 50).astype(np.int16)
        
        segments = segmenter.process_vad_result(
            is_speech=is_speech,
            audio_chunk=audio,
            timestamp=ts,
            confidence=0.8 if is_speech else 0.2
        )
        
        for seg in segments:
            print(f"Segment: {seg.duration:.2f}s, peak: {seg.peak_amplitude:.3f}")
    
    # Get visualization data
    viz_data = segmenter.get_visualization_data()
    
    print(f"\nVisualization Data:")
    print(f"  Total segments: {viz_data['segment_count']}")
    print(f"  Total speech duration: {viz_data['total_speech_duration']:.2f}s")
    print(f"  Average segment duration: {viz_data['average_segment_duration']:.2f}s")
    
    # Print first segment details
    if viz_data['segments']:
        first = viz_data['segments'][0]
        print(f"\nFirst segment:")
        print(f"  Start: {first['start']:.2f}s")
        print(f"  End: {first['end']:.2f}s")
        print(f"  Duration: {first['duration']:.2f}s")
        print(f"  Waveform samples: {len(first['waveform']) if first['waveform'] else 0}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Audio Processing Module - Examples")
    print("=" * 60)
    
    examples = [
        ("Test Audio Sources", example_1_test_audio_sources),
        ("Microphone Capture with VAD", example_2_microphone_capture_with_vad),
        ("System Audio Capture", example_3_system_audio_capture),
        ("Video Audio Extraction", example_4_video_audio_extraction),
        ("Pipeline with Processors", example_5_pipeline_with_processors),
        ("Performance Benchmarking", example_6_benchmarking),
        ("Visualization Data", example_7_visualization_data),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nSelect examples to run (comma-separated, or 'all'):")
    print("  Example: 1,3,5 or 'all'")
    
    try:
        choice = input("\nYour choice: ").strip().lower()
    except KeyboardInterrupt:
        print("\nExiting...")
        return
    
    if choice == 'all':
        selected = range(len(examples))
    else:
        try:
            selected = [int(x) - 1 for x in choice.split(',')]
        except ValueError:
            print("Invalid input. Running example 1 only.")
            selected = [0]
    
    for idx in selected:
        if 0 <= idx < len(examples):
            name, func = examples[idx]
            try:
                func()
            except Exception as e:
                print(f"\nError in example '{name}': {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"Invalid example number: {idx + 1}")
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
