"""Base ASR interface and data structures."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ASRProvider(Enum):
    """ASR provider types."""
    WHISPER_CPP = "whisper.cpp"
    FASTER_WHISPER = "faster_whisper"
    MLX_WHISPER = "mlx_whisper"
    OPENAI_API = "openai_api"


@dataclass
class Word:
    """Word-level timestamp information."""
    word: str
    start: float  # Start time in seconds
    end: float    # End time in seconds
    probability: Optional[float] = None


@dataclass
class Segment:
    """Transcription segment with timestamps."""
    id: int
    start: float
    end: float
    text: str
    words: Optional[List[Word]] = None
    confidence: float = 0.0
    speaker: Optional[str] = None


@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    text: str
    language: str
    confidence: float
    segments: List[Segment] = field(default_factory=list)
    words: Optional[List[Word]] = None
    duration: Optional[float] = None
    processing_time: Optional[float] = None
    
    @property
    def word_count(self) -> int:
        """Return total word count."""
        return len(self.text.split())
    
    @property
    def is_reliable(self) -> bool:
        """Check if transcription confidence is above threshold."""
        return self.confidence >= 0.7


class BaseASR(ABC):
    """Abstract base class for ASR implementations."""
    
    def __init__(self, model_name: str, language: Optional[str] = None):
        self.model_name = model_name
        self.language = language
        self._is_initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the ASR model."""
        pass
    
    @abstractmethod
    def transcribe(
        self, 
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'zh', 'en')
            **kwargs: Additional implementation-specific options
            
        Returns:
            TranscriptionResult with text, timestamps, and metadata
        """
        pass
    
    def transcribe_batch(
        self,
        audio_paths: List[str],
        language: Optional[str] = None,
        **kwargs
    ) -> List[TranscriptionResult]:
        """
        Transcribe multiple audio files.
        
        Default implementation processes sequentially.
        Override for parallel/batch processing.
        """
        return [self.transcribe(path, language, **kwargs) for path in audio_paths]
    
    @abstractmethod
    def transcribe_stream(
        self,
        audio_stream: Iterator[bytes],
        sample_rate: int = 16000,
        **kwargs
    ) -> Iterator[TranscriptionResult]:
        """
        Transcribe audio stream in real-time.
        
        Args:
            audio_stream: Iterator yielding audio chunks
            sample_rate: Audio sample rate in Hz
            **kwargs: Additional options
            
        Yields:
            TranscriptionResult chunks as they become available
        """
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Return True if this ASR supports real-time streaming."""
        pass
    
    @property
    @abstractmethod
    def supports_word_timestamps(self) -> bool:
        """Return True if this ASR supports word-level timestamps."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if model is initialized."""
        return self._is_initialized
    
    def get_info(self) -> Dict[str, Any]:
        """Get ASR implementation information."""
        return {
            "model_name": self.model_name,
            "language": self.language,
            "supports_streaming": self.supports_streaming,
            "supports_word_timestamps": self.supports_word_timestamps,
            "initialized": self.is_initialized,
        }
