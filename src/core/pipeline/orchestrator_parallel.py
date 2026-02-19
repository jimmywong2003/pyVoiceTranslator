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

# Week 0: Data integrity tracking
from .segment_tracker import SegmentTracker, SegmentStage
from .queue_monitor import QueueMonitor, InstrumentedQueue

logger = logging.getLogger(__name__)


@dataclass
class PipelineSegment:
    """Segment data passed between pipeline stages."""
    segment_id: int
    audio_data: np.ndarray
    start_time: float
    # Week 0: UUID for tracking
    segment_uuid: Optional[str] = None
    # ASR and translation results
    vad_confidence: float = 0.0
    asr_result: Optional[object] = None
    translation_result: Optional[str] = None
    asr_start_time: Optional[float] = None
    asr_end_time: Optional[float] = None
    translation_start_time: Optional[float] = None
    translation_end_time: Optional[float] = None
    is_partial: bool = False
    # Timing for overlap analysis
    vad_created_time: Optional[float] = None  # When VAD created this segment
    asr_queued_time: Optional[float] = None   # When ASR worker picked it up
    translation_queued_time: Optional[float] = None  # When translation was queued
    output_queued_time: Optional[float] = None  # When output was queued


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
        
        # Dedicated translation executor (2 workers for true parallelism)
        self._translation_executor = ThreadPoolExecutor(
            max_workers=2,  # Increased from 1 to allow parallel translations
            thread_name_prefix="TranslationWorker"
        )
        
        # Bounded queues between stages
        self._vad_queue: Queue = Queue(maxsize=10)      # Audio → VAD
        self._asr_queue: Queue = Queue(maxsize=10)      # VAD → ASR
        self._translation_queue: Queue = Queue(maxsize=5)  # ASR → Translation
        self._output_queue: Queue = Queue(maxsize=20)   # Translation → Output
        
        # Week 0: Data integrity tracking
        self._segment_tracker = SegmentTracker()
        self._queue_monitor = QueueMonitor()
        
        # Register queues for monitoring
        self._queue_monitor.register_queue("vad", self._vad_queue)
        self._queue_monitor.register_queue("asr", self._asr_queue)
        self._queue_monitor.register_queue("translation", self._translation_queue)
        self._queue_monitor.register_queue("output", self._output_queue)
        
        # Set up drop/error callbacks
        self._segment_tracker.on_drop(self._on_segment_drop)
        self._segment_tracker.on_error(self._on_segment_error)
        
        # Worker threads
        self._vad_thread: Optional[threading.Thread] = None
        self._asr_thread: Optional[threading.Thread] = None
        self._translation_thread: Optional[threading.Thread] = None  # Dedicated translation worker
        self._output_thread: Optional[threading.Thread] = None
        
        # Tracking
        self._segment_counter = 0
        self._in_flight_segments: dict = {}  # segment_id → Future
        self._metrics = ParallelPipelineMetrics()
        self._metrics_lock = threading.Lock()
        
        # Overlap optimization - track completed translations for ordering
        self._completed_translations: dict = {}  # segment_id -> segment
        self._next_output_segment_id = 1  # Track next segment to output
        self._translation_lock = threading.Lock()
        
        logger.info("ParallelTranslationPipeline initialized (2 ASR workers, 2 translation workers, overlap enabled)")
        logger.info("Week 0: Data integrity tracking enabled (SegmentTracker + QueueMonitor)")
    
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
                from src.core.asr.post_processor import create_post_processed_asr
                from src.app.platform_utils import configure_asr_for_platform
                
                # Get platform-optimized ASR configuration
                asr_config = configure_asr_for_platform(self.config.asr_model_size)
                logger.info(f"    Platform config: device={asr_config['device']}, "
                          f"compute={asr_config['compute_type']}, threads={asr_config['cpu_threads']}")
                
                # Create base ASR with platform-optimized settings
                base_asr = FasterWhisperASR(
                    model_size=self.config.asr_model_size,
                    device=asr_config["device"],
                    compute_type=asr_config["compute_type"],
                    cpu_threads=asr_config["cpu_threads"],
                    language=self.config.asr_language
                )
                
                # Wrap with post-processor for hallucination filtering and text cleaning
                self._asr = create_post_processed_asr(
                    base_asr=base_asr,
                    language=self.config.asr_language,
                    remove_filler_words=True,
                    enable_hallucination_filter=True,
                    min_confidence=0.3
                )
                self._asr.initialize()
                logger.info("    ✅ Using post-processed ASR (hallucination filter + text cleaning)")
            
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
        self._translation_thread = threading.Thread(target=self._translation_worker, name="TranslationWorker")
        self._output_thread = threading.Thread(target=self._output_worker, name="OutputWorker")
        
        self._vad_thread.start()
        self._asr_thread.start()
        self._translation_thread.start()
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
    
    def _on_segment_drop(self, trace):
        """Callback when a segment is dropped."""
        logger.error(f"🚨 SEGMENT DROPPED: ID={trace.segment_id}, Reason={trace.dropped_reason}")
    
    def _on_segment_error(self, trace):
        """Callback when a segment has an error."""
        logger.error(f"🚨 SEGMENT ERROR: ID={trace.segment_id}, Error={trace.error_message}")
    
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
                    
                    # Week 0: Create segment with UUID tracking
                    audio_duration_ms = len(segment.audio_data) / self.config.sample_rate * 1000
                    segment_uuid = self._segment_tracker.create_segment(
                        self._segment_counter,
                        audio_duration_ms=audio_duration_ms
                    )
                    
                    pipeline_segment = PipelineSegment(
                        segment_id=self._segment_counter,
                        segment_uuid=segment_uuid,
                        audio_data=segment.audio_data,
                        start_time=time.time(),
                        vad_confidence=segment.confidence,
                        is_partial=getattr(segment, 'is_partial', False)
                    )
                    
                    # Record VAD processed stage
                    self._segment_tracker.record_stage(segment_uuid, SegmentStage.VAD_PROCESSED)
                    
                    try:
                        self._asr_queue.put_nowait(pipeline_segment)
                        
                        # Track queue operation
                        self._queue_monitor.record_put("asr", True, 0.1)
                        self._segment_tracker.record_stage(segment_uuid, SegmentStage.ASR_QUEUED)
                        
                        with self._metrics_lock:
                            self._metrics.total_segments += 1
                            self._metrics.queued_segments = self._asr_queue.qsize()
                        logger.debug(f"Queued segment {self._segment_counter} for ASR (queue: {self._asr_queue.qsize()})")
                    except Full:
                        # Week 0: Track drop
                        self._queue_monitor.record_put("asr", False, 0.1)
                        self._segment_tracker.record_drop(segment_uuid, "ASR queue full")
                        logger.warning(f"ASR queue full, dropping segment {self._segment_counter}")
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"VAD worker error: {e}")
        
        logger.info("VAD worker stopped")
    
    def _asr_worker(self):
        """ASR worker (dedicated thread - submits to ThreadPool)."""
        logger.info("ASR worker started")
        
        pending_futures = []
        
        while self._is_running:
            try:
                # Get segment from VAD queue
                segment = self._asr_queue.get(timeout=0.1)
                
                # Submit to ASR executor
                future = self._asr_executor.submit(self._process_asr, segment)
                pending_futures.append(future)
                
                # Add completion callback
                future.add_done_callback(self._on_asr_complete)
                
                with self._metrics_lock:
                    self._metrics.asr_in_progress += 1
                
                # Clean up completed futures
                pending_futures = [f for f in pending_futures if not f.done()]
                if len(pending_futures) >= 2:
                    logger.debug(f"ASR pipeline full: {len(pending_futures)} segments in flight")
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"ASR worker error: {e}")
        
        logger.info("ASR worker stopped")
    
    def _translation_worker(self):
        """Translation worker (dedicated thread - continuously processes translation queue)."""
        logger.info("Translation worker started")
        
        while self._is_running:
            try:
                # Get segment from translation queue
                segment = self._translation_queue.get(timeout=0.1)
                
                # Process translation asynchronously
                self._process_translation_async(segment)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Translation worker error: {e}")
        
        logger.info("Translation worker stopped")
    
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
            
            # ASR transcription (includes post-processing with hallucination filter + text cleaning)
            asr_result = self._asr.transcribe(
                audio_path,
                language=self.config.asr_language
            )
            
            segment.asr_end_time = time.time()
            segment.asr_result = asr_result
            
            # Log ASR result
            asr_time = (segment.asr_end_time - segment.asr_start_time) * 1000
            if asr_result and asr_result.text.strip():
                logger.info(f"ASR segment {segment.segment_id}: '{asr_result.text[:50]}...' ({asr_time:.0f}ms)")
            else:
                # Result was filtered by post-processor (hallucination or low quality)
                logger.warning(f"ASR segment {segment.segment_id}: Filtered/Empty result ({asr_time:.0f}ms) - skipping translation")
            
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
            # ASR result was filtered by post-processor, skip translation
            logger.debug(f"Translation segment {segment.segment_id}: Skipped (ASR filtered)")
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
            segment.asr_end_time = time.time()
            
            with self._metrics_lock:
                self._metrics.asr_in_progress -= 1
            
            # Track when translation is queued
            segment.translation_queued_time = time.time()
            
            # Submit to translation queue
            try:
                self._translation_queue.put_nowait(segment)
                logger.debug(f"Segment {segment.segment_id}: Queued for translation")
            except Full:
                logger.warning(f"Segment {segment.segment_id}: Translation queue full, processing inline")
                self._process_translation_async(segment)
            
        except Exception as e:
            logger.error(f"ASR completion error: {e}")
    
    def _process_translation_async(self, segment: PipelineSegment):
        """Submit translation task asynchronously (parallel, no chaining)."""
        # Track actual translation start time
        segment.translation_start_time = time.time()
        
        # Submit new translation immediately (no waiting for previous)
        # This allows ASR[i] to overlap with Translation[i-1]
        trans_future = self._translation_executor.submit(
            self._process_translation, segment
        )
        
        # Add completion callback
        trans_future.add_done_callback(
            lambda f, seg=segment: self._on_translation_complete(f, seg)
        )
        
        with self._metrics_lock:
            self._metrics.translation_in_progress += 1
        
        logger.debug(f"Segment {segment.segment_id}: Translation submitted (parallel mode)")
    
    def _on_translation_complete(self, future: Future, segment: PipelineSegment):
        """Callback when translation completes (handles out-of-order)."""
        try:
            completed_segment = future.result()
            completed_segment.translation_end_time = time.time()
            
            # Calculate translation duration
            trans_duration = (completed_segment.translation_end_time - completed_segment.translation_start_time) * 1000 if completed_segment.translation_start_time else 0
            
            with self._metrics_lock:
                self._metrics.translation_in_progress -= 1
                self._metrics.completed_segments += 1
            
            # Store completed translation
            with self._translation_lock:
                self._completed_translations[segment.segment_id] = completed_segment
                
                # Emit all segments that are ready in order
                while self._next_output_segment_id in self._completed_translations:
                    ready_segment = self._completed_translations.pop(self._next_output_segment_id)
                    self._next_output_segment_id += 1
                    
                    # Queue for output
                    try:
                        self._output_queue.put_nowait(ready_segment)
                        logger.debug(f"Segment {ready_segment.segment_id}: Translation complete ({trans_duration:.0f}ms), queued for output (in-order)")
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
                continue
            except Exception as e:
                logger.error(f"Output worker error: {e}")
        
        logger.info("Output worker stopped")
    
    def _emit_output(self, segment: PipelineSegment):
        """Emit translation output."""
        if not self._output_callback:
            return
        
        if not segment.asr_result or not segment.asr_result.text.strip():
            return
        
        # Calculate timing
        now = time.time()
        total_time = (now - segment.start_time) * 1000
        asr_time = (segment.asr_end_time - segment.asr_start_time) * 1000 if segment.asr_end_time else 0
        trans_time = (segment.translation_end_time - segment.translation_start_time) * 1000 if segment.translation_end_time else 0
        
        # Calculate queue wait times
        vad_to_asr_queue = (segment.asr_start_time - segment.start_time) * 1000 if segment.asr_start_time else 0
        asr_to_trans_queue = (segment.translation_start_time - segment.asr_end_time) * 1000 if segment.translation_start_time and segment.asr_end_time else 0
        
        # Calculate overlap savings
        # Without overlap (sequential): ASR_time + queue_wait + Translation_time
        # With overlap (parallel): max(ASR[i], Translation[i-1]) + overhead
        sequential_time = asr_time + trans_time
        theoretical_parallel_time = max(asr_time, trans_time)
        actual_parallel_time = total_time - vad_to_asr_queue - asr_to_trans_queue
        
        # Overlap effectiveness
        overlap_savings = sequential_time - actual_parallel_time
        overlap_efficiency = (overlap_savings / sequential_time * 100) if sequential_time > 0 else 0
        
        # Log detailed profiling for this segment (only if significant overlap or every 10th segment)
        show_profiling = (overlap_savings > 50) or (segment.segment_id % 10 == 0)
        if show_profiling:
            logger.info(
                f"\n📊 SEGMENT {segment.segment_id} PROFILING:\n"
                f"  ⏱️  ASR: {asr_time:.0f}ms | Translation: {trans_time:.0f}ms | Total: {total_time:.0f}ms\n"
                f"  ⏳ Queue waits: VAD→ASR={vad_to_asr_queue:.0f}ms | ASR→Trans={asr_to_trans_queue:.0f}ms\n"
                f"  🔀 Sequential: {sequential_time:.0f}ms | Parallel: {actual_parallel_time:.0f}ms | Savings: {overlap_savings:.0f}ms ({overlap_efficiency:.1f}%)"
            )
        
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
        
        if self._translation_thread and self._translation_thread.is_alive():
            self._translation_thread.join(timeout=timeout)
        
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=timeout)
        
        # Shutdown executors
        self._asr_executor.shutdown(wait=False)
        self._translation_executor.shutdown(wait=False)
        
        # Process remaining items in queues if requested
        if process_final:
            self._drain_queues()
        
        # Reset ordering state
        with self._translation_lock:
            self._completed_translations.clear()
            self._next_output_segment_id = 1
        
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
            avg_asr = self._metrics.avg_asr_time_ms
            avg_trans = self._metrics.avg_translation_time_ms
            avg_total = self._metrics.avg_total_time_ms
            avg_savings = self._metrics.overlap_savings_ms
            
            print(f"\n   Avg ASR Time: {avg_asr:.0f}ms")
            print(f"   Avg Translation Time: {avg_trans:.0f}ms")
            print(f"   Avg Total Time: {avg_total:.0f}ms")
            print(f"   Avg Overlap Savings: {avg_savings:.0f}ms")
            
            # Analysis
            sequential = avg_asr + avg_trans
            if sequential > 0:
                theoretical_min = max(avg_asr, avg_trans)
                actual_overhead = avg_total - theoretical_min
                efficiency = (avg_savings / sequential * 100) if sequential > 0 else 0
                
                print(f"\n🔍 Overlap Analysis:")
                print(f"   Sequential (ASR + Trans): {sequential:.0f}ms")
                print(f"   Theoretical Parallel: {theoretical_min:.0f}ms")
                print(f"   Actual Total: {avg_total:.0f}ms")
                print(f"   Overhead: {actual_overhead:.0f}ms")
                print(f"   Efficiency: {efficiency:.1f}%")
                
                # Note about real-time vs batch
                print(f"\n💡 Note:")
                if avg_savings < 10:
                    print(f"   For real-time streaming: 0ms overlap is EXPECTED")
                    print(f"   (segments arrive at speech speed, not queued)")
                    print(f"   Overlap optimization helps with batch file processing")
                else:
                    print(f"   ✅ Overlap optimization is working!")
                    print(f"   Savings of {avg_savings:.0f}ms per segment")
    
    def get_parallel_metrics(self) -> dict:
        """Get parallel pipeline metrics."""
        with self._metrics_lock:
            return self._metrics.to_dict()


# Convenience function
def create_parallel_pipeline(config: Optional[PipelineConfig] = None) -> ParallelTranslationPipeline:
    """Create a parallel translation pipeline."""
    return ParallelTranslationPipeline(config)
