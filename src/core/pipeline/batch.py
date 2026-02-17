"""Batch video translation pipeline."""

import time
from typing import Optional, Callable, List
from pathlib import Path

from .base import TranslationPipeline, PipelineResult
from ..asr.base import BaseASR
from ..translation.base import BaseTranslator
from ..audio.video import VideoExtractor


class BatchVideoTranslator(TranslationPipeline):
    """
    Batch video transcription and translation pipeline.
    
    Processes video files by extracting audio, transcribing,
    and translating in segments.
    
    Example:
        >>> translator = BatchVideoTranslator(
        ...     asr=faster_whisper_asr,
        ...     translator=nllb_translator,
        ...     source_lang="zh",
        ...     target_lang="en"
        ... )
        >>> result = translator.process("video.mp4")
        >>> print(result.to_srt())  # Get subtitles
    """
    
    def __init__(
        self,
        asr: BaseASR,
        translator: BaseTranslator,
        source_lang: str,
        target_lang: str,
        segment_duration: float = 30.0,
        overlap: float = 1.0,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        super().__init__(source_lang, target_lang, progress_callback)
        
        self.asr = asr
        self.translator = translator
        self.segment_duration = segment_duration
        self.overlap = overlap
        
        # Initialize components
        if not asr.is_initialized:
            asr.initialize()
        if not translator.is_initialized:
            translator.initialize()
        
        self.video_extractor = VideoExtractor()
    
    def process(
        self,
        video_path: str,
        audio_track: int = 0,
        **kwargs
    ) -> PipelineResult:
        """
        Process video file through the pipeline.
        
        Args:
            video_path: Path to video file
            audio_track: Audio track index (default: 0)
            **kwargs: Additional options
            
        Returns:
            PipelineResult with full transcription and translation
        """
        start_time = time.time()
        
        try:
            # Extract audio
            self._report_progress(0.05, "Extracting audio from video...")
            audio_path = self.video_extractor.extract(
                video_path,
                audio_track=audio_track
            )
            
            # Get video duration
            duration = self.video_extractor.get_duration(video_path)
            
            # Transcribe
            self._report_progress(0.15, "Transcribing audio...")
            transcription = self.asr.transcribe(
                audio_path,
                language=self.source_lang,
                word_timestamps=True
            )
            
            # Update progress
            self._report_progress(0.6, "Translating text...")
            
            # Translate segments
            translated_segments = []
            total_segments = len(transcription.segments)
            
            for i, segment in enumerate(transcription.segments):
                # Translate segment
                translation = self.translator.translate(
                    segment.text,
                    self.source_lang,
                    self.target_lang
                )
                
                translated_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'source_text': segment.text,
                    'translated_text': translation.translated_text,
                    'words': segment.words
                })
                
                # Report progress
                progress = 0.6 + (0.35 * (i + 1) / total_segments)
                self._report_progress(
                    progress,
                    f"Translating segment {i+1}/{total_segments}..."
                )
            
            # Combine translated text
            full_translated = " ".join([
                s['translated_text'] for s in translated_segments
            ])
            
            processing_time = time.time() - start_time
            
            # Create result
            result = PipelineResult(
                source_audio=audio_path,
                source_duration=duration,
                transcription=transcription,
                source_text=transcription.text,
                source_language=transcription.language,
                translated_text=full_translated,
                target_language=self.target_lang,
                processing_time=processing_time,
                confidence=transcription.confidence
            )
            
            # Store segments for subtitle export
            result._translated_segments = translated_segments
            
            self._report_progress(1.0, "Complete!")
            
            return result
        
        except Exception as e:
            return PipelineResult(
                source_audio=video_path,
                errors=[str(e)],
                confidence=0.0
            )
    
    def process_with_segments(
        self,
        video_path: str,
        audio_track: int = 0,
        **kwargs
    ) -> List[PipelineResult]:
        """
        Process video and return results per segment.
        
        Args:
            video_path: Path to video file
            audio_track: Audio track index
            **kwargs: Additional options
            
        Returns:
            List of PipelineResult for each segment
        """
        # Extract audio with segments
        segments = self.video_extractor.extract_with_timestamps(
            video_path,
            segment_duration=self.segment_duration,
            overlap=self.overlap
        )
        
        results = []
        total = len(segments)
        
        for i, segment in enumerate(segments):
            self._report_progress(
                i / total,
                f"Processing segment {i+1}/{total}..."
            )
            
            # Process segment
            result = self._process_segment(segment)
            results.append(result)
        
        return results
    
    def _process_segment(self, segment: dict) -> PipelineResult:
        """Process a single video segment."""
        start_time = time.time()
        
        try:
            # Transcribe
            transcription = self.asr.transcribe(
                segment['audio_path'],
                language=self.source_lang
            )
            
            # Translate
            translation = self.translator.translate(
                transcription.text,
                self.source_lang,
                self.target_lang
            )
            
            processing_time = time.time() - start_time
            
            return PipelineResult(
                source_audio=segment['audio_path'],
                source_duration=segment['end'] - segment['start'],
                transcription=transcription,
                source_text=transcription.text,
                source_language=transcription.language,
                translated_text=translation.translated_text,
                target_language=self.target_lang,
                processing_time=processing_time,
                confidence=transcription.confidence
            )
        
        except Exception as e:
            return PipelineResult(
                source_audio=segment['audio_path'],
                errors=[str(e)],
                confidence=0.0
            )
    
    def batch_process(
        self,
        video_paths: List[str],
        **kwargs
    ) -> List[PipelineResult]:
        """
        Process multiple video files.
        
        Args:
            video_paths: List of video file paths
            **kwargs: Additional options
            
        Returns:
            List of PipelineResult objects
        """
        results = []
        total = len(video_paths)
        
        for i, path in enumerate(video_paths):
            self._report_progress(
                i / total,
                f"Processing video {i+1}/{total}: {Path(path).name}..."
            )
            
            result = self.process(path, **kwargs)
            results.append(result)
        
        self._report_progress(1.0, "All videos processed!")
        
        return results
    
    def process_stream(self, audio_stream, **kwargs):
        """Not supported for batch video translator."""
        raise NotImplementedError(
            "BatchVideoTranslator does not support streaming. "
            "Use RealtimeTranslator for streaming."
        )
