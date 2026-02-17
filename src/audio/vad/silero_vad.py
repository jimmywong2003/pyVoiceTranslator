"""
Silero VAD implementation

High-accuracy voice activity detection using Silero's deep learning model.
Optimized for real-time streaming applications.
"""

import numpy as np
import torch
from collections import deque
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging

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


class SileroVADProcessor:
    """
    Silero VAD processor with streaming support
    
    Features:
    - Real-time streaming VAD
    - Configurable thresholds
    - Speech padding for natural boundaries
    - State machine for robust detection
    
    Usage:
        vad = SileroVADProcessor(sample_rate=16000)
        
        for audio_chunk in audio_stream:
            segment = vad.process_chunk(audio_chunk)
            if segment:
                print(f"Speech detected: {segment.duration:.2f}s")
                # Process segment...
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        speech_pad_ms: int = 30,
        use_onnx: bool = False
    ):
        """
        Initialize Silero VAD processor
        
        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, 48000)
            threshold: Speech detection threshold (0.0 - 1.0)
            min_speech_duration_ms: Minimum speech duration to trigger
            min_silence_duration_ms: Silence duration to end segment
            speech_pad_ms: Padding around speech segments
            use_onnx: Use ONNX runtime instead of PyTorch
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.use_onnx = use_onnx
        
        # Validate sample rate
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Unsupported sample rate: {sample_rate}")
        
        # Load Silero VAD model
        logger.info("Loading Silero VAD model...")
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
        
        # Disable gradient computation for inference
        torch.set_grad_enabled(False)
        
        # Pre-compute thresholds
        self._min_speech_chunks = max(1, min_speech_duration_ms // 30)
        self._min_silence_chunks = max(1, min_silence_duration_ms // 30)
        self._speech_pad_chunks = speech_pad_ms // 30
        
        # State tracking (must be after threshold computation)
        self._reset_state()
        
        logger.info(f"VAD initialized: threshold={threshold}, "
                   f"min_speech={min_speech_duration_ms}ms, "
                   f"min_silence={min_silence_duration_ms}ms")
    
    def _reset_state(self):
        """Reset internal state"""
        self.state = VADState.SILENCE
        self.speech_counter = 0
        self.silence_counter = 0
        self.chunk_idx = 0
        self.current_segment_audio: List[np.ndarray] = []
        self.segment_start_time = 0.0
        self.confidences: List[float] = []
        
        # Pre-speech buffer for padding
        self.pre_buffer = deque(maxlen=self._speech_pad_chunks + 1)
    
    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[AudioSegment]:
        """
        Process a single audio chunk through VAD
        
        Args:
            audio_chunk: Audio data as numpy array (int16 or float32)
                        Expected size: sample_rate * 30ms (e.g., 480 samples at 16kHz)
        
        Returns:
            AudioSegment if speech segment completed, None otherwise
        """
        # Validate input
        # Silero VAD requires minimum chunk size: sample_rate / 31.25
        # For 16kHz: 16000 / 31.25 = 512 samples minimum
        min_samples = max(512, int(self.sample_rate * 0.03))
        expected_samples = int(self.sample_rate * 0.03)  # 30ms
        
        if len(audio_chunk) < min_samples:
            # Pad to minimum required size
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
        
        # Store in pre-buffer
        self.pre_buffer.append(audio_chunk)
        
        # State machine
        segment = None
        current_time = self.chunk_idx * 0.03  # 30ms chunks
        
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
                    # Include pre-buffer for natural start
                    self.current_segment_audio = list(self.pre_buffer)
                    self.segment_start_time = current_time - len(self.pre_buffer) * 0.03
                    logger.debug(f"Speech started at {self.segment_start_time:.3f}s")
            
            elif self.state == VADState.SPEECH:
                # Continue accumulating
                self.current_segment_audio.append(audio_chunk)
                
        else:
            # Silence detected
            self.silence_counter += 1
            self.speech_counter = 0
            
            if self.state == VADState.SPEECH:
                # Check if silence duration exceeds threshold
                if self.silence_counter >= self._min_silence_chunks:
                    # Transition to silence - finalize segment
                    segment = self._finalize_segment(current_time)
                    self.state = VADState.SILENCE
                    logger.debug(f"Speech ended at {current_time:.3f}s, "
                               f"duration: {segment.duration:.3f}s")
            
            elif self.state == VADState.SILENCE:
                # Continue buffering pre-speech audio
                pass
        
        self.chunk_idx += 1
        return segment
    
    def _finalize_segment(self, end_time: float) -> AudioSegment:
        """Finalize current speech segment"""
        # Concatenate all audio
        audio_data = np.concatenate(self.current_segment_audio)
        
        # Calculate average confidence
        avg_confidence = np.mean(self.confidences) if self.confidences else 0.5
        
        # Reset segment state
        self.current_segment_audio = []
        self.confidences = []
        self.pre_buffer.clear()
        
        return AudioSegment(
            start_time=self.segment_start_time,
            end_time=end_time,
            audio_data=audio_data,
            confidence=float(avg_confidence),
            sample_rate=self.sample_rate
        )
    
    def force_finalize(self) -> Optional[AudioSegment]:
        """
        Force finalize any pending segment
        
        Call this when stopping capture to get the last segment
        
        Returns:
            AudioSegment if there's a pending segment, None otherwise
        """
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
