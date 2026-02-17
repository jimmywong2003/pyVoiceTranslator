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
from collections import deque

# Audio components
from src.audio import AudioManager, AudioConfig, AudioSource
from src.audio.vad.silero_vad import SileroVADProcessor  # Base import

# Try to import improved VAD
try:
    from src.audio.vad.silero_vad_improved import (
        ImprovedSileroVADProcessor,
        create_vad_for_system_audio,
        create_vad_for_microphone
    )
    _HAS_IMPROVED_VAD = True
except ImportError:
    _HAS_IMPROVED_VAD = False

# ASR components
from src.core.asr.faster_whisper import FasterWhisperASR

# Translation components
from src.core.translation.marian import MarianTranslator
from src.core.translation.pivot import create_translator_with_pivot
from src.core.translation.cache import CachedTranslator, TranslationCache

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the translation pipeline."""
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 30
    audio_device_index: Optional[int] = None  # None for default
    audio_source: AudioSource = AudioSource.MICROPHONE  # MICROPHONE or SYSTEM_AUDIO
    
    # VAD settings
    vad_threshold: float = 0.5  # 0.5 for better sensitivity with system audio
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 400  # Increased for better sentence boundaries
    
    # Enhanced VAD buffering settings
    vad_lookback_ms: int = 500  # Pre-speech buffer to capture sentence beginnings (was 30ms)
    max_segment_duration_ms: int = 5000  # Max segment duration before forced split (5s for lower latency)
    pause_threshold_ms: int = 800  # Pause duration to trigger sentence boundary
    
    # Legacy compatibility
    max_segment_duration_s: float = 10.0  # Prevent overly long segments
    
    # Adaptive VAD settings (Phase 1)
    use_adaptive_vad: bool = True  # Enable adaptive VAD
    adaptive_vad_environment: str = "auto"  # "auto", "quiet", "office", "noisy"
    vad_min_threshold: float = 0.3  # Minimum adaptive threshold
    vad_max_threshold: float = 0.8  # Maximum adaptive threshold
    enable_vad_noise_estimation: bool = True
    enable_vad_energy_filter: bool = True  # Reduces CPU usage
    
    # ASR settings
    asr_model_size: str = "base"  # Changed from "tiny" to "base" for better accuracy
    asr_language: Optional[str] = None  # Auto-detect if None
    
    # ASR Deduplication settings
    enable_deduplication: bool = True
    dedup_window_size: int = 3  # Number of recent texts to compare against
    dedup_similarity_threshold: float = 0.85  # Similarity threshold (0-1)
    
    # Translation settings
    source_language: str = "en"
    target_language: str = "zh"
    translator_type: str = "marian"  # "marian" or "nllb"
    
    # Translation cache settings
    enable_translation_cache: bool = True
    translation_cache_size: int = 500
    translation_cache_ttl: Optional[int] = 3600  # 1 hour
    
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
    is_partial: bool = False  # True if this is part of a longer segment


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
        self._translator: Optional[CachedTranslator] = None
        
        # State
        self._is_running = False
        self._output_callback: Optional[Callable[[TranslationOutput], None]] = None
        self._processing_thread: Optional[threading.Thread] = None
        
        # Queue for audio segments
        self._segment_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        
        # Deduplication: store recent transcriptions
        self._recent_texts: deque = deque(maxlen=self.config.dedup_window_size)
        
        # Statistics
        self._stats = {
            "segments_processed": 0,
            "segments_deduped": 0,
            "translation_cache_hits": 0,
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
            
            # Try calibration-based VAD first (if enabled)
            if self.config.use_adaptive_vad:
                try:
                    from src.audio.vad.adaptive_vad_with_calibration import (
                        AdaptiveVADWithCalibration, CalibrationConfig,
                    )
                    
                    cal_config = CalibrationConfig(
                        calibration_duration=3.0,  # 3 seconds calibration
                        sample_rate=self.config.sample_rate,
                        base_threshold=self.config.vad_threshold,
                        min_speech_duration_ms=self.config.min_speech_duration_ms,
                        min_silence_duration_ms=self.config.min_silence_duration_ms,
                        speech_pad_ms=self.config.vad_lookback_ms,
                        max_segment_duration_ms=self.config.max_segment_duration_ms,
                    )
                    
                    self._vad = AdaptiveVADWithCalibration(cal_config)
                    logger.info(f"    ✅ Using CALIBRATION-BASED VAD: "
                               f"{cal_config.calibration_duration}s calibration, "
                               f"auto-threshold=True")
                    
                except ImportError as e:
                    logger.warning(f"    Calibration-based VAD not available ({e}), falling back to environment-aware VAD")
                    # Fallback to environment-aware
                    try:
                        from src.audio.vad.environment_aware_vad import (
                            EnvironmentAwareVADProcessor, EnvironmentAwareConfig,
                        )
                        env_config = EnvironmentAwareConfig(
                            sample_rate=self.config.sample_rate,
                            base_threshold=self.config.vad_threshold,
                            min_speech_duration_ms=self.config.min_speech_duration_ms,
                            min_silence_duration_ms=self.config.min_silence_duration_ms,
                            speech_pad_ms=self.config.vad_lookback_ms,
                            max_segment_duration_ms=self.config.max_segment_duration_ms,
                            min_threshold=self.config.vad_min_threshold,
                            max_threshold=self.config.vad_max_threshold,
                            enable_energy_prefilter=self.config.enable_vad_energy_filter,
                        )
                        self._vad = EnvironmentAwareVADProcessor(env_config)
                        logger.info(f"    ✅ Using ENVIRONMENT-AWARE VAD (fallback)")
                    except ImportError:
                        self.config.use_adaptive_vad = False
            
            # Fall back to improved VAD if adaptive not available or disabled
            if not self.config.use_adaptive_vad and _HAS_IMPROVED_VAD:
                self._vad = ImprovedSileroVADProcessor(
                    sample_rate=self.config.sample_rate,
                    threshold=self.config.vad_threshold,
                    min_speech_duration_ms=self.config.min_speech_duration_ms,
                    min_silence_duration_ms=self.config.min_silence_duration_ms,
                    speech_pad_ms=self.config.vad_lookback_ms,
                    max_segment_duration_ms=self.config.max_segment_duration_ms,
                    pause_threshold_ms=self.config.pause_threshold_ms
                )
                logger.info(f"    Using improved VAD: lookback={self.config.vad_lookback_ms}ms, "
                           f"max_duration={self.config.max_segment_duration_ms}ms")
            
            elif not self.config.use_adaptive_vad:
                # Fallback to legacy VAD
                logger.warning("    Using legacy VAD (improved VAD not available)")
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
                    # Use pivot translation if direct model not available
                    base_translator = create_translator_with_pivot(
                        source_lang=self.config.source_language,
                        target_lang=self.config.target_language,
                        device="auto"
                    )
                    base_translator.initialize()
                    
                    # Wrap with cache if enabled
                    if self.config.enable_translation_cache:
                        cache = TranslationCache(
                            max_size=self.config.translation_cache_size,
                            ttl=self.config.translation_cache_ttl
                        )
                        self._translator = CachedTranslator(base_translator, cache)
                        logger.info("    (with translation caching)")
                    else:
                        self._translator = base_translator
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
        
        # Process through VAD (may return single segment or list of segments)
        vad_result = self._vad.process_chunk(chunk)
        
        # Handle both legacy (single segment) and improved (list) VAD
        if vad_result is None:
            return
        
        segments = vad_result if isinstance(vad_result, list) else [vad_result]
        
        for segment in segments:
            try:
                self._segment_queue.put_nowait(segment)
                partial_marker = " (partial)" if getattr(segment, 'is_partial', False) else ""
                logger.debug(f"Added segment{partial_marker}: {segment.duration:.2f}s")
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
    
    def _is_duplicate(self, text: str) -> bool:
        """
        Check if text is similar to recent transcriptions.
        
        Uses simple word overlap ratio for similarity check.
        """
        if not self.config.enable_deduplication or not self._recent_texts:
            return False
        
        text_lower = text.lower().strip()
        text_words = set(text_lower.split())
        
        if not text_words:
            return False
        
        for recent_text in self._recent_texts:
            recent_words = set(recent_text.lower().split())
            
            # Calculate Jaccard similarity
            intersection = text_words & recent_words
            union = text_words | recent_words
            
            if union:
                similarity = len(intersection) / len(union)
                if similarity >= self.config.dedup_similarity_threshold:
                    logger.debug(f"Duplicate detected (similarity: {similarity:.2f}): '{text[:50]}...'")
                    return True
        
        return False
    
    def _add_to_history(self, text: str):
        """Add text to recent history for deduplication."""
        if self.config.enable_deduplication:
            self._recent_texts.append(text)
    
    def _is_hallucination(self, text: str) -> bool:
        """Check if text is likely a hallucination (repeated words)."""
        words = text.lower().split()
        if len(words) < 4:
            return False
        
        # Check for excessive repetition
        unique_words = set(words)
        if len(unique_words) < len(words) * 0.3:  # Less than 30% unique words
            return True
        
        # Check for specific patterns
        for word in unique_words:
            count = words.count(word)
            if count > len(words) * 0.5 and len(words) > 10:  # Word appears >50% of time
                return True
        
        return False
    
    def _process_segment(self, segment):
        """Process a single speech segment through ASR and Translation."""
        start_time = time.time()
        
        # Check max segment duration
        if segment.duration > self.config.max_segment_duration_s:
            logger.warning(f"Segment too long ({segment.duration:.1f}s), may cause slow processing")
        
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
                
                # Check for hallucinations (repeated words)
                if self._is_hallucination(source_text):
                    logger.warning(f"Hallucination detected, skipping: '{source_text[:80]}...'")
                    return
                
                # 2. Deduplication check
                if self._is_duplicate(source_text):
                    self._stats["segments_deduped"] += 1
                    logger.debug(f"Skipping duplicate: '{source_text[:50]}...'")
                    return
                
                # Add to history
                self._add_to_history(source_text)
                
                # 3. Translation (if enabled and needed)
                translated_text = None
                cache_hit = False
                if (self.config.enable_translation and 
                    self._translator and 
                    detected_language != self.config.target_language):
                    
                    # Check if result was from cache
                    if self.config.enable_translation_cache:
                        cache_before = self._translator.cache._hits
                    
                    trans_result = self._translator.translate(
                        source_text,
                        source_lang=detected_language,
                        target_lang=self.config.target_language
                    )
                    translated_text = trans_result.translated_text
                    
                    # Track cache hit
                    if self.config.enable_translation_cache:
                        if self._translator.cache._hits > cache_before:
                            cache_hit = True
                            self._stats["translation_cache_hits"] += 1
                
                # 4. Create output
                processing_time = (time.time() - start_time) * 1000
                
                output = TranslationOutput(
                    timestamp=time.time(),
                    source_text=source_text,
                    translated_text=translated_text,
                    source_language=detected_language,
                    target_language=self.config.target_language,
                    confidence=asr_result.confidence,
                    processing_time_ms=processing_time,
                    is_partial=getattr(segment, 'is_partial', False)
                )
                
                # 5. Send to callback
                if self._output_callback:
                    self._output_callback(output)
                
                # Update stats
                self._stats["segments_processed"] += 1
                self._stats["total_audio_duration"] += segment.duration
                self._stats["total_processing_time"] += processing_time
                
                cache_indicator = " [C]" if cache_hit else ""
                logger.info(
                    f"[{output.source_language}] {source_text} -> "
                    f"[{output.target_language}] {translated_text} "
                    f"({processing_time:.0f}ms){cache_indicator}"
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
    
    def stop(self, timeout: float = 5.0, process_final: bool = False):
        """
        Stop the translation pipeline.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
            process_final: Whether to process the final VAD segment (may be slow)
        """
        if not self._is_running:
            return
        
        logger.info("Stopping translation pipeline...")
        self._is_running = False
        
        # Stop audio capture first (prevents new data)
        if self._audio_manager:
            try:
                self._audio_manager.stop_capture()
            except Exception as e:
                logger.warning(f"Error stopping audio capture: {e}")
        
        # Wait for processing thread with timeout
        if self._processing_thread and self._processing_thread.is_alive():
            logger.debug("Waiting for processing thread to stop...")
            self._processing_thread.join(timeout=timeout)
            if self._processing_thread.is_alive():
                logger.warning("Processing thread did not stop in time")
        
        # Finalize any pending VAD segment (optional, can be slow)
        if process_final and self._vad:
            try:
                final_segment = self._vad.force_finalize()
                if final_segment:
                    logger.info(f"Processing final segment: {final_segment.duration:.2f}s")
                    # Process final segment with timeout protection
                    import threading
                    result = [None]
                    def process_with_timeout():
                        try:
                            self._process_segment(final_segment)
                            result[0] = True
                        except Exception as e:
                            logger.error(f"Error processing final segment: {e}")
                            result[0] = False
                    
                    final_thread = threading.Thread(target=process_with_timeout)
                    final_thread.start()
                    final_thread.join(timeout=3.0)  # Max 3 seconds for final segment
                    
                    if final_thread.is_alive():
                        logger.warning("Final segment processing timed out, skipping")
            except Exception as e:
                logger.warning(f"Error finalizing VAD segment: {e}")
        
        # Clear any remaining queue items
        if self._segment_queue:
            try:
                while not self._segment_queue.empty():
                    self._segment_queue.get_nowait()
            except:
                pass
        
        logger.info("✅ Translation pipeline stopped")
        self._print_stats()
    
    def _print_stats(self):
        """Print pipeline statistics."""
        if self._stats["start_time"]:
            runtime = time.time() - self._stats["start_time"]
            print(f"\n📊 Pipeline Statistics:")
            print(f"   Runtime: {runtime:.1f}s")
            print(f"   Segments processed: {self._stats['segments_processed']}")
            if self._stats["segments_deduped"] > 0:
                print(f"   Segments deduplicated: {self._stats['segments_deduped']}")
            if self._stats["translation_cache_hits"] > 0:
                print(f"   Translation cache hits: {self._stats['translation_cache_hits']}")
            print(f"   Total audio duration: {self._stats['total_audio_duration']:.1f}s")
            if self._stats["segments_processed"] > 0:
                avg_time = self._stats["total_processing_time"] / self._stats["segments_processed"]
                print(f"   Avg processing time: {avg_time:.0f}ms")
            
            # Print adaptive VAD stats if available
            if self.config.use_adaptive_vad and hasattr(self._vad, 'print_summary'):
                try:
                    self._vad.print_summary()
                except Exception as e:
                    logger.debug(f"Could not print VAD summary: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._is_running
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return self._stats.copy()
