"""Hybrid edge-cloud translation pipeline."""

import time
from typing import Optional, Callable, Iterator
from pathlib import Path

from .base import TranslationPipeline, PipelineResult
from ..asr.base import BaseASR
from ..translation.base import BaseTranslator


class HybridTranslator(TranslationPipeline):
    """
    Hybrid edge-cloud translation pipeline with fallback.
    
    Uses edge models by default, but falls back to cloud APIs
    when confidence is low or for specific scenarios.
    
    Example:
        >>> translator = HybridTranslator(
        ...     edge_asr=whisper_cpp_asr,
        ...     edge_translator=nllb_translator,
        ...     cloud_asr=openai_api_asr,  # Optional
        ...     cloud_translator=deepl_translator,  # Optional
        ...     source_lang="zh",
        ...     target_lang="en",
        ...     confidence_threshold=0.7
        ... )
        >>> result = translator.process("audio.wav")
    """
    
    def __init__(
        self,
        edge_asr: BaseASR,
        edge_translator: BaseTranslator,
        source_lang: str,
        target_lang: str,
        cloud_asr: Optional[BaseASR] = None,
        cloud_translator: Optional[BaseTranslator] = None,
        confidence_threshold: float = 0.7,
        retry_on_low_confidence: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        super().__init__(source_lang, target_lang, progress_callback)
        
        self.edge_asr = edge_asr
        self.edge_translator = edge_translator
        self.cloud_asr = cloud_asr
        self.cloud_translator = cloud_translator
        self.confidence_threshold = confidence_threshold
        self.retry_on_low_confidence = retry_on_low_confidence
        
        # Initialize edge components
        if not edge_asr.is_initialized:
            edge_asr.initialize()
        if not edge_translator.is_initialized:
            edge_translator.initialize()
        
        # Initialize cloud components if available
        if cloud_asr and not cloud_asr.is_initialized:
            cloud_asr.initialize()
        if cloud_translator and not cloud_translator.is_initialized:
            cloud_translator.initialize()
    
    @property
    def has_cloud_fallback(self) -> bool:
        """Check if cloud fallback is available."""
        return self.cloud_asr is not None and self.cloud_translator is not None
    
    def process(
        self,
        audio_path: str,
        prefer_cloud: bool = False,
        **kwargs
    ) -> PipelineResult:
        """
        Process audio file with edge-cloud hybrid approach.
        
        Args:
            audio_path: Path to audio file
            prefer_cloud: Prefer cloud processing (default: False)
            **kwargs: Additional options
            
        Returns:
            PipelineResult with best available transcription and translation
        """
        start_time = time.time()
        
        # If prefer_cloud and cloud available, use cloud directly
        if prefer_cloud and self.has_cloud_fallback:
            return self._process_cloud(audio_path)
        
        # Try edge first
        self._report_progress(0.1, "Processing with edge models...")
        edge_result = self._process_edge(audio_path)
        
        # Check if edge result is good enough
        if edge_result.is_success and edge_result.is_reliable:
            self._report_progress(1.0, "Edge processing successful!")
            return edge_result
        
        # Fall back to cloud if available and enabled
        if self.has_cloud_fallback and self.retry_on_low_confidence:
            self._report_progress(0.5, "Edge confidence low, trying cloud...")
            cloud_result = self._process_cloud(audio_path)
            
            if cloud_result.is_success:
                # Return cloud result with edge result as fallback info
                cloud_result.edge_fallback = edge_result
                self._report_progress(1.0, "Cloud processing successful!")
                return cloud_result
        
        # Return edge result even if low confidence
        self._report_progress(1.0, "Processing complete (edge only)")
        return edge_result
    
    def _process_edge(self, audio_path: str) -> PipelineResult:
        """Process using edge models."""
        try:
            # Transcribe
            transcription = self.edge_asr.transcribe(
                audio_path,
                language=self.source_lang
            )
            
            # Translate
            translation = self.edge_translator.translate(
                transcription.text,
                self.source_lang,
                self.target_lang
            )
            
            return PipelineResult(
                source_audio=audio_path,
                transcription=transcription,
                source_text=transcription.text,
                source_language=transcription.language,
                translation=translation,
                translated_text=translation.translated_text,
                target_language=self.target_lang,
                confidence=transcription.confidence,
                processing_time=translation.processing_time
            )
        
        except Exception as e:
            return PipelineResult(
                source_audio=audio_path,
                errors=[f"Edge error: {str(e)}"],
                confidence=0.0
            )
    
    def _process_cloud(self, audio_path: str) -> PipelineResult:
        """Process using cloud APIs."""
        try:
            # Transcribe
            transcription = self.cloud_asr.transcribe(
                audio_path,
                language=self.source_lang
            )
            
            # Translate
            translation = self.cloud_translator.translate(
                transcription.text,
                self.source_lang,
                self.target_lang
            )
            
            return PipelineResult(
                source_audio=audio_path,
                transcription=transcription,
                source_text=transcription.text,
                source_language=transcription.language,
                translation=translation,
                translated_text=translation.translated_text,
                target_language=self.target_lang,
                confidence=transcription.confidence,
                processing_time=translation.processing_time
            )
        
        except Exception as e:
            return PipelineResult(
                source_audio=audio_path,
                errors=[f"Cloud error: {str(e)}"],
                confidence=0.0
            )
    
    def process_stream(self, audio_stream, **kwargs):
        """Streaming not supported for hybrid translator."""
        raise NotImplementedError(
            "HybridTranslator does not support streaming. "
            "Use RealtimeTranslator for streaming."
        )
    
    def get_info(self) -> dict:
        """Get hybrid translator information."""
        return {
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'confidence_threshold': self.confidence_threshold,
            'has_cloud_fallback': self.has_cloud_fallback,
            'edge_asr': self.edge_asr.get_info(),
            'edge_translator': self.edge_translator.get_info(),
            'cloud_asr': self.cloud_asr.get_info() if self.cloud_asr else None,
            'cloud_translator': self.cloud_translator.get_info() if self.cloud_translator else None,
        }
