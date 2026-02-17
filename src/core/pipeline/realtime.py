"""Real-time translation pipeline."""

import time
import tempfile
import numpy as np
from typing import Iterator, Optional, Callable
from pathlib import Path

import soundfile as sf

from .base import TranslationPipeline, PipelineResult
from ..asr.base import BaseASR
from ..translation.base import BaseTranslator
from ..audio.vad import BaseVAD, SileroVAD, StreamingVAD, VADState


class RealtimeTranslator(TranslationPipeline):
    """
    Real-time speech-to-text translation pipeline.
    
    Processes audio chunks as they arrive, using VAD to detect
    speech segments and translate them.
    
    Example:
        >>> translator = RealtimeTranslator(
        ...     asr=whisper_cpp_asr,
        ...     translator=nllb_translator,
        ...     source_lang="zh",
        ...     target_lang="en"
        ... )
        >>> for result in translator.process_stream(audio_stream):
        ...     print(result.translated_text)
    """
    
    def __init__(
        self,
        asr: BaseASR,
        translator: BaseTranslator,
        source_lang: str,
        target_lang: str,
        vad: Optional[BaseVAD] = None,
        min_speech_duration: float = 1.0,
        min_silence_duration: float = 0.5,
        sample_rate: int = 16000,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        super().__init__(source_lang, target_lang, progress_callback)
        
        self.asr = asr
        self.translator = translator
        self.vad = vad or SileroVAD()
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        self.sample_rate = sample_rate
        
        # Initialize components
        if not asr.is_initialized:
            asr.initialize()
        if not translator.is_initialized:
            translator.initialize()
        
        # Streaming VAD
        self.streaming_vad = StreamingVAD(
            self.vad,
            min_speech_duration=min_speech_duration,
            min_silence_duration=min_silence_duration
        )
        
        # Audio buffer for continuous processing
        self._audio_buffer = []
        self._buffer_duration = 0
    
    def process(
        self,
        audio_path: str,
        **kwargs
    ) -> PipelineResult:
        """
        Process audio file (for non-streaming use).
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional options
            
        Returns:
            PipelineResult with full transcription and translation
        """
        start_time = time.time()
        
        try:
            # Transcribe
            self._report_progress(0.1, "Transcribing audio...")
            transcription = self.asr.transcribe(
                audio_path,
                language=self.source_lang
            )
            
            # Translate
            self._report_progress(0.6, "Translating text...")
            translation = self.translator.translate(
                transcription.text,
                self.source_lang,
                self.target_lang
            )
            
            processing_time = time.time() - start_time
            
            return PipelineResult(
                source_audio=audio_path,
                transcription=transcription,
                source_text=transcription.text,
                source_language=transcription.language,
                translation=translation,
                translated_text=translation.translated_text,
                target_language=self.target_lang,
                processing_time=processing_time,
                confidence=transcription.confidence * 0.9  # Combined confidence
            )
        
        except Exception as e:
            return PipelineResult(
                source_audio=audio_path,
                errors=[str(e)],
                confidence=0.0
            )
    
    def process_stream(
        self,
        audio_stream: Iterator[bytes],
        sample_rate: Optional[int] = None,
        **kwargs
    ) -> Iterator[PipelineResult]:
        """
        Process audio stream in real-time.
        
        Args:
            audio_stream: Iterator yielding audio chunks (PCM16 bytes)
            sample_rate: Audio sample rate (default: 16000)
            **kwargs: Additional options
            
        Yields:
            PipelineResult for each completed speech segment
        """
        sr = sample_rate or self.sample_rate
        self._is_running = True
        
        for audio_chunk in audio_stream:
            if not self._is_running:
                break
            
            # Convert bytes to numpy array
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Normalize to float [-1, 1]
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Process through VAD
            state, segment = self.streaming_vad.process(audio_float, sr)
            
            # If speech segment completed, process it
            if segment and state == VADState.SILENCE:
                result = self._process_segment(segment, audio_float)
                if result:
                    yield result
        
        # Flush any remaining speech
        remaining_segment = self.streaming_vad.flush()
        if remaining_segment:
            result = self._process_segment(remaining_segment, None)
            if result:
                yield result
        
        self._is_running = False
    
    def _process_segment(
        self,
        segment,
        audio_data: Optional[np.ndarray]
    ) -> Optional[PipelineResult]:
        """Process a speech segment through ASR and translation."""
        start_time = time.time()
        
        try:
            # Save segment to temp file
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as tmp:
                # Create segment audio
                if audio_data is not None:
                    sf.write(tmp.name, audio_data, self.sample_rate)
                tmp_path = tmp.name
            
            # Transcribe
            transcription = self.asr.transcribe(
                tmp_path,
                language=self.source_lang
            )
            
            # Skip if no speech detected
            if not transcription.text.strip():
                return None
            
            # Translate
            translation = self.translator.translate(
                transcription.text,
                self.source_lang,
                self.target_lang
            )
            
            processing_time = time.time() - start_time
            
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
            return PipelineResult(
                source_text=transcription.text,
                source_language=transcription.language,
                transcription=transcription,
                translated_text=translation.translated_text,
                target_language=self.target_lang,
                translation=translation,
                processing_time=processing_time,
                confidence=transcription.confidence
            )
        
        except Exception as e:
            return PipelineResult(
                errors=[str(e)],
                confidence=0.0
            )
    
    def process_microphone(
        self,
        callback: Callable[[PipelineResult], None],
        chunk_duration: float = 0.5,
        **kwargs
    ):
        """
        Process audio from microphone in real-time.
        
        Args:
            callback: Function to call with each translation result
            chunk_duration: Audio chunk duration in seconds
            **kwargs: Additional options
        """
        try:
            import sounddevice as sd
        except ImportError:
            raise ImportError(
                "sounddevice not installed. "
                "Run: pip install sounddevice"
            )
        
        chunk_samples = int(self.sample_rate * chunk_duration)
        
        def audio_callback(indata, frames, time_info, status):
            # Convert to bytes
            audio_bytes = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            
            # Process
            for result in self.process_stream(iter([audio_bytes])):
                callback(result)
        
        # Start recording
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.int16,
            blocksize=chunk_samples,
            callback=audio_callback
        ):
            self._report_progress(0, "Listening...")
            while self._is_running:
                time.sleep(0.1)
