"""
Parallel Translation Pipeline with ThreadPoolExecutor

Implements Option 1: Pipeline Parallelism with Overlap
- Stage 1: Audio Capture (dedicated thread)
- Stage 2: VAD Processing (dedicated thread)
- Stage 3: ASR Processing (ThreadPool, 2 workers)
- Stage 4: Translation (overlaps with next ASR)
- Stage 5: Output (dedicated thread)

Key Optimizations:
1. ASR and Translation overlap (major latency reduction)
2. Multiple ASR workers (throughput improvement)
3. Bounded queues (memory management)
4. Non-blocking pipeline (prevents head-of-line blocking)
"""

import time
import threading
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from queue import Queue, Empty, Full
from concurrent.futures import ThreadPoolExecutor, Future
from collections import deque
import numpy as np

# Import existing components
from .orchestrator import (
    TranslationPipeline, 
    PipelineConfig, 
    TranslationOutput,
    AudioSource
)
from src.audio import AudioManager, AudioConfig
from src.audio.vad.environment_aware_vad import EnvironmentAwareVADProcessor, EnvironmentAwareConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineSegment:
    """Segment data passed between pipeline stages."""
    segment_id: int
    audio_data: np.ndarray
    start_time: float
    vad_confidence: float = 0.0
    asr_result: Optional[object] = None
    translation_result: Optional[str] = None
    asr_start_time: Optional[float] = None
    asr_end_time: Optional[float] = None
    translation_start_time: Optional[float] = None
    translation_end_time: Optional[float] = None
    is_partial: bool = False


@dataclass
class ParallelPipelineMetrics:
    """Metrics for parallel pipeline performance."""
    total_segments: int = 0
    queued_segments: int = 0
    asr_in_progress: int = 0
    translation_in_progress: int = 0
    completed_segments: int = 0
    
    # Timing
    avg_asr_time_ms: float = 0.0
    avg_translation_time_ms: float = 0.0
    avg_total_time_ms: float = 0.0
    
    # Overlap efficiency
    overlap_savings_ms: float = 0.0
    
    def to_dict(self):
        return {
            'total_segments': self.total_segments,
            'queued_segments': self.queued_segments,
            'asr_in_progress': self.asr_in_progress,
            'translation_in_progress': self.translation_in_progress,
            'completed_segments': self.completed_segments,
            'avg_asr_time_ms': self.avg_asr_time_ms,
            'avg_translation_time_ms': self.avg_translation_time_ms,
            'avg_total_time_ms': self.avg_total_time_ms,
            'overlap_savings_ms': self.overlap_savings_ms,
        }


class ParallelTranslationPipeline(TranslationPipeline):
    """
    Parallel translation pipeline with ThreadPoolExecutor.
    
    Architecture:
    - Audio Thread: Captures audio, minimal processing
    - VAD Thread: Detects speech segments
    - ASR ThreadPool: 2 workers for parallel ASR
    - Translation Thread: Handles translation (overlaps with ASR)
    - Output Thread: Calls user callback
    
    Key Feature: ASR[i] and Translation[i-1] run in parallel,
    reducing effective latency from (ASR + Translation) to max(ASR, Translation).
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize parallel pipeline."""
        super().__init__(config)
        
        # ThreadPool for ASR (2 workers for dual-core systems)
        self._asr_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="ASRWorker"
        )
        
        # Dedicated translation executor (1 worker)
        self._translation_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="TranslationWorker"
        )
        
        # Bounded queues between stages
        self._vad_queue: Queue = Queue(maxsize=10)      # Audio → VAD
        self._asr_queue: Queue = Queue(maxsize=10)      # VAD → ASR (increased from 5)
        self._translation_queue: Queue = Queue(maxsize=5)  # ASR → Translation
        self._output_queue: Queue = Queue(maxsize=20)   # Translation → Output
        
        # Worker threads
        self._vad_thread: Optional[threading.Thread] = None
        self._asr_thread: Optional[threading.Thread] = None
        self._output_thread: Optional[threading.Thread] = None
        
        # Tracking
        self._segment_counter = 0
        self._in_flight_segments: dict = {}  # segment_id → Future
        self._metrics = ParallelPipelineMetrics()
        self._metrics_lock = threading.Lock()
        
        # Overlap optimization
        self._previous_translation_future: Optional[Future] = None
        self._previous_segment_id: Optional[int] = None
        
        logger.info("ParallelTranslationPipeline initialized (2 ASR workers, overlap enabled)")
    
    def initialize(self) -> bool:
        """Initialize all pipeline components."""
        try:
            logger.info("Initializing parallel pipeline components...")
            
            # 1. Audio Manager
            logger.info("  - Audio Manager...")
            audio_config = AudioConfig(
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                chunk_duration_ms=self.config.chunk_duration_ms
            )
            self._audio_manager = AudioManager(audio_config)
            
            # 2. VAD (Calibration-based if enabled)
            logger.info("  - VAD Processor...")
            if self.config.use_adaptive_vad:
                try:
                    from src.audio.vad.adaptive_vad_with_calibration import (
                        AdaptiveVADWithCalibration, CalibrationConfig
                    )
                    cal_config = CalibrationConfig(
                        calibration_duration=3.0,
                        sample_rate=self.config.sample_rate,
                        base_threshold=self.config.vad_threshold,
                        min_speech_duration_ms=self.config.min_speech_duration_ms,
                        min_silence_duration_ms=self.config.min_silence_duration_ms,
                        speech_pad_ms=self.config.vad_lookback_ms,
                        max_segment_duration_ms=self.config.max_segment_duration_ms,
                    )
                    self._vad = AdaptiveVADWithCalibration(cal_config)
                    logger.info("    ✅ Using CALIBRATION-BASED VAD with parallel support (3s calibration)")
                except ImportError:
                    logger.warning("    Calibration-based VAD not available, using environment-aware VAD")
                    self._vad = self._create_environment_aware_vad()
            else:
                self._vad = self._create_improved_vad()
            
            # 3. ASR (already initialized in parent)
            logger.info(f"  - ASR ({self.config.asr_model_size})...")
            if not self._asr or not self._asr.is_initialized:
                from src.core.asr.faster_whisper import FasterWhisperASR
                self._asr = FasterWhisperASR(
                    model_size=self.config.asr_model_size,
                    device="cpu",
                    compute_type="int8",
                    language=self.config.asr_language
                )
                self._asr.initialize()
            
            # 4. Translator (already initialized in parent)
            if self.config.enable_translation:
                logger.info(f"  - Translator ({self.config.translator_type})...")
                if not self._translator:
                    self._initialize_translator()
            
            logger.info("✅ Parallel pipeline initialization complete!")
            logger.info(f"   ASR Workers: 2 (ThreadPool + Queue) | Translation Workers: 1 | Overlap: Enabled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize parallel pipeline: {e}")
            return False
    
    def _create_improved_vad(self):
        """Create improved VAD as fallback."""
        from src.audio.vad.silero_vad_improved import ImprovedSileroVADProcessor
        return ImprovedSileroVADProcessor(
            sample_rate=self.config.sample_rate,
            threshold=self.config.vad_threshold,
            min_speech_duration_ms=self.config.min_speech_duration_ms,
            min_silence_duration_ms=self.config.min_silence_duration_ms,
            speech_pad_ms=self.config.vad_lookback_ms,
            max_segment_duration_ms=self.config.max_segment_duration_ms,
            pause_threshold_ms=self.config.pause_threshold_ms
        )
    
    def _create_environment_aware_vad(self):
        """Create environment-aware VAD as second fallback."""
        try:
            from src.audio.vad.environment_aware_vad import (
                EnvironmentAwareVADProcessor, EnvironmentAwareConfig
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
            logger.info("    ✅ Using ENVIRONMENT-AWARE VAD (fallback)")
            return EnvironmentAwareVADProcessor(env_config)
        except ImportError:
            logger.warning("    Environment-aware VAD not available, using improved VAD")
            return self._create_improved_vad()
    
    def _initialize_translator(self):
        """Initialize translator."""
        from src.core.translation.marian import MarianTranslator
        from src.core.translation.cache import CachedTranslator, TranslationCache
        
        base_translator = MarianTranslator(
            source_lang=self.config.source_language,
            target_lang=self.config.target_language,
            device="auto"
        )
        base_translator.initialize()
        
        if self.config.enable_translation_cache:
            cache = TranslationCache(
                max_size=self.config.translation_cache_size,
                ttl=self.config.translation_cache_ttl
            )
            self._translator = CachedTranslator(base_translator, cache)
        else:
            self._translator = base_translator
    
    def start(self, output_callback: Callable[[TranslationOutput], None],
              audio_source: AudioSource = AudioSource.MICROPHONE,
              device_index: Optional[int] = None) -> bool:
        """Start the parallel pipeline."""
        if self._is_running:
            logger.warning("Pipeline already running")
            return False
        
        if not self._asr or not self._asr.is_initialized:
            if not self.initialize():
                return False
        
        self._output_callback = output_callback
        self._is_running = True
        self._stats["start_time"] = time.time()
        
        # Start worker threads
        self._vad_thread = threading.Thread(target=self._vad_worker, name="VADWorker")
        self._asr_thread = threading.Thread(target=self._asr_worker, name="ASRWorker")
        self._output_thread = threading.Thread(target=self._output_worker, name="OutputWorker")
        
        self._vad_thread.start()
        self._asr_thread.start()
        self._output_thread.start()
        
        # Start audio capture
        success = self._audio_manager.start_capture(
            audio_source,
            self._audio_callback,
            device_index=device_index
        )
        
        if not success:
            self._is_running = False
            return False
        
        logger.info("✅ Parallel translation pipeline started!")
        logger.info("   Architecture: Audio→VAD→ASR(2x)→Translation→Output")
        logger.info("   Optimization: ASR[i] overlaps with Translation[i-1]")
        return True
    
    def _audio_callback(self, chunk: np.ndarray):
        """Audio capture callback (runs in audio thread)."""
        if not self._is_running:
            return
        
        # Non-blocking queue put
        try:
            self._vad_queue.put_nowait(chunk)
        except Full:
            logger.warning("VAD queue full, dropping audio chunk")
    
    def _vad_worker(self):
        """VAD processing worker (dedicated thread)."""
        logger.info("VAD worker started")
        
        while self._is_running:
            try:
                # Get audio chunk with timeout
                chunk = self._vad_queue.get(timeout=0.1)
                
                # Process through VAD
                segments = self._vad.process_chunk(chunk)
                
                # Queue segments for ASR
                for segment in segments:
                    self._segment_counter += 1
                    
                    pipeline_segment = PipelineSegment(
                        segment_id=self._segment_counter,
                        audio_data=segment.audio_data,
                        start_time=time.time(),
                        vad_confidence=segment.confidence,
                        is_partial=getattr(segment, 'is_partial', False)
                    )
                    
                    try:
                        self._asr_queue.put_nowait(pipeline_segment)
                        with self._metrics_lock:
                            self._metrics.total_segments += 1
                            self._metrics.queued_segments = self._asr_queue.qsize()
                        logger.debug(f"Queued segment {self._segment_counter} for ASR (queue: {self._asr_queue.qsize()})")
                    except Full:
                        logger.warning(f"ASR queue full, dropping segment {self._segment_counter}")
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"VAD worker error: {e}")
        
        logger.info("VAD worker stopped")
    
    def _asr_worker(self):
        """ASR worker (dedicated thread - submits to ThreadPool)."""
        logger.info("ASR worker started")
        
        while self._is_running:
            try:
                # Get segment from VAD queue
                segment = self._asr_queue.get(timeout=0.1)
                
                # Submit to ASR executor
                future = self._asr_executor.submit(self._process_asr, segment)
                
                # Add completion callback
                future.add_done_callback(self._on_asr_complete)
                
                with self._metrics_lock:
                    self._metrics.asr_in_progress += 1
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"ASR worker error: {e}")
        
        logger.info("ASR worker stopped")
    
    def _is_asr_hallucination(self, text: str) -> bool:
        """
        Detect ASR hallucinations like repetition patterns.
        
        Returns True if text is likely a hallucination.
        """
        if not text or len(text) < 5:
            return False
        
        # Pattern 1: Character repetition (e.g., "夜の夜の夜の...")
        # Detect same character/substring repeated many times
        for length in range(1, min(10, len(text) // 3)):
            for i in range(len(text) - length * 3):
                pattern = text[i:i+length]
                if len(pattern.strip()) == 0:
                    continue
                # Check if pattern repeats 4+ times
                count = 0
                pos = i
                while pos < len(text) and text[pos:pos+length] == pattern:
                    count += 1
                    pos += length
                if count >= 4:  # Pattern repeats 4+ times
                    logger.warning(f"ASR hallucination detected: repetition of '{pattern}' {count} times")
                    return True
        
        # Pattern 2: Excessive repetition of same word
        words = text.split()
        if len(words) >= 5:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            # If any word appears >50% of time, it's likely hallucination
            max_count = max(word_counts.values())
            if max_count / len(words) > 0.5:
                most_common = max(word_counts.keys(), key=lambda w: word_counts[w])
                logger.warning(f"ASR hallucination detected: word '{most_common}' appears {max_count}/{len(words)} times")
                return True
        
        # Pattern 3: Very long repetitive sequences
        if len(text) > 100:
            # Check for repeating 2-4 character sequences
            for seq_len in range(2, 5):
                sequences = [text[i:i+seq_len] for i in range(0, len(text)-seq_len, seq_len)]
                if len(sequences) >= 10:
                    unique_ratio = len(set(sequences)) / len(sequences)
                    if unique_ratio < 0.3:  # Less than 30% unique sequences
                        logger.warning(f"ASR hallucination detected: low diversity ({unique_ratio:.1%}) in long text")
                        return True
        
        return False
    
    def _process_asr(self, segment: PipelineSegment) -> PipelineSegment:
        """Process ASR (runs in ThreadPool)."""
        segment.asr_start_time = time.time()
        
        try:
            import tempfile
            import soundfile as sf
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, segment.audio_data, self.config.sample_rate)
                audio_path = tmp.name
            
            # ASR transcription
            asr_result = self._asr.transcribe(
                audio_path,
                language=self.config.asr_language
            )
            
            segment.asr_end_time = time.time()
            
            # Check for hallucinations
            if asr_result and asr_result.text.strip():
                if self._is_asr_hallucination(asr_result.text):
                    logger.warning(f"ASR segment {segment.segment_id}: Rejected hallucination: '{asr_result.text[:50]}...'")
                    asr_result.text = ""  # Clear the text
            
            segment.asr_result = asr_result
            
            # Log ASR result
            asr_time = (segment.asr_end_time - segment.asr_start_time) * 1000
            if asr_result and asr_result.text.strip():
                logger.info(f"ASR segment {segment.segment_id}: '{asr_result.text[:50]}...' ({asr_time:.0f}ms)")
            else:
                logger.warning(f"ASR segment {segment.segment_id}: Empty result ({asr_time:.0f}ms)")
            
            # Cleanup
            import os
            os.unlink(audio_path)
            
        except Exception as e:
            logger.error(f"ASR error for segment {segment.segment_id}: {e}")
        
        return segment
    
    def _process_translation(self, segment: PipelineSegment) -> PipelineSegment:
        """Process translation (runs in ThreadPool)."""
        if not self.config.enable_translation or not self._translator:
            return segment
        
        if not segment.asr_result or not segment.asr_result.text.strip():
            return segment
        
        segment.translation_start_time = time.time()
        
        try:
            trans_result = self._translator.translate(
                segment.asr_result.text,
                source_lang=segment.asr_result.language or self.config.source_language,
                target_lang=self.config.target_language
            )
            segment.translation_result = trans_result.translated_text
            segment.translation_end_time = time.time()
            
            # Log translation result
            trans_time = (segment.translation_end_time - segment.translation_start_time) * 1000
            logger.info(f"Translation segment {segment.segment_id}: '{segment.asr_result.text[:30]}...' -> '{segment.translation_result[:30]}...' ({trans_time:.0f}ms)")
            
        except Exception as e:
            logger.error(f"Translation error for segment {segment.segment_id}: {e}")
        
        return segment
    
    def _submit_asr_task(self, segment: PipelineSegment):
        """Submit ASR task to thread pool."""
        future = self._asr_executor.submit(self._process_asr, segment)
        
        # Add callback for when ASR completes
        future.add_done_callback(self._on_asr_complete)
        
        with self._metrics_lock:
            self._metrics.asr_in_progress += 1
        
        return future
    
    def _on_asr_complete(self, future: Future):
        """Callback when ASR completes."""
        try:
            segment = future.result()
            
            with self._metrics_lock:
                self._metrics.asr_in_progress -= 1
            
            # Submit to translation queue
            try:
                self._translation_queue.put_nowait(segment)
            except Full:
                logger.warning("Translation queue full, processing inline")
                self._process_translation_async(segment)
            
        except Exception as e:
            logger.error(f"ASR completion error: {e}")
    
    def _process_translation_async(self, segment: PipelineSegment):
        """Submit translation task asynchronously."""
        # Check if previous translation is still running
        # If so, we'll chain them (sequential translation is safer)
        if self._previous_translation_future and not self._previous_translation_future.done():
            # Wait for previous to complete (maintains order)
            self._previous_translation_future.result()
        
        # Submit new translation
        trans_future = self._translation_executor.submit(
            self._process_translation, segment
        )
        
        # Add completion callback
        trans_future.add_done_callback(
            lambda f, seg=segment: self._on_translation_complete(f, seg)
        )
        
        self._previous_translation_future = trans_future
        
        with self._metrics_lock:
            self._metrics.translation_in_progress += 1
    
    def _on_translation_complete(self, future: Future, segment: PipelineSegment):
        """Callback when translation completes."""
        try:
            completed_segment = future.result()
            
            with self._metrics_lock:
                self._metrics.translation_in_progress -= 1
                self._metrics.completed_segments += 1
            
            # Queue for output
            try:
                self._output_queue.put_nowait(completed_segment)
            except Full:
                logger.warning("Output queue full, dropping segment")
            
        except Exception as e:
            logger.error(f"Translation completion error: {e}")
    
    def _output_worker(self):
        """Output worker (dedicated thread)."""
        logger.info("Output worker started")
        
        while self._is_running:
            try:
                segment = self._output_queue.get(timeout=0.1)
                self._emit_output(segment)
                
            except Empty:
                # Check for completed translations that need async processing
                self._check_translation_queue()
                continue
            except Exception as e:
                logger.error(f"Output worker error: {e}")
        
        logger.info("Output worker stopped")
    
    def _check_translation_queue(self):
        """Check for segments ready for translation."""
        try:
            while True:
                segment = self._translation_queue.get_nowait()
                self._process_translation_async(segment)
        except Empty:
            pass
    
    def _emit_output(self, segment: PipelineSegment):
        """Emit translation output."""
        if not self._output_callback:
            return
        
        if not segment.asr_result or not segment.asr_result.text.strip():
            return
        
        # Calculate timing
        total_time = (time.time() - segment.start_time) * 1000
        asr_time = (segment.asr_end_time - segment.asr_start_time) * 1000 if segment.asr_end_time else 0
        trans_time = (segment.translation_end_time - segment.translation_start_time) * 1000 if segment.translation_end_time else 0
        
        # Calculate overlap savings
        # Without overlap: ASR_time + Translation_time
        # With overlap: max(ASR_time, Translation_time) + overhead
        sequential_time = asr_time + trans_time
        overlap_savings = sequential_time - total_time
        
        with self._metrics_lock:
            self._metrics.avg_asr_time_ms = (
                0.9 * self._metrics.avg_asr_time_ms + 0.1 * asr_time
            )
            self._metrics.avg_translation_time_ms = (
                0.9 * self._metrics.avg_translation_time_ms + 0.1 * trans_time
            )
            self._metrics.avg_total_time_ms = (
                0.9 * self._metrics.avg_total_time_ms + 0.1 * total_time
            )
            if overlap_savings > 0:
                self._metrics.overlap_savings_ms = (
                    0.9 * self._metrics.overlap_savings_ms + 0.1 * overlap_savings
                )
        
        # Create output
        output = TranslationOutput(
            timestamp=time.time(),
            source_text=segment.asr_result.text,
            translated_text=segment.translation_result if self.config.enable_translation else None,
            source_language=segment.asr_result.language or self.config.source_language,
            target_language=self.config.target_language,
            confidence=segment.asr_result.confidence,
            processing_time_ms=total_time,
            is_partial=segment.is_partial
        )
        
        # Call user callback
        try:
            self._output_callback(output)
            logger.info(f"Output emitted: '{output.source_text[:40]}...' -> '{(output.translated_text or '')[:40]}...' ({total_time:.0f}ms)")
        except Exception as e:
            logger.error(f"Output callback error: {e}")
        
        # Update stats
        self._stats["segments_processed"] += 1
        self._stats["total_audio_duration"] += len(segment.audio_data) / self.config.sample_rate
        self._stats["total_processing_time"] += total_time
    
    def stop(self, timeout: float = 5.0, process_final: bool = True):
        """Stop the parallel pipeline.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
            process_final: If True, process remaining items in queues before stopping
        """
        if not self._is_running:
            return
        
        logger.info("Stopping parallel pipeline...")
        self._is_running = False
        
        # Stop audio capture
        if self._audio_manager:
            self._audio_manager.stop_capture()
        
        # Wait for threads
        if self._vad_thread and self._vad_thread.is_alive():
            self._vad_thread.join(timeout=timeout)
        
        if self._asr_thread and self._asr_thread.is_alive():
            self._asr_thread.join(timeout=timeout)
        
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=timeout)
        
        # Shutdown executors
        self._asr_executor.shutdown(wait=False)
        self._translation_executor.shutdown(wait=False)
        
        # Process remaining items in queues if requested
        if process_final:
            self._drain_queues()
        
        logger.info("✅ Parallel pipeline stopped")
        self._print_parallel_stats()
    
    def _drain_queues(self):
        """Process remaining items in queues."""
        # Drain output queue
        try:
            while True:
                segment = self._output_queue.get_nowait()
                self._emit_output(segment)
        except Empty:
            pass
    
    def _print_parallel_stats(self):
        """Print parallel pipeline statistics."""
        super()._print_stats()
        
        print("\n📊 Parallel Pipeline Metrics:")
        print(f"   ASR Workers: 2")
        print(f"   Translation Workers: 1")
        print(f"   Overlap Optimization: Enabled")
        
        with self._metrics_lock:
            print(f"   Avg Overlap Savings: {self._metrics.overlap_savings_ms:.0f}ms")
            print(f"   Effective Latency Reduction: ~{self._metrics.overlap_savings_ms/10:.0f}%")
    
    def get_parallel_metrics(self) -> dict:
        """Get parallel pipeline metrics."""
        with self._metrics_lock:
            return self._metrics.to_dict()


# Convenience function
def create_parallel_pipeline(config: Optional[PipelineConfig] = None) -> ParallelTranslationPipeline:
    """Create a parallel translation pipeline."""
    return ParallelTranslationPipeline(config)
