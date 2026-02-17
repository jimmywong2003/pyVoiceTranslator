"""Base pipeline interface for translation workflows."""

from abc import ABC, abstractmethod
from typing import Optional, List, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from ..asr.base import TranscriptionResult
from ..translation.base import TranslationResult


@dataclass
class PipelineResult:
    """Complete pipeline result with ASR and translation."""
    # Source information
    source_audio: Optional[str] = None
    source_duration: Optional[float] = None
    
    # ASR results
    transcription: Optional[TranscriptionResult] = None
    source_text: Optional[str] = None
    source_language: Optional[str] = None
    
    # Translation results
    translation: Optional[TranslationResult] = None
    translated_text: Optional[str] = None
    target_language: Optional[str] = None
    
    # Metadata
    processing_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    @property
    def is_success(self) -> bool:
        """Check if pipeline completed successfully."""
        return len(self.errors) == 0 and self.translated_text is not None
    
    @property
    def is_reliable(self) -> bool:
        """Check if result confidence is above threshold."""
        return self.confidence >= 0.7
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'source_audio': self.source_audio,
            'source_duration': self.source_duration,
            'source_text': self.source_text,
            'source_language': self.source_language,
            'translated_text': self.translated_text,
            'target_language': self.target_language,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'errors': self.errors,
            'is_success': self.is_success,
        }
    
    def to_srt(self) -> str:
        """Convert to SRT subtitle format."""
        if not self.transcription or not self.transcription.segments:
            return ""
        
        srt_lines = []
        for i, seg in enumerate(self.transcription.segments, 1):
            # Format timestamps
            start = self._format_timestamp(seg.start)
            end = self._format_timestamp(seg.end)
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(seg.text)
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def to_vtt(self) -> str:
        """Convert to WebVTT subtitle format."""
        if not self.transcription or not self.transcription.segments:
            return ""
        
        vtt_lines = ["WEBVTT", ""]
        
        for seg in self.transcription.segments:
            start = self._format_timestamp(seg.start, vtt=True)
            end = self._format_timestamp(seg.end, vtt=True)
            
            vtt_lines.append(f"{start} --> {end}")
            vtt_lines.append(seg.text)
            vtt_lines.append("")
        
        return "\n".join(vtt_lines)
    
    @staticmethod
    def _format_timestamp(seconds: float, vtt: bool = False) -> str:
        """Format seconds to SRT/VTT timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        if vtt:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class TranslationPipeline(ABC):
    """Abstract base class for translation pipelines."""
    
    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.progress_callback = progress_callback
        self._is_running = False
    
    @abstractmethod
    def process(
        self,
        audio_path: str,
        **kwargs
    ) -> PipelineResult:
        """
        Process audio file through the pipeline.
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional options
            
        Returns:
            PipelineResult with transcription and translation
        """
        pass
    
    @abstractmethod
    def process_stream(
        self,
        audio_stream: Iterator[bytes],
        **kwargs
    ) -> Iterator[PipelineResult]:
        """
        Process audio stream in real-time.
        
        Args:
            audio_stream: Iterator yielding audio chunks
            **kwargs: Additional options
            
        Yields:
            PipelineResult chunks as they become available
        """
        pass
    
    def _report_progress(self, progress: float, message: str):
        """Report progress through callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently processing."""
        return self._is_running
    
    def stop(self):
        """Stop the pipeline."""
        self._is_running = False
