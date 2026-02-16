"""
End-to-End Translation Pipeline Orchestrator

Coordinates audio capture, VAD, ASR, and translation into a real-time pipeline.
"""

import time
import threading
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from queue import Queue, Empty
import numpy as np
import tempfile
import os

# Audio components
from audio_module import AudioManager, AudioConfig, AudioSource
from audio_module.vad.silero_vad import SileroVADProcessor

# ASR components
from voice_translation.src.asr.faster_whisper import FasterWhisperASR

# Translation components
from voice_translation.src.translation.marian import MarianTranslator

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the translation pipeline."""
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 30
    audio_device_index: Optional[int] = None  # None for default
    
    # VAD settings
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 250
    
    # ASR settings
    asr_model_size: str = "tiny"  # tiny, base, small
    asr_language: Optional[str] = None  # Auto-detect if None
    
    # Translation settings
    source_language: str = "en"
    target_language: str = "zh"
    translator_type: str = "marian"  # "marian" or "nllb"
    
    # Pipeline settings
    max_queue_size: int = 10
    enable_translation: bool = True


@dataclass
class TranslationOutput:
    """Output from the translation pipeline."""
    timestamp: float
    source_text: str
    translated_text: Optional[str]
    source_language: str
    target_language: str
    confidence: float
    processing_time_ms: float


class TranslationPipeline:
    """
    End-to-end real-time translation pipeline.
    
    Connects audio capture → VAD → ASR → Translation → Output
    
    Usage:
        config = PipelineConfig(source_language="en", target_language="zh")
        pipeline = TranslationPipeline(config)
        
        def on_output(output: TranslationOutput):
            print(f"{output.source_text} -> {output.translated_text}")
        
        pipeline.start(on_output)
        # ... run for some time ...
        pipeline.stop()
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the translation pipeline."""
        self.config = config or PipelineConfig()
        
        # Components
        self._audio_manager: Optional[AudioManager] = None
        self._vad: Optional[SileroVADProcessor] = None
        self._asr: Optional[FasterWhisperASR] = None
        self._translator: Optional[MarianTranslator] = None
        
        # State
        self._is_running = False
        self._output_callback: Optional[Callable[[TranslationOutput], None]] = None
        self._processing_thread: Optional[threading.Thread] = None
        
        # Queue for audio segments
        self._segment_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        
        # Statistics
        self._stats = {
            "segments_processed": 0,
            "total_audio_duration": 0.0,
            "total_processing_time": 0.0,
            "start_time": None
        }
        
        logger.info("TranslationPipeline initialized")
    
    def initialize(self) -> bool:
        """Initialize all pipeline components."""
        try:
            logger.info("Initializing pipeline components...")
            
            # 1. Initialize Audio Manager
            logger.info("  - Audio Manager...")
            audio_config = AudioConfig(
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                chunk_duration_ms=self.config.chunk_duration_ms
            )
            self._audio_manager = AudioManager(audio_config)
            
            # 2. Initialize VAD
            logger.info("  - VAD Processor...")
            self._vad = SileroVADProcessor(
                sample_rate=self.config.sample_rate,
                threshold=self.config.vad_threshold,
                min_speech_duration_ms=self.config.min_speech_duration_ms
            )
            
            # 3. Initialize ASR
            logger.info(f"  - ASR ({self.config.asr_model_size})...")
            self._asr = FasterWhisperASR(
                model_size=self.config.asr_model_size,
                device="cpu",
                compute_type="int8",
                language=self.config.asr_language
            )
            self._asr.initialize()
            
            # 4. Initialize Translator (if enabled)
            if self.config.enable_translation:
                logger.info(f"  - Translator ({self.config.translator_type})...")
                if self.config.translator_type == "marian":
                    self._translator = MarianTranslator(
                        source_lang=self.config.source_language,
                        target_lang=self.config.target_language,
                        device="auto"
                    )
                    self._translator.initialize()
                else:
                    # Fallback to NLLB or raise error
                    raise NotImplementedError("NLLB translator not yet integrated")
            
            logger.info("✅ Pipeline initialization complete!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            return False
    
    def _audio_callback(self, chunk: np.ndarray):
        """Process audio chunk from capture."""
        if not self._is_running:
            return
        
        # Process through VAD
        vad_segment = self._vad.process_chunk(chunk)
        
        if vad_segment:
            # Speech segment detected, add to queue
            try:
                self._segment_queue.put_nowait(vad_segment)
                logger.debug(f"Added segment: {vad_segment.duration:.2f}s")
            except:
                logger.warning("Segment queue full, dropping segment")
    
    def _processing_loop(self):
        """Main processing loop (runs in separate thread)."""
        logger.info("Processing loop started")
        
        while self._is_running:
            try:
                # Get segment from queue
                segment = self._segment_queue.get(timeout=0.1)
                self._process_segment(segment)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing segment: {e}")
        
        logger.info("Processing loop stopped")
    
    def _process_segment(self, segment):
        """Process a single speech segment through ASR and Translation."""
        start_time = time.time()
        
        try:
            # Save segment to temp file for ASR
            import soundfile as sf
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, segment.audio_data, self.config.sample_rate)
                audio_path = tmp.name
            
            try:
                # 1. ASR Transcription
                asr_result = self._asr.transcribe(
                    audio_path,
                    language=self.config.asr_language
                )
                
                if not asr_result.text.strip():
                    logger.debug("Empty transcription, skipping")
                    return
                
                source_text = asr_result.text.strip()
                detected_language = asr_result.language
                
                # 2. Translation (if enabled and needed)
                translated_text = None
                if (self.config.enable_translation and 
                    self._translator and 
                    detected_language != self.config.target_language):
                    
                    trans_result = self._translator.translate(
                        source_text,
                        source_lang=detected_language,
                        target_lang=self.config.target_language
                    )
                    translated_text = trans_result.translated_text
                
                # 3. Create output
                processing_time = (time.time() - start_time) * 1000
                
                output = TranslationOutput(
                    timestamp=time.time(),
                    source_text=source_text,
                    translated_text=translated_text,
                    source_language=detected_language,
                    target_language=self.config.target_language,
                    confidence=asr_result.confidence,
                    processing_time_ms=processing_time
                )
                
                # 4. Send to callback
                if self._output_callback:
                    self._output_callback(output)
                
                # Update stats
                self._stats["segments_processed"] += 1
                self._stats["total_audio_duration"] += segment.duration
                self._stats["total_processing_time"] += processing_time
                
                logger.info(
                    f"[{output.source_language}] {source_text} -> "
                    f"[{output.target_language}] {translated_text} "
                    f"({processing_time:.0f}ms)"
                )
                
            finally:
                os.unlink(audio_path)
                
        except Exception as e:
            logger.error(f"Error in segment processing: {e}")
    
    def start(
        self,
        output_callback: Callable[[TranslationOutput], None],
        audio_source: AudioSource = AudioSource.MICROPHONE,
        device_index: Optional[int] = None
    ) -> bool:
        """
        Start the translation pipeline.
        
        Args:
            output_callback: Function to call with translation output
            audio_source: Audio source (microphone or system audio)
            device_index: Specific audio device index
            
        Returns:
            True if started successfully
        """
        if self._is_running:
            logger.warning("Pipeline already running")
            return False
        
        # Initialize if needed
        if not self._asr or not self._asr.is_initialized:
            if not self.initialize():
                return False
        
        self._output_callback = output_callback
        self._is_running = True
        self._stats["start_time"] = time.time()
        
        # Start processing thread
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            name="PipelineProcessor",
            daemon=True
        )
        self._processing_thread.start()
        
        # Start audio capture
        success = self._audio_manager.start_capture(
            audio_source,
            self._audio_callback,
            device_index=device_index
        )
        
        if not success:
            self._is_running = False
            logger.error("Failed to start audio capture")
            return False
        
        logger.info("✅ Translation pipeline started!")
        return True
    
    def stop(self):
        """Stop the translation pipeline."""
        if not self._is_running:
            return
        
        logger.info("Stopping translation pipeline...")
        self._is_running = False
        
        # Stop audio capture
        if self._audio_manager:
            self._audio_manager.stop_capture()
        
        # Wait for processing thread
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # Finalize any pending VAD segment
        if self._vad:
            final_segment = self._vad.force_finalize()
            if final_segment:
                self._process_segment(final_segment)
        
        logger.info("✅ Translation pipeline stopped")
        self._print_stats()
    
    def _print_stats(self):
        """Print pipeline statistics."""
        if self._stats["start_time"]:
            runtime = time.time() - self._stats["start_time"]
            print(f"\n📊 Pipeline Statistics:")
            print(f"   Runtime: {runtime:.1f}s")
            print(f"   Segments processed: {self._stats['segments_processed']}")
            print(f"   Total audio duration: {self._stats['total_audio_duration']:.1f}s")
            if self._stats["segments_processed"] > 0:
                avg_time = self._stats["total_processing_time"] / self._stats["segments_processed"]
                print(f"   Avg processing time: {avg_time:.0f}ms")
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._is_running
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return self._stats.copy()
