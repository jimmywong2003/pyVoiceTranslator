"""
Improved Silero VAD with enhanced buffering and sentence segmentation

Key improvements:
1. Larger lookback buffer (500ms) to capture sentence beginnings
2. Smart sentence boundary detection for long segments
3. Maximum segment duration enforcement with graceful splitting
4. Pause-based segmentation for natural sentence breaks
"""

import numpy as np
import torch
from collections import deque
from typing import Optional, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class VADState(Enum):
    """VAD state machine states"""
    SILENCE = "silence"
    SPEECH = "speech"
    UNKNOWN = "unknown"


@dataclass
class AudioSegment:
    """Represents a detected speech segment"""
    start_time: float
    end_time: float
    audio_data: np.ndarray
    confidence: float
    sample_rate: int
    is_partial: bool = False  # True if segment was split
    
    @property
    def duration(self) -> float:
        """Get segment duration in seconds"""
        return self.end_time - self.start_time
    
    def to_bytes(self) -> bytes:
        """Convert audio data to bytes"""
        return self.audio_data.tobytes()
    
    def to_float32(self) -> np.ndarray:
        """Convert audio to float32 normalized format"""
        return self.audio_data.astype(np.float32) / 32768.0
    
    def split_at(self, split_time: float) -> Tuple['AudioSegment', 'AudioSegment']:
        """Split segment at specified time (relative to start)"""
        split_samples = int(split_time * self.sample_rate)
        
        first = AudioSegment(
            start_time=self.start_time,
            end_time=self.start_time + split_time,
            audio_data=self.audio_data[:split_samples],
            confidence=self.confidence,
            sample_rate=self.sample_rate,
            is_partial=True
        )
        
        second = AudioSegment(
            start_time=self.start_time + split_time,
            end_time=self.end_time,
            audio_data=self.audio_data[split_samples:],
            confidence=self.confidence,
            sample_rate=self.sample_rate,
            is_partial=True
        )
        
        return first, second


class ImprovedSileroVADProcessor:
    """
    Improved Silero VAD with sentence-aware segmentation
    
    Improvements:
    - 500ms lookback buffer (was 30ms) - captures sentence beginnings
    - Pause-based sentence boundary detection
    - Maximum segment duration enforcement (8s default)
    - Smart splitting at natural pauses
    
    Usage:
        vad = ImprovedSileroVADProcessor(sample_rate=16000)
        
        for audio_chunk in audio_stream:
            segments = vad.process_chunk(audio_chunk)  # Returns list now
            for segment in segments:
                process_segment(segment)
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 300,  # Increased from 100ms for better sentence boundaries
        speech_pad_ms: int = 500,  # Increased from 30ms for sentence beginning capture
        max_segment_duration_ms: int = 8000,  # 8 seconds max per segment
        use_onnx: bool = False,
        enable_pause_detection: bool = True,
        pause_threshold_ms: int = 800,  # Pause to consider as sentence boundary
    ):
        """
        Initialize Improved Silero VAD processor
        
        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, 48000)
            threshold: Speech detection threshold (0.0 - 1.0)
            min_speech_duration_ms: Minimum speech duration to trigger
            min_silence_duration_ms: Silence to end segment (300ms good for sentences)
            speech_pad_ms: Pre-speech buffer (500ms to capture sentence starts)
            max_segment_duration_ms: Maximum segment duration before forced split
            use_onnx: Use ONNX runtime instead of PyTorch
            enable_pause_detection: Enable pause-based sentence splitting
            pause_threshold_ms: Pause duration to trigger sentence split
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.max_segment_duration_ms = max_segment_duration_ms
        self.use_onnx = use_onnx
        self.enable_pause_detection = enable_pause_detection
        self.pause_threshold_ms = pause_threshold_ms
        
        # Validate sample rate
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Unsupported sample rate: {sample_rate}")
        
        # Load Silero VAD model
        logger.info("Loading Silero VAD model (improved version)...")
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=use_onnx
            )
            self.model = model
            self.get_speech_timestamps = utils[0]
            self.save_audio = utils[1]
            self.read_audio = utils[2]
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            raise
        
        # Set model to evaluation mode
        self.model.eval()
        torch.set_grad_enabled(False)
        
        # Pre-compute thresholds
        self._min_speech_chunks = max(1, min_speech_duration_ms // 30)
        self._min_silence_chunks = max(1, min_silence_duration_ms // 30)
        self._speech_pad_chunks = speech_pad_ms // 30
        self._max_segment_chunks = max_segment_duration_ms // 30
        self._pause_chunks = pause_threshold_ms // 30
        
        # State tracking
        self._reset_state()
        
        logger.info(f"Improved VAD initialized: threshold={threshold}, "
                   f"min_speech={min_speech_duration_ms}ms, "
                   f"min_silence={min_silence_duration_ms}ms, "
                   f"speech_pad={speech_pad_ms}ms, "
                   f"max_duration={max_segment_duration_ms}ms")
    
    def _reset_state(self):
        """Reset internal state"""
        self.state = VADState.SILENCE
        self.speech_counter = 0
        self.silence_counter = 0
        self.chunk_idx = 0
        self.current_segment_audio: List[np.ndarray] = []
        self.segment_start_time = 0.0
        self.confidences: List[float] = []
        
        # Extended pre-speech buffer (500ms)
        self.pre_buffer = deque(maxlen=self._speech_pad_chunks + 1)
        
        # Pause detection buffer
        self.speech_probs_buffer = deque(maxlen=100)  # ~3 seconds of history
        self.chunk_times = deque(maxlen=100)
        
        # Forced split tracking
        self.last_split_idx = 0
    
    def process_chunk(self, audio_chunk: np.ndarray) -> List[AudioSegment]:
        """
        Process a single audio chunk through VAD
        
        Args:
            audio_chunk: Audio data as numpy array (int16 or float32)
        
        Returns:
            List of AudioSegments (0, 1, or more if splitting occurs)
        """
        segments = []
        
        # Validate and prepare input
        min_samples = max(512, int(self.sample_rate * 0.03))
        if len(audio_chunk) < min_samples:
            audio_chunk = np.pad(
                audio_chunk,
                (0, min_samples - len(audio_chunk)),
                mode='constant'
            )
        
        # Convert to float32 tensor
        if audio_chunk.dtype == np.int16:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk.astype(np.float32)
        
        audio_tensor = torch.from_numpy(audio_float)
        
        # Get VAD probability
        try:
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
        except Exception as e:
            logger.warning(f"VAD inference error: {e}")
            speech_prob = 0.0
        
        # Store in buffers
        self.pre_buffer.append(audio_chunk)
        self.speech_probs_buffer.append(speech_prob)
        self.chunk_times.append(self.chunk_idx * 0.03)
        
        # State machine
        current_time = self.chunk_idx * 0.03
        
        if speech_prob >= self.threshold:
            # Speech detected
            self.speech_counter += 1
            self.silence_counter = 0
            self.confidences.append(speech_prob)
            
            if self.state == VADState.SILENCE:
                # Check if we have enough consecutive speech
                if self.speech_counter >= self._min_speech_chunks:
                    # Transition to speech
                    self.state = VADState.SPEECH
                    # Include extended pre-buffer for natural start
                    self.current_segment_audio = list(self.pre_buffer)
                    self.segment_start_time = current_time - len(self.pre_buffer) * 0.03
                    logger.debug(f"Speech started at {self.segment_start_time:.3f}s "
                               f"(with {len(self.pre_buffer)*30}ms lookback)")
            
            elif self.state == VADState.SPEECH:
                # Continue accumulating
                self.current_segment_audio.append(audio_chunk)
                
                # Check for maximum duration
                current_duration = len(self.current_segment_audio) * 0.03
                if current_duration >= self.max_segment_duration_ms / 1000:
                    # Try to find a natural pause to split
                    split_point = self._find_natural_split()
                    if split_point:
                        segment = self._split_at(split_point, current_time)
                        if segment:
                            segments.append(segment)
                            logger.debug(f"Split long segment at natural pause: {split_point:.3f}s")
                    else:
                        # Force split at max duration
                        segment = self._finalize_segment(current_time, is_partial=True)
                        segments.append(segment)
                        logger.warning(f"Forced split at max duration: {current_duration:.1f}s")
                        
                        # Start new segment with overlap for continuity
                        overlap_chunks = min(len(self.current_segment_audio), 10)  # 300ms overlap
                        self.current_segment_audio = self.current_segment_audio[-overlap_chunks:]
                        self.segment_start_time = current_time - len(self.current_segment_audio) * 0.03
                        self.confidences = self.confidences[-overlap_chunks:] if self.confidences else []
        
        else:
            # Silence detected
            self.silence_counter += 1
            self.speech_counter = 0
            
            if self.state == VADState.SPEECH:
                self.current_segment_audio.append(audio_chunk)
                
                # Check if silence duration exceeds threshold
                if self.silence_counter >= self._min_silence_chunks:
                    # Check if this is a natural sentence boundary or forced split
                    current_duration = len(self.current_segment_audio) * 0.03
                    
                    if current_duration > 3.0 and self.enable_pause_detection:
                        # For long segments, try to find a better split point
                        split_point = self._find_natural_split()
                        if split_point and split_point < current_time - 0.5:
                            # Split at natural pause
                            segment1 = self._split_at(split_point, split_point)
                            if segment1:
                                segments.append(segment1)
                            
                            # Continue with remaining audio
                            segment2 = self._finalize_segment(current_time)
                            segments.append(segment2)
                            logger.debug(f"Split at sentence boundary: {split_point:.3f}s")
                        else:
                            # End segment normally
                            segment = self._finalize_segment(current_time)
                            segments.append(segment)
                    else:
                        # End segment normally
                        segment = self._finalize_segment(current_time)
                        segments.append(segment)
                    
                    self.state = VADState.SILENCE
            
            elif self.state == VADState.SILENCE:
                # Continue buffering pre-speech audio
                pass
        
        self.chunk_idx += 1
        return segments
    
    def _find_natural_split(self) -> Optional[float]:
        """
        Find a natural pause in the speech for splitting
        
        Returns:
            Time relative to segment start to split at, or None if no good split found
        """
        if len(self.speech_probs_buffer) < 20:  # Need at least 600ms history
            return None
        
        # Look for a sustained pause (low probability) in the recent history
        probs = list(self.speech_probs_buffer)
        chunk_duration = 0.03  # 30ms per chunk
        
        # Scan for pause regions
        min_pause_duration = self.pause_threshold_ms / 1000  # Convert to seconds
        min_pause_chunks = int(min_pause_duration / chunk_duration)
        
        # Look backwards from current position
        current_pos = len(probs) - 1
        pause_start = None
        
        for i in range(current_pos, max(0, current_pos - 100), -1):
            if probs[i] < self.threshold * 0.5:  # Well below threshold
                if pause_start is None:
                    pause_start = i
            else:
                if pause_start is not None:
                    pause_duration = (pause_start - i) * chunk_duration
                    if pause_duration >= min_pause_duration:
                        # Found a good pause
                        split_idx = pause_start + (pause_start - i) // 2  # Middle of pause
                        
                        # Calculate time relative to segment start
                        segment_start_idx = len(probs) - len(self.current_segment_audio)
                        relative_idx = max(0, split_idx - segment_start_idx)
                        
                        # Ensure minimum segment duration after split
                        remaining_chunks = len(self.current_segment_audio) - relative_idx
                        if remaining_chunks >= self._min_speech_chunks:
                            return relative_idx * chunk_duration
                    pause_start = None
        
        return None
    
    def _split_at(self, split_time: float, current_time: float) -> Optional[AudioSegment]:
        """Split current segment at specified time"""
        split_chunks = int(split_time / 0.03)
        
        if split_chunks < self._min_speech_chunks:
            return None
        if split_chunks >= len(self.current_segment_audio):
            return None
        
        # Create segment from first part
        audio_data = np.concatenate(self.current_segment_audio[:split_chunks])
        avg_confidence = np.mean(self.confidences[:split_chunks]) if self.confidences else 0.5
        
        segment = AudioSegment(
            start_time=self.segment_start_time,
            end_time=self.segment_start_time + split_time,
            audio_data=audio_data,
            confidence=float(avg_confidence),
            sample_rate=self.sample_rate,
            is_partial=True
        )
        
        # Keep remaining audio for next segment
        self.current_segment_audio = self.current_segment_audio[split_chunks:]
        self.segment_start_time = current_time - len(self.current_segment_audio) * 0.03
        self.confidences = self.confidences[split_chunks:] if self.confidences else []
        
        return segment
    
    def _finalize_segment(self, end_time: float, is_partial: bool = False) -> AudioSegment:
        """Finalize current speech segment"""
        audio_data = np.concatenate(self.current_segment_audio)
        avg_confidence = np.mean(self.confidences) if self.confidences else 0.5
        
        segment = AudioSegment(
            start_time=self.segment_start_time,
            end_time=end_time,
            audio_data=audio_data,
            confidence=float(avg_confidence),
            sample_rate=self.sample_rate,
            is_partial=is_partial
        )
        
        # Reset segment state
        self.current_segment_audio = []
        self.confidences = []
        self.pre_buffer.clear()
        
        return segment
    
    def force_finalize(self) -> Optional[AudioSegment]:
        """Force finalize any pending segment"""
        if self.state == VADState.SPEECH and self.current_segment_audio:
            current_time = self.chunk_idx * 0.03
            return self._finalize_segment(current_time)
        return None
    
    def reset(self):
        """Reset VAD state for new session"""
        self._reset_state()
        logger.debug("VAD state reset")
    
    def get_state(self) -> VADState:
        """Get current VAD state"""
        return self.state
    
    def set_threshold(self, threshold: float):
        """Update detection threshold"""
        self.threshold = max(0.0, min(1.0, threshold))
        logger.info(f"VAD threshold updated to {self.threshold}")


def create_vad_for_system_audio() -> ImprovedSileroVADProcessor:
    """Create VAD optimized for system audio capture"""
    return ImprovedSileroVADProcessor(
        sample_rate=16000,
        threshold=0.4,  # Lower threshold for potentially quieter system audio
        min_speech_duration_ms=200,  # Shorter minimum for quick response
        min_silence_duration_ms=400,  # Good balance for sentence boundaries
        speech_pad_ms=500,  # Capture sentence beginnings
        max_segment_duration_ms=10000,  # 10s max for system audio
        pause_threshold_ms=1000,  # 1s pause for sentence boundary
    )


def create_vad_for_microphone() -> ImprovedSileroVADProcessor:
    """Create VAD optimized for microphone capture"""
    return ImprovedSileroVADProcessor(
        sample_rate=16000,
        threshold=0.5,
        min_speech_duration_ms=250,
        min_silence_duration_ms=300,
        speech_pad_ms=500,  # Capture sentence beginnings
        max_segment_duration_ms=4000  # Phase 1.1,  # 8s max for microphone
        pause_threshold_ms=800,
    )
