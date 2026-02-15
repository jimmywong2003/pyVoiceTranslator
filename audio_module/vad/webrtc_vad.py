"""
WebRTC VAD implementation

Lightweight fallback VAD using Google's WebRTC implementation.
Lower accuracy but minimal resource usage.
"""

import numpy as np
from collections import deque
from typing import Optional, List
from dataclasses import dataclass
import logging

from .silero_vad import VADState, AudioSegment

logger = logging.getLogger(__name__)


class WebRTCVADProcessor:
    """
    WebRTC VAD processor
    
    Lightweight alternative to Silero VAD with lower resource usage.
    Good for low-power devices or as a fallback.
    
    Limitations:
    - Only supports 8000, 16000, 32000, 48000 Hz
    - Frame sizes: 10, 20, or 30ms
    - Less accurate in noisy environments
    
    Usage:
        vad = WebRTCVADProcessor(sample_rate=16000, aggressiveness=2)
        
        for audio_chunk in audio_stream:
            segment = vad.process_chunk(audio_chunk)
            if segment:
                print(f"Speech detected: {segment.duration:.2f}s")
    """
    
    # Aggressiveness levels: 0 (least) to 3 (most aggressive)
    AGGRESSIVENESS_LEVELS = {
        0: "Very permissive - more false positives",
        1: "Permissive",
        2: "Balanced (recommended)",
        3: "Aggressive - more false negatives"
    }
    
    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 2,
        frame_duration_ms: int = 30,
        min_speech_duration_ms: int = 300,
        min_silence_duration_ms: int = 150
    ):
        """
        Initialize WebRTC VAD processor
        
        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, 48000)
            aggressiveness: VAD aggressiveness (0-3)
            frame_duration_ms: Frame size in ms (10, 20, or 30)
            min_speech_duration_ms: Minimum speech duration
            min_silence_duration_ms: Silence duration to end segment
        """
        self.sample_rate = sample_rate
        self.aggressiveness = aggressiveness
        self.frame_duration_ms = frame_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        
        # Validate parameters
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Unsupported sample rate: {sample_rate}")
        
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"Unsupported frame duration: {frame_duration_ms}")
        
        if aggressiveness not in [0, 1, 2, 3]:
            raise ValueError(f"Invalid aggressiveness: {aggressiveness}")
        
        # Import webrtcvad
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(aggressiveness)
            logger.info(f"WebRTC VAD initialized (aggressiveness={aggressiveness})")
        except ImportError:
            logger.error("webrtcvad not installed. Run: pip install webrtcvad")
            raise
        
        # Calculate frame size
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # State tracking
        self._reset_state()
        
        # Pre-compute thresholds
        self._min_speech_frames = max(1, min_speech_duration_ms // frame_duration_ms)
        self._min_silence_frames = max(1, min_silence_duration_ms // frame_duration_ms)
        
        logger.info(f"WebRTC VAD: frame_size={self.frame_size}, "
                   f"min_speech_frames={self._min_speech_frames}")
    
    def _reset_state(self):
        """Reset internal state"""
        self.state = VADState.SILENCE
        self.speech_counter = 0
        self.silence_counter = 0
        self.frame_idx = 0
        self.current_segment_audio: List[np.ndarray] = []
        self.segment_start_time = 0.0
        self.pre_buffer = deque(maxlen=5)
    
    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[AudioSegment]:
        """
        Process audio chunk through WebRTC VAD
        
        Args:
            audio_chunk: Audio data as numpy array (int16)
        
        Returns:
            AudioSegment if speech segment completed, None otherwise
        """
        # Ensure correct format
        if audio_chunk.dtype != np.int16:
            if audio_chunk.dtype == np.float32:
                audio_chunk = (audio_chunk * 32767).astype(np.int16)
            else:
                audio_chunk = audio_chunk.astype(np.int16)
        
        # Handle chunk size mismatch
        if len(audio_chunk) < self.frame_size:
            # Pad to frame size
            audio_chunk = np.pad(
                audio_chunk,
                (0, self.frame_size - len(audio_chunk)),
                mode='constant'
            )
        elif len(audio_chunk) > self.frame_size:
            # Process only first frame
            audio_chunk = audio_chunk[:self.frame_size]
        
        # Convert to bytes for WebRTC VAD
        frame_bytes = audio_chunk.tobytes()
        
        # Run VAD
        try:
            is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
        except Exception as e:
            logger.warning(f"WebRTC VAD error: {e}")
            is_speech = False
        
        # Store in pre-buffer
        self.pre_buffer.append(audio_chunk)
        
        # State machine
        segment = None
        current_time = self.frame_idx * (self.frame_duration_ms / 1000)
        
        if is_speech:
            # Speech detected
            self.speech_counter += 1
            self.silence_counter = 0
            
            if self.state == VADState.SILENCE:
                if self.speech_counter >= self._min_speech_frames:
                    # Transition to speech
                    self.state = VADState.SPEECH
                    self.current_segment_audio = list(self.pre_buffer)
                    self.segment_start_time = current_time - len(self.pre_buffer) * (self.frame_duration_ms / 1000)
                    logger.debug(f"Speech started at {self.segment_start_time:.3f}s")
            
            elif self.state == VADState.SPEECH:
                self.current_segment_audio.append(audio_chunk)
        
        else:
            # Silence detected
            self.silence_counter += 1
            self.speech_counter = 0
            
            if self.state == VADState.SPEECH:
                if self.silence_counter >= self._min_silence_frames:
                    # End segment
                    segment = self._finalize_segment(current_time)
                    self.state = VADState.SILENCE
                    logger.debug(f"Speech ended at {current_time:.3f}s")
        
        self.frame_idx += 1
        return segment
    
    def _finalize_segment(self, end_time: float) -> AudioSegment:
        """Finalize current speech segment"""
        audio_data = np.concatenate(self.current_segment_audio)
        
        self.current_segment_audio = []
        self.pre_buffer.clear()
        
        return AudioSegment(
            start_time=self.segment_start_time,
            end_time=end_time,
            audio_data=audio_data,
            confidence=0.7,  # WebRTC doesn't provide confidence scores
            sample_rate=self.sample_rate
        )
    
    def force_finalize(self) -> Optional[AudioSegment]:
        """Force finalize any pending segment"""
        if self.state == VADState.SPEECH and self.current_segment_audio:
            current_time = self.frame_idx * (self.frame_duration_ms / 1000)
            return self._finalize_segment(current_time)
        return None
    
    def reset(self):
        """Reset VAD state"""
        self._reset_state()
        logger.debug("WebRTC VAD state reset")
    
    def get_state(self) -> VADState:
        """Get current VAD state"""
        return self.state
    
    def set_aggressiveness(self, aggressiveness: int):
        """Update VAD aggressiveness"""
        if aggressiveness not in [0, 1, 2, 3]:
            raise ValueError(f"Invalid aggressiveness: {aggressiveness}")
        
        self.aggressiveness = aggressiveness
        self.vad.set_mode(aggressiveness)
        logger.info(f"WebRTC VAD aggressiveness set to {aggressiveness}")
