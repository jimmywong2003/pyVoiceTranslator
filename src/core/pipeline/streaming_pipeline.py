"""
Streaming Pipeline - Phase 1.5

End-to-end integration of all streaming components:
- StreamingASR: Cumulative context, draft/final modes
- AdaptiveDraftController: Skip drafts if paused/busy
- StreamingTranslator: Semantic gating, SOV safety
- StreamingMetricsCollector: TTFT, Meaning Latency
- StreamingUI: Diff visualization, transitions
"""

import time
import threading
import logging
from typing import Optional, Callable, Dict
from dataclasses import dataclass
from queue import Queue, Empty
import numpy as np

from ..asr.faster_whisper import FasterWhisperASR
from ..asr.post_processor import create_post_processed_asr
from ..asr.streaming_asr import StreamingASR, StreamingASRResult
from ..translation.marian import MarianTranslator
from ..translation.streaming_translator import StreamingTranslator
from .adaptive_controller import VADState
from ..utils.streaming_metrics import StreamingMetricsCollector
from ...gui.streaming_ui import StreamingUI
from .adaptive_controller import AdaptiveDraftController
from .segment_tracker import SegmentTracker, SegmentStage

logger = logging.getLogger(__name__)


@dataclass
class StreamingPipelineConfig:
    """Configuration for streaming pipeline."""
    # ASR
    asr_model_size: str = "base"
    asr_language: str = "en"
    
    # Translation
    source_language: str = "en"
    target_language: str = "fr"
    enable_translation: bool = True
    
    # Draft control
    draft_interval_ms: float = 2000
    min_speech_duration_ms: float = 500
    max_segment_duration_ms: float = 4000
    
    # Adaptive control
    pause_threshold_ms: float = 500
    max_queue_depth: int = 2
    
    # Metrics
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.draft_interval_ms < 1000:
            logger.warning(f"Draft interval {self.draft_interval_ms}ms is very short")


class StreamingTranslationPipeline:
    """
    End-to-end streaming translation pipeline.
    
    Phase 1.5: Integration of all streaming components.
    
    Architecture:
        Audio → VAD → Buffer → [Adaptive Check] → Draft ASR → [Semantic Check] → Translation → UI
                              ↓                          ↓
                         Skip if paused             Skip if incomplete
                              ↓                          ↓
                         Silence Detected → Final ASR → Final Translation → UI
    
    Usage:
        config = StreamingPipelineConfig()
        pipeline = StreamingTranslationPipeline(config)
        
        def on_output(text, is_final, stability):
            print(f"{'Final' if is_final else 'Draft'}: {text}")
        
        pipeline.start(on_output)
        # ... stream audio ...
        pipeline.stop()
    """
    
    def __init__(self, config: StreamingPipelineConfig):
        """Initialize streaming pipeline."""
        self.config = config
        
        # Initialize components
        logger.info("Initializing Streaming Translation Pipeline...")
        
        # ASR with post-processing for improved accuracy
        base_asr = FasterWhisperASR(
            model_size=config.asr_model_size,
            language=config.asr_language
        )
        self._base_asr = create_post_processed_asr(
            base_asr=base_asr,
            language=config.asr_language,
            remove_filler_words=True,
            enable_hallucination_filter=True,
            min_confidence=0.3
        )
        self._streaming_asr = StreamingASR(self._base_asr)
        
        # Translation
        if config.enable_translation:
            self._base_translator = MarianTranslator(
                source_lang=config.source_language,
                target_lang=config.target_language
            )
            self._streaming_translator = StreamingTranslator(
                self._base_translator,
                config.source_language,
                config.target_language
            )
        else:
            self._streaming_translator = None
        
        # Draft controller
        self._draft_controller = AdaptiveDraftController(
            draft_interval_ms=config.draft_interval_ms,
            pause_threshold_ms=config.pause_threshold_ms,
            max_queue_depth=config.max_queue_depth
        )
        
        # Metrics
        if config.enable_metrics:
            self._metrics = StreamingMetricsCollector()
        else:
            self._metrics = None
        
        # UI (optional, can be replaced with custom callback)
        self._ui = StreamingUI()
        
        # Segment tracking
        self._segment_tracker = SegmentTracker()
        
        # State
        self._is_running = False
        self._audio_buffer: list = []
        self._buffer_lock = threading.Lock()
        self._segment_counter = 0
        
        # Threading
        self._processing_thread: Optional[threading.Thread] = None
        self._output_callback: Optional[Callable] = None
        
        logger.info("✅ Streaming Pipeline initialized")
    
    def initialize(self) -> bool:
        """Initialize all components."""
        try:
            logger.info("Initializing components...")
            
            # Initialize ASR
            self._base_asr.initialize()
            logger.info("  ✅ ASR initialized")
            
            # Initialize translator
            if self._streaming_translator:
                self._base_translator.initialize()
                logger.info("  ✅ Translator initialized")
            
            logger.info("✅ All components ready")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def start(self, output_callback: Callable[[str, bool, float], None]):
        """
        Start the streaming pipeline.
        
        Args:
            output_callback: Function(text, is_final, stability) -> None
        """
        if self._is_running:
            logger.warning("Pipeline already running")
            return
        
        self._output_callback = output_callback
        self._is_running = True
        
        # Start processing thread
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            name="StreamingPipeline"
        )
        self._processing_thread.start()
        
        logger.info("✅ Streaming Pipeline started")
    
    def stop(self):
        """Stop the streaming pipeline."""
        if not self._is_running:
            return
        
        logger.info("Stopping Streaming Pipeline...")
        self._is_running = False
        
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # Print statistics
        if self._metrics:
            self._metrics.print_summary()
        
        self._ui.print_stats()
        
        logger.info("✅ Streaming Pipeline stopped")
    
    def process_audio(self, audio_chunk: np.ndarray):
        """
        Process incoming audio chunk.
        
        This is the main entry point for audio data.
        
        Args:
            audio_chunk: Audio data (numpy array, 16kHz)
        """
        with self._buffer_lock:
            self._audio_buffer.append(audio_chunk)
            self._streaming_asr.add_audio(audio_chunk)
    
    def _processing_loop(self):
        """Main processing loop (runs in separate thread)."""
        logger.info("Processing loop started")
        
        last_draft_time = 0
        speech_start_time = time.time()
        segment_uuid = None
        
        while self._is_running:
            try:
                current_time = time.time()
                buffer_duration_ms = len(self._audio_buffer) * 1000 / 16  # 16 samples/ms
                
                # Check if we should trigger a draft
                vad_state = VADState(
                    is_speaking=True,
                    recent_pause_ms=0,  # Would come from actual VAD
                    speech_duration_ms=buffer_duration_ms,
                    silence_duration_ms=0
                )
                
                should_draft = self._draft_controller.should_trigger_draft(
                    buffer_duration_ms,
                    vad_state,
                    compute_queue_depth=0  # Would track actual queue
                )
                
                if should_draft and buffer_duration_ms >= self.config.min_speech_duration_ms:
                    # Create segment if new
                    if segment_uuid is None:
                        self._segment_counter += 1
                        segment_uuid = self._segment_tracker.create_segment(
                            self._segment_counter,
                            audio_duration_ms=buffer_duration_ms
                        )
                        speech_start_time = current_time
                        
                        if self._metrics:
                            self._metrics.start_segment(segment_uuid, self._segment_counter)
                    
                    # Generate draft
                    self._process_draft(segment_uuid, speech_start_time)
                    last_draft_time = current_time
                
                # Small sleep to prevent busy-wait
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                time.sleep(0.5)
        
        logger.info("Processing loop stopped")
    
    def _process_draft(self, segment_uuid: str, speech_start_time: float):
        """Process draft generation."""
        try:
            # Generate draft ASR
            asr_result = self._streaming_asr.generate_draft()
            
            if not asr_result.text:
                return
            
            # Track metrics
            if self._metrics:
                self._metrics.record_first_draft(segment_uuid, asr_result.text)
                self._metrics.record_asr_call(segment_uuid)
            
            # Translate (with semantic gating)
            if self._streaming_translator:
                trans_result = self._streaming_translator.translate_streaming(
                    asr_result.text,
                    is_final=False
                )
                
                if trans_result.text:
                    # Record metrics
                    if self._metrics:
                        self._metrics.record_first_translation(
                            segment_uuid,
                            trans_result.text
                        )
                    
                    # Update UI
                    ui_result = self._ui.update_draft(
                        trans_result.text,
                        stability=trans_result.stability
                    )
                    
                    # Output callback
                    if self._output_callback:
                        self._output_callback(
                            trans_result.text,
                            False,
                            trans_result.stability
                        )
            else:
                # No translation, output ASR directly
                self._ui.update_draft(asr_result.text, stability=0.5)
                if self._output_callback:
                    self._output_callback(asr_result.text, False, 0.5)
            
        except Exception as e:
            logger.error(f"Draft processing error: {e}")
    
    def finalize_segment(self):
        """Finalize current segment (call on silence detection)."""
        try:
            # Generate final ASR
            asr_result = self._streaming_asr.generate_final()
            
            if not asr_result.text:
                return
            
            # Translate final
            if self._streaming_translator:
                trans_result = self._streaming_translator.translate_streaming(
                    asr_result.text,
                    is_final=True
                )
                
                # Update UI
                self._ui.show_final(
                    trans_result.text or asr_result.text,
                    stability=1.0
                )
                
                # Output callback
                if self._output_callback:
                    self._output_callback(
                        trans_result.text or asr_result.text,
                        True,
                        1.0
                    )
            else:
                self._ui.show_final(asr_result.text, stability=1.0)
                if self._output_callback:
                    self._output_callback(asr_result.text, True, 1.0)
            
            # Reset for next segment
            self._audio_buffer.clear()
            self._draft_controller.start_segment()
            
        except Exception as e:
            logger.error(f"Finalization error: {e}")
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        metrics = {}
        
        if self._metrics:
            snapshot = self._metrics.get_snapshot()
            metrics['ttft_ms'] = snapshot.avg_ttft_ms
            metrics['meaning_latency_ms'] = snapshot.avg_meaning_latency_ms
            metrics['ear_to_voice_lag_ms'] = snapshot.avg_ear_to_voice_lag_ms
            metrics['draft_stability'] = snapshot.avg_draft_stability
        
        draft_stats = self._draft_controller.get_stats()
        metrics['draft_trigger_rate'] = draft_stats['trigger_rate']
        
        ui_stats = self._ui.get_stats()
        metrics['draft_updates'] = ui_stats['draft_updates']
        metrics['final_shows'] = ui_stats['final_shows']
        
        return metrics
    
    def print_summary(self):
        """Print pipeline summary."""
        print("\n" + "=" * 60)
        print("📊 STREAMING PIPELINE SUMMARY (Phase 1.5)")
        print("=" * 60)
        
        print(f"\n  Configuration:")
        print(f"    ASR:      {self.config.asr_model_size}")
        print(f"    Language: {self.config.source_language} -> {self.config.target_language}")
        print(f"    Draft:    Every {self.config.draft_interval_ms}ms")
        
        metrics = self.get_metrics()
        
        print(f"\n  Performance:")
        if 'ttft_ms' in metrics:
            print(f"    TTFT:            {metrics['ttft_ms']:.0f}ms")
        if 'meaning_latency_ms' in metrics:
            print(f"    Meaning Latency: {metrics['meaning_latency_ms']:.0f}ms")
        if 'ear_to_voice_lag_ms' in metrics:
            print(f"    Ear-to-Voice:    {metrics['ear_to_voice_lag_ms']:.0f}ms")
        
        print(f"\n  Activity:")
        print(f"    Draft updates: {metrics.get('draft_updates', 0)}")
        print(f"    Final shows:   {metrics.get('final_shows', 0)}")
        print(f"    Trigger rate:  {metrics.get('draft_trigger_rate', 0):.1f}%")
        
        print("=" * 60)


def create_streaming_pipeline(
    source_lang: str = "en",
    target_lang: str = "fr",
    asr_model: str = "base"
) -> StreamingTranslationPipeline:
    """
    Factory function to create a streaming pipeline.
    
    Args:
        source_lang: Source language code
        target_lang: Target language code
        asr_model: ASR model size
        
    Returns:
        Configured StreamingTranslationPipeline
    """
    config = StreamingPipelineConfig(
        source_language=source_lang,
        target_language=target_lang,
        asr_model_size=asr_model,
        asr_language=source_lang
    )
    
    pipeline = StreamingTranslationPipeline(config)
    
    return pipeline
