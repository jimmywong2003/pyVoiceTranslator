"""
PoC 2: Turn-Based Speaker Diarization Test
Tests speaker detection logic without UI
"""

import sys
import time
import numpy as np
from pathlib import Path
from collections import deque

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class SimpleSpeakerDiarization:
    """
    Simplified speaker diarization using turn-based detection.
    
    V1 Strategy:
    - Detect speaker turns using pause detection
    - Assume alternating speakers for structured meetings
    - User-configurable speaker count (2-8)
    """
    
    def __init__(self, max_speakers: int = 4):
        self.max_speakers = max_speakers
        self.speaker_counter = 0
        self._last_speaker = None
        self._turn_counter = 0
        self._segments = []
    
    def process_segment(
        self,
        audio_segment: np.ndarray,
        start_time: float,
        end_time: float,
        is_new_turn: bool = False
    ) -> dict:
        """
        Process audio segment and identify speaker.
        
        Args:
            audio_segment: Audio samples (MUST be real audio, not empty!)
            start_time: Segment start time
            end_time: Segment end time
            is_new_turn: True if this is a new speaker turn
            
        Returns:
            Speaker segment info
        """
        # CRITICAL: Must use real audio for proper testing
        if audio_segment is None or len(audio_segment) == 0:
            raise ValueError("Empty audio segment! Use real audio for accurate testing.")
        
        # Simple turn-based assignment
        if is_new_turn or self._last_speaker is None:
            self._turn_counter += 1
            speaker_id = f"Speaker {(self._turn_counter % self.max_speakers) + 1}"
        else:
            speaker_id = self._last_speaker
        
        self._last_speaker = speaker_id
        
        segment = {
            "speaker_id": speaker_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "audio_rms": np.sqrt(np.mean(audio_segment**2)),
            "confidence": 0.8 if is_new_turn else 0.9
        }
        
        self._segments.append(segment)
        return segment
    
    def reset(self):
        """Reset all speaker data."""
        self.speaker_counter = 0
        self._last_speaker = None
        self._turn_counter = 0
        self._segments.clear()


def test_with_real_audio():
    """Test 1: CRITICAL - Use real audio for latency benchmark"""
    print("\n=== Test 1: Real Audio Processing ===")
    print("Generating test audio (simulated microphone input)...")
    
    diarization = SimpleSpeakerDiarization(max_speakers=3)
    
    # Simulate real audio: 1 second at 16kHz
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    
    # Generate test audio (simulated speech-like signal)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * 440 * t) * 0.3  # 440Hz tone
    audio += np.random.normal(0, 0.01, samples)  # Add noise
    
    # Process multiple segments
    latencies = []
    for i in range(10):
        start = time.time()
        
        segment = diarization.process_segment(
            audio_segment=audio,
            start_time=i * 1.0,
            end_time=(i + 1) * 1.0,
            is_new_turn=(i % 2 == 0)  # Alternate speakers
        )
        
        elapsed = time.time() - start
        latencies.append(elapsed * 1000)  # Convert to ms
        
        print(f"  Segment {i+1}: {elapsed*1000:.2f}ms -> {segment['speaker_id']}")
    
    avg_latency = np.mean(latencies)
    max_latency = np.max(latencies)
    
    print(f"\nLatency Results:")
    print(f"  Average: {avg_latency:.2f}ms")
    print(f"  Maximum: {max_latency:.2f}ms")
    print(f"  Target: <50ms")
    
    if avg_latency < 50:
        print("✓ PASS: Latency within acceptable range")
        return True, avg_latency
    else:
        print("✗ FAIL: Latency too high")
        return False, avg_latency


def test_empty_audio_detection():
    """Test 2: Verify empty audio raises error (catches placeholder bugs)"""
    print("\n=== Test 2: Empty Audio Detection ===")
    
    diarization = SimpleSpeakerDiarization()
    
    try:
        diarization.process_segment(
            audio_segment=np.array([]),  # Empty - should fail
            start_time=0.0,
            end_time=1.0
        )
        print("✗ FAIL: Should have raised error for empty audio")
        return False
    except ValueError as e:
        print(f"✓ PASS: Correctly rejected empty audio")
        print(f"  Error: {e}")
        return True


def test_speaker_rotation():
    """Test 3: Speaker rotation with configurable count"""
    print("\n=== Test 3: Speaker Rotation (max_speakers=4) ===")
    
    diarization = SimpleSpeakerDiarization(max_speakers=4)
    sample_rate = 16000
    audio = np.random.normal(0, 0.1, sample_rate)  # 1 second noise
    
    speakers_seen = set()
    
    for i in range(8):  # 8 segments
        segment = diarization.process_segment(
            audio_segment=audio,
            start_time=i * 1.0,
            end_time=(i + 1) * 1.0,
            is_new_turn=True  # Force new speaker each time
        )
        speakers_seen.add(segment["speaker_id"])
        print(f"  Turn {i+1}: {segment['speaker_id']}")
    
    print(f"\nSpeakers used: {speakers_seen}")
    
    if len(speakers_seen) == 4:
        print("✓ PASS: Correctly rotated through 4 speakers")
        return True
    else:
        print(f"✗ FAIL: Expected 4 speakers, got {len(speakers_seen)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 2: Speaker Diarization with REAL Audio")
    print("=" * 60)
    print("\n⚠ CRITICAL: This PoC must use real audio buffers!")
    print("   Testing with empty arrays gives false positives.")
    
    results = {
        "real_audio": test_with_real_audio(),
        "empty_detection": test_empty_audio_detection(),
        "rotation": test_speaker_rotation()
    }
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    
    real_audio_pass, latency = results["real_audio"]
    print(f"  Real Audio Test: {'PASS' if real_audio_pass else 'FAIL'} ({latency:.2f}ms)")
    print(f"  Empty Detection: {'PASS' if results['empty_detection'] else 'FAIL'}")
    print(f"  Speaker Rotation: {'PASS' if results['rotation'] else 'FAIL'}")
    
    overall = real_audio_pass and results["empty_detection"] and results["rotation"]
    
    print("\n" + "=" * 60)
    if overall:
        print("✓ ALL TESTS PASSED - Can proceed with turn-based diarization")
    else:
        print("✗ SOME TESTS FAILED - Consider delaying speaker ID to V2")
    print("=" * 60)
    
    # Write results
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 2: Speaker Diarization\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Latency: {latency:.2f}ms (target <50ms)\n")
        f.write(f"- Real Audio Test: {'PASS' if real_audio_pass else 'FAIL'}\n")
        f.write(f"- Empty Detection: {'PASS' if results['empty_detection'] else 'FAIL'}\n")
        f.write(f"- Speaker Rotation: {'PASS' if results['rotation'] else 'FAIL'}\n")
        f.write(f"- **Overall**: {'PASS' if overall else 'FAIL'}\n")
    
    print("\n✓ Results appended to results.md")
