"""Voice Activity Detection (VAD) implementations."""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class VADState(Enum):
    """VAD state machine states."""
    SILENCE = "silence"
    SPEECH = "speech"
    STARTING = "starting"
    ENDING = "ending"


@dataclass
class SpeechSegment:
    """Detected speech segment."""
    start: float  # Start time in seconds
    end: float    # End time in seconds
    confidence: float
    
    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end - self.start


class BaseVAD:
    """Base class for VAD implementations."""
    
    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.3,
    ):
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
    
    def detect(self, audio_chunk: np.ndarray) -> float:
        """
        Detect speech probability in audio chunk.
        
        Args:
            audio_chunk: Audio samples
            
        Returns:
            Speech probability (0.0 to 1.0)
        """
        raise NotImplementedError
    
    def detect_segments(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> List[SpeechSegment]:
        """
        Detect all speech segments in audio.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate
            
        Returns:
            List of speech segments
        """
        raise NotImplementedError


class SileroVAD(BaseVAD):
    """
    Silero VAD implementation.
    
    High-quality neural network-based VAD.
    
    Example:
        >>> vad = SileroVAD()
        >>> prob = vad.detect(audio_chunk)
        >>> segments = vad.detect_segments(audio, 16000)
    """
    
    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.3,
        model_name: str = "silero_vad",
    ):
        super().__init__(threshold, min_speech_duration, min_silence_duration)
        
        self.model_name = model_name
        self._model = None
        self._utils = None
        self._sample_rate = 16000
    
    def _load_model(self):
        """Lazy load Silero VAD model."""
        if self._model is not None:
            return
        
        try:
            import torch
            self._model, self._utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self._model.eval()
        except Exception as e:
            raise ImportError(
                f"Failed to load Silero VAD: {e}. "
                "Make sure torch and torchaudio are installed."
            )
    
    def detect(self, audio_chunk: np.ndarray) -> float:
        """
        Detect speech probability.
        
        Args:
            audio_chunk: Audio samples (should be 30ms for optimal performance)
            
        Returns:
            Speech probability (0.0 to 1.0)
        """
        self._load_model()
        
        import torch
        
        # Convert to tensor
        if isinstance(audio_chunk, np.ndarray):
            audio_chunk = torch.from_numpy(audio_chunk).float()
        
        # Ensure correct shape
        if audio_chunk.dim() == 1:
            audio_chunk = audio_chunk.unsqueeze(0)
        
        # Get speech probability
        with torch.no_grad():
            speech_prob = self._model(audio_chunk, self._sample_rate).item()
        
        return speech_prob
    
    def detect_segments(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> List[SpeechSegment]:
        """
        Detect speech segments using Silero VAD.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate (must be 8000 or 16000)
            
        Returns:
            List of speech segments
        """
        self._load_model()
        
        import torch
        
        # Validate sample rate
        if sample_rate not in [8000, 16000]:
            raise ValueError("Silero VAD requires 8000 or 16000 Hz sample rate")
        
        # Convert to tensor
        if isinstance(audio, np.ndarray):
            audio = torch.from_numpy(audio).float()
        
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
        
        # Use Silero's get_speech_timestamps utility
        get_speech_timestamps = self._utils[0]
        
        timestamps = get_speech_timestamps(
            audio[0],
            self._model,
            threshold=self.threshold,
            sampling_rate=sample_rate,
            min_speech_duration_ms=int(self.min_speech_duration * 1000),
            min_silence_duration_ms=int(self.min_silence_duration * 1000),
        )
        
        # Convert to SpeechSegment objects
        segments = []
        for ts in timestamps:
            start = ts['start'] / sample_rate
            end = ts['end'] / sample_rate
            segments.append(SpeechSegment(
                start=start,
                end=end,
                confidence=1.0  # Silero doesn't provide per-segment confidence
            ))
        
        return segments
    
    def get_speech_chunks(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> List[np.ndarray]:
        """
        Extract speech chunks from audio.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate
            
        Returns:
            List of audio arrays containing only speech
        """
        segments = self.detect_segments(audio, sample_rate)
        
        chunks = []
        for seg in segments:
            start_sample = int(seg.start * sample_rate)
            end_sample = int(seg.end * sample_rate)
            chunks.append(audio[start_sample:end_sample])
        
        return chunks


class WebRTCVAD(BaseVAD):
    """
    WebRTC VAD implementation.
    
    Lightweight, fast VAD suitable for real-time applications.
    Less accurate than Silero but faster.
    
    Example:
        >>> vad = WebRTCVAD(aggressiveness=2)
        >>> is_speech = vad.detect(audio_chunk, sample_rate=16000)
    """
    
    def __init__(
        self,
        aggressiveness: int = 2,
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.3,
    ):
        super().__init__(0.5, min_speech_duration, min_silence_duration)
        
        self.aggressiveness = aggressiveness
        self._vad = None
    
    def _load_vad(self):
        """Lazy load WebRTC VAD."""
        if self._vad is not None:
            return
        
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(self.aggressiveness)
        except ImportError:
            raise ImportError(
                "webrtcvad not installed. "
                "Run: pip install webrtcvad-wheels"
            )
    
    def detect(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        Detect if audio chunk contains speech.
        
        Args:
            audio_chunk: Audio samples (must be 10, 20, or 30ms)
            sample_rate: Sample rate (must be 8000, 16000, 32000, or 48000)
            
        Returns:
            True if speech detected
        """
        self._load_vad()
        
        # Convert to bytes (16-bit PCM)
        if isinstance(audio_chunk, np.ndarray):
            audio_bytes = (audio_chunk * 32767).astype(np.int16).tobytes()
        else:
            audio_bytes = audio_chunk
        
        return self._vad.is_speech(audio_bytes, sample_rate)
    
    def detect_segments(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30
    ) -> List[SpeechSegment]:
        """
        Detect speech segments using WebRTC VAD.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate
            frame_duration_ms: Frame duration (10, 20, or 30ms)
            
        Returns:
            List of speech segments
        """
        self._load_vad()
        
        frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Process frames
        segments = []
        in_speech = False
        speech_start = 0
        
        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i + frame_size]
            is_speech = self.detect(frame, sample_rate)
            
            if is_speech and not in_speech:
                # Speech start
                in_speech = True
                speech_start = i / sample_rate
            elif not is_speech and in_speech:
                # Speech end
                in_speech = False
                speech_end = i / sample_rate
                
                if speech_end - speech_start >= self.min_speech_duration:
                    segments.append(SpeechSegment(
                        start=speech_start,
                        end=speech_end,
                        confidence=1.0
                    ))
        
        # Handle ongoing speech at end
        if in_speech:
            speech_end = len(audio) / sample_rate
            if speech_end - speech_start >= self.min_speech_duration:
                segments.append(SpeechSegment(
                    start=speech_start,
                    end=speech_end,
                    confidence=1.0
                ))
        
        return segments


class StreamingVAD:
    """
    Streaming VAD with state machine for real-time processing.
    
    Example:
        >>> vad = StreamingVAD(silero_vad)
        >>> for chunk in audio_stream:
        ...     state, segment = vad.process(chunk)
        ...     if state == VADState.ENDING:
        ...         process_segment(segment)
    """
    
    def __init__(
        self,
        vad: BaseVAD,
        threshold: float = 0.5,
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.5,
    ):
        self.vad = vad
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        
        self.state = VADState.SILENCE
        self.buffer = []
        self.speech_start = 0
        self.silence_start = 0
        self.total_samples = 0
    
    def process(
        self,
        audio_chunk: np.ndarray,
        sample_rate: int = 16000
    ) -> Tuple[VADState, Optional[SpeechSegment]]:
        """
        Process audio chunk in streaming mode.
        
        Args:
            audio_chunk: Audio samples
            sample_rate: Sample rate
            
        Returns:
            Tuple of (current_state, speech_segment if ending)
        """
        # Detect speech
        if isinstance(self.vad, SileroVAD):
            prob = self.vad.detect(audio_chunk)
            is_speech = prob > self.threshold
        else:
            is_speech = self.vad.detect(audio_chunk, sample_rate)
        
        chunk_duration = len(audio_chunk) / sample_rate
        self.total_samples += len(audio_chunk)
        
        segment = None
        
        # State machine
        if self.state == VADState.SILENCE:
            if is_speech:
                self.state = VADState.STARTING
                self.speech_start = (self.total_samples - len(audio_chunk)) / sample_rate
                self.buffer = [audio_chunk]
        
        elif self.state == VADState.STARTING:
            self.buffer.append(audio_chunk)
            speech_duration = len(self.buffer) * chunk_duration
            
            if speech_duration >= self.min_speech_duration:
                self.state = VADState.SPEECH
            elif not is_speech:
                self.state = VADState.SILENCE
                self.buffer = []
        
        elif self.state == VADState.SPEECH:
            self.buffer.append(audio_chunk)
            
            if not is_speech:
                self.state = VADState.ENDING
                self.silence_start = self.total_samples / sample_rate
        
        elif self.state == VADState.ENDING:
            self.buffer.append(audio_chunk)
            silence_duration = (self.total_samples / sample_rate) - self.silence_start
            
            if is_speech:
                self.state = VADState.SPEECH
            elif silence_duration >= self.min_silence_duration:
                # Speech ended
                speech_end = self.silence_start
                segment = SpeechSegment(
                    start=self.speech_start,
                    end=speech_end,
                    confidence=1.0
                )
                self.state = VADState.SILENCE
                self.buffer = []
        
        return self.state, segment
    
    def flush(self) -> Optional[SpeechSegment]:
        """Flush any remaining speech in buffer."""
        if self.state in [VADState.SPEECH, VADState.ENDING] and self.buffer:
            segment = SpeechSegment(
                start=self.speech_start,
                end=self.total_samples / 16000,
                confidence=1.0
            )
            self.state = VADState.SILENCE
            self.buffer = []
            return segment
        return None
