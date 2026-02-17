#!/usr/bin/env python3
"""
Simple VAD Test - Verify Voice Activity Detection is working

Usage:
    python test_vad_simple.py [--device INDEX] [--threshold 0.5]

What to expect:
1. Start the script
2. Speak into your microphone
3. You should see "🎤 SPEECH DETECTED" messages when you speak
4. When you stop speaking, a segment will be captured and saved
5. Check the saved WAV files to verify audio was captured
"""

import sys
import time
import wave
import tempfile
import logging
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simple format
)
logger = logging.getLogger(__name__)


def test_vad(device_index: int = None, threshold: float = 0.5, duration: int = 30):
    """
    Test VAD by monitoring audio and saving detected speech segments.
    
    Args:
        device_index: Audio device index (None for default)
        threshold: VAD threshold (0.0-1.0)
        duration: Test duration in seconds
    """
    print("=" * 60)
    print("VAD SIMPLE TEST")
    print("=" * 60)
    print(f"\nSettings:")
    print(f"  Device: {device_index or 'Default'}")
    print(f"  Threshold: {threshold}")
    print(f"  Duration: {duration}s")
    print(f"\nInstructions:")
    print("  1. Speak into your microphone")
    print("  2. Watch for '🎤 SPEECH DETECTED' messages")
    print("  3. Stop speaking to end the segment")
    print("  4. Captured audio will be saved to /tmp/vad_test/")
    print("=" * 60)
    
    try:
        from src.audio import AudioManager, AudioConfig, AudioSource
        from src.audio.vad.silero_vad import SileroVADProcessor
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure you're in the correct directory and venv is activated")
        return 1
    
    # Setup
    output_dir = Path("/tmp/vad_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    audio_config = AudioConfig(
        sample_rate=16000,
        channels=1,
        chunk_duration_ms=30
    )
    
    vad = SileroVADProcessor(
        sample_rate=16000,
        threshold=threshold,
        min_speech_duration_ms=250,
        min_silence_duration_ms=100
    )
    
    audio_manager = AudioManager(audio_config)
    
    segments_captured = []
    speech_events = []
    start_time = time.time()
    
    def on_audio(chunk: np.ndarray):
        """Process audio chunk."""
        nonlocal segments_captured, speech_events
        
        # Calculate audio level (RMS)
        rms = np.sqrt(np.mean(chunk ** 2))
        level = min(1.0, rms / 500)
        
        # Show audio level bar
        bar_len = 30
        filled = int(bar_len * level)
        bar = '█' * filled + '░' * (bar_len - filled)
        
        # Process through VAD
        segment = vad.process_chunk(chunk)
        
        # Get VAD state
        state = vad._state.value.upper()
        state_emoji = "🎤" if state == "SPEECH" else "🔇"
        
        # Print status
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        print(f"\r[{bar}] {level:.2f} {state_emoji} {state} | Time: {remaining:.1f}s | Segments: {len(segments_captured)}", 
              end='', flush=True)
        
        if segment:
            # Speech segment completed
            segments_captured.append(segment)
            speech_events.append({
                'time': elapsed,
                'duration': segment.duration,
                'confidence': segment.confidence
            })
            print(f"\n✅ Segment #{len(segments_captured)}: {segment.duration:.2f}s (conf: {segment.confidence:.2f})")
            
            # Save the segment
            filename = output_dir / f"segment_{len(segments_captured):03d}_{datetime.now():%H%M%S}.wav"
            with wave.open(str(filename), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)
                wav_file.writeframes(segment.audio_data.tobytes())
            print(f"   Saved: {filename}")
    
    # Start capture
    print("\n🎙️  Starting audio capture...\n")
    
    try:
        success = audio_manager.start_capture(
            AudioSource.MICROPHONE,
            on_audio,
            device_index=device_index
        )
        
        if not success:
            print("\n❌ Failed to start audio capture")
            return 1
        
        # Run for specified duration
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        
        # Stop capture
        audio_manager.stop_capture()
        
        # Finalize any pending segment
        final_segment = vad.force_finalize()
        if final_segment:
            segments_captured.append(final_segment)
            print(f"\n✅ Final segment: {final_segment.duration:.2f}s")
        
    except Exception as e:
        print(f"\n\n❌ Error during capture: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"\nTotal segments captured: {len(segments_captured)}")
    print(f"Total speech events: {len(speech_events)}")
    
    if segments_captured:
        total_duration = sum(s.duration for s in segments_captured)
        avg_confidence = sum(s.confidence for s in segments_captured) / len(segments_captured)
        print(f"Total speech duration: {total_duration:.2f}s")
        print(f"Average confidence: {avg_confidence:.2f}")
        print(f"\nSaved files location: {output_dir}")
        print("\n✅ VAD is working! Check the saved WAV files to verify audio quality.")
    else:
        print("\n⚠️  No speech segments captured.")
        print("\nTroubleshooting:")
        print("  1. Check your microphone is connected and selected")
        print("  2. Try speaking louder or closer to the mic")
        print(f"  3. Lower the threshold (current: {threshold}) - try 0.3 or 0.4")
        print("  4. Check system microphone permissions")
    
    print("=" * 60)
    return 0


def list_audio_devices():
    """List available audio input devices."""
    import sounddevice as sd
    
    print("\nAvailable Audio Input Devices:")
    print("-" * 60)
    
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            default_mark = " (DEFAULT)" if i == sd.default.device[0] else ""
            print(f"  {i}: {dev['name']}{default_mark}")
            print(f"     Channels: {dev['max_input_channels']}, Sample Rate: {int(dev['default_samplerate'])}Hz")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Simple VAD Test - Verify voice detection is working"
    )
    parser.add_argument(
        "--device", "-d",
        type=int,
        default=None,
        help="Audio device index (use --list to see available devices)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.5,
        help="VAD threshold (0.0-1.0, lower = more sensitive, default: 0.5)"
    )
    parser.add_argument(
        "--duration", "-T",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available audio devices and exit"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_audio_devices()
        return 0
    
    return test_vad(args.device, args.threshold, args.duration)


if __name__ == "__main__":
    sys.exit(main())
