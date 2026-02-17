"""
Audio streaming pipeline

High-performance audio processing pipeline with:
- Multi-threaded processing
- Backpressure handling
- Performance metrics
- Processor chaining
"""

import threading
import time
import logging
from typing import Callable, List, Optional, Dict, Any
from dataclasses import dataclass, field
from queue import Queue, Empty
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for audio streaming pipeline"""
    buffer_size_ms: int = 3000
    processing_threads: int = 2
    enable_backpressure: bool = True
    max_queue_size: int = 100
    drop_on_overflow: bool = True  # Drop oldest vs block


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    chunks_processed: int = 0
    chunks_dropped: int = 0
    chunks_queued: int = 0
    avg_processing_time_ms: float = 0.0
    max_processing_time_ms: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def runtime_seconds(self) -> float:
        return time.time() - self.start_time
    
    @property
    def throughput_chunks_per_sec(self) -> float:
        runtime = self.runtime_seconds
        return self.chunks_processed / runtime if runtime > 0 else 0
    
    @property
    def drop_rate(self) -> float:
        total = self.chunks_processed + self.chunks_dropped
        return self.chunks_dropped / total if total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunks_processed": self.chunks_processed,
            "chunks_dropped": self.chunks_dropped,
            "chunks_queued": self.chunks_queued,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "max_processing_time_ms": self.max_processing_time_ms,
            "runtime_seconds": self.runtime_seconds,
            "throughput_chunks_per_sec": self.throughput_chunks_per_sec,
            "drop_rate": self.drop_rate
        }


class AudioProcessor:
    """Base class for audio processors"""
    
    def __init__(self, name: str = "processor"):
        self.name = name
        
    def process(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Process audio chunk
        
        Args:
            audio_chunk: Input audio data
            
        Returns:
            Processed audio data
        """
        raise NotImplementedError
    
    def reset(self):
        """Reset processor state"""
        pass


class AudioStreamingPipeline:
    """
    High-performance audio streaming pipeline
    
    Features:
    - Multi-threaded processing
    - Configurable backpressure
    - Processor chaining
    - Real-time metrics
    
    Usage:
        config = PipelineConfig(processing_threads=2)
        pipeline = AudioStreamingPipeline(config)
        
        # Add processors
        pipeline.add_processor(resample_processor)
        pipeline.add_processor(vad_processor)
        
        # Start pipeline
        pipeline.start()
        
        # Feed audio
        for chunk in audio_stream:
            pipeline.feed(chunk)
        
        # Get output
        while True:
            output = pipeline.get_output(timeout=0.1)
            if output is not None:
                process_output(output)
        
        # Stop
        pipeline.stop()
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize streaming pipeline
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        
        # Queues
        self.input_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        self.output_queue: Queue = Queue()
        
        # Processors
        self.processors: List[AudioProcessor] = []
        
        # Threading
        self.is_running = False
        self.threads: List[threading.Thread] = []
        self._lock = threading.Lock()
        
        # Metrics
        self.metrics = PipelineMetrics()
        
        logger.info(f"Pipeline initialized with {self.config.processing_threads} threads")
    
    def add_processor(self, processor: AudioProcessor):
        """
        Add audio processor to pipeline
        
        Processors are applied in order added.
        
        Args:
            processor: AudioProcessor instance
        """
        self.processors.append(processor)
        logger.debug(f"Added processor: {processor.name}")
    
    def add_processor_func(self, func: Callable[[np.ndarray], np.ndarray], name: str = "func"):
        """
        Add a function as a processor
        
        Args:
            func: Processing function
            name: Processor name
        """
        class FuncProcessor(AudioProcessor):
            def process(self, audio_chunk):
                return func(audio_chunk)
        
        processor = FuncProcessor(name)
        self.add_processor(processor)
    
    def start(self):
        """Start the pipeline"""
        if self.is_running:
            logger.warning("Pipeline already running")
            return
        
        self.is_running = True
        self.metrics.start_time = time.time()
        
        # Start processing threads
        for i in range(self.config.processing_threads):
            thread = threading.Thread(
                target=self._processing_loop,
                name=f"AudioProcessor-{i}",
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
        
        logger.info(f"Pipeline started with {len(self.threads)} threads")
    
    def stop(self):
        """Stop the pipeline"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=2.0)
        
        self.threads = []
        
        # Clear queues
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except Empty:
                break
        
        logger.info("Pipeline stopped")
    
    def feed(self, audio_chunk: np.ndarray) -> bool:
        """
        Feed audio chunk into pipeline
        
        Args:
            audio_chunk: Audio data to process
            
        Returns:
            True if accepted, False if dropped
        """
        if not self.is_running:
            logger.warning("Pipeline not running, cannot feed")
            return False
        
        # Handle backpressure
        if self.input_queue.full():
            if self.config.drop_on_overflow:
                # Drop oldest chunks
                while self.input_queue.full():
                    try:
                        self.input_queue.get_nowait()
                        with self._lock:
                            self.metrics.chunks_dropped += 1
                    except Empty:
                        break
            else:
                # Would block - drop instead
                with self._lock:
                    self.metrics.chunks_dropped += 1
                return False
        
        try:
            self.input_queue.put_nowait(audio_chunk)
            with self._lock:
                self.metrics.chunks_queued = self.input_queue.qsize()
            return True
        except:
            with self._lock:
                self.metrics.chunks_dropped += 1
            return False
    
    def get_output(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """
        Get processed audio chunk
        
        Args:
            timeout: Maximum time to wait for output
            
        Returns:
            Processed audio chunk or None if timeout
        """
        try:
            return self.output_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def _processing_loop(self):
        """Main processing loop (runs in worker threads)"""
        while self.is_running:
            try:
                # Get chunk from input queue
                chunk = self.input_queue.get(timeout=0.1)
                
                # Process
                start_time = time.perf_counter()
                processed = self._process_chunk(chunk)
                processing_time = (time.perf_counter() - start_time) * 1000
                
                # Update metrics
                self._update_metrics(processing_time)
                
                # Send to output
                if processed is not None:
                    self.output_queue.put(processed)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Processing error: {e}")
    
    def _process_chunk(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Process audio chunk through all processors
        
        Args:
            audio_chunk: Input audio data
            
        Returns:
            Processed audio or None if dropped
        """
        processed = audio_chunk
        
        for processor in self.processors:
            try:
                processed = processor.process(processed)
                if processed is None:
                    # Processor dropped the chunk
                    return None
            except Exception as e:
                logger.error(f"Processor {processor.name} error: {e}")
                return None
        
        return processed
    
    def _update_metrics(self, processing_time_ms: float):
        """Update performance metrics"""
        with self._lock:
            self.metrics.chunks_processed += 1
            
            # Exponential moving average for processing time
            alpha = 0.1
            self.metrics.avg_processing_time_ms = (
                alpha * processing_time_ms +
                (1 - alpha) * self.metrics.avg_processing_time_ms
            )
            
            # Track max processing time
            if processing_time_ms > self.metrics.max_processing_time_ms:
                self.metrics.max_processing_time_ms = processing_time_ms
    
    def get_metrics(self) -> PipelineMetrics:
        """Get current metrics (returns a copy)"""
        with self._lock:
            # Return a copy to avoid race conditions
            return PipelineMetrics(
                chunks_processed=self.metrics.chunks_processed,
                chunks_dropped=self.metrics.chunks_dropped,
                chunks_queued=self.input_queue.qsize(),
                avg_processing_time_ms=self.metrics.avg_processing_time_ms,
                max_processing_time_ms=self.metrics.max_processing_time_ms,
                start_time=self.metrics.start_time
            )
    
    def reset_metrics(self):
        """Reset performance metrics"""
        with self._lock:
            self.metrics = PipelineMetrics()
        logger.debug("Metrics reset")
    
    def reset_processors(self):
        """Reset all processors"""
        for processor in self.processors:
            processor.reset()
        logger.debug("Processors reset")
    
    def clear_queues(self):
        """Clear input and output queues"""
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except Empty:
                break
        
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except Empty:
                break
        
        logger.debug("Queues cleared")


# Common audio processors

class ResampleProcessor(AudioProcessor):
    """Audio resampling processor"""
    
    def __init__(self, source_rate: int, target_rate: int):
        super().__init__(f"resample_{source_rate}_to_{target_rate}")
        self.source_rate = source_rate
        self.target_rate = target_rate
        
    def process(self, audio_chunk: np.ndarray) -> np.ndarray:
        if self.source_rate == self.target_rate:
            return audio_chunk
        
        # Linear interpolation resampling
        ratio = self.target_rate / self.source_rate
        new_length = int(len(audio_chunk) * ratio)
        indices = np.linspace(0, len(audio_chunk) - 1, new_length)
        return np.interp(indices, np.arange(len(audio_chunk)), audio_chunk).astype(audio_chunk.dtype)


class GainProcessor(AudioProcessor):
    """Audio gain processor"""
    
    def __init__(self, gain_db: float):
        super().__init__(f"gain_{gain_db}db")
        self.gain = 10 ** (gain_db / 20)
        
    def process(self, audio_chunk: np.ndarray) -> np.ndarray:
        if audio_chunk.dtype == np.int16:
            # Convert to float, apply gain, convert back
            float_audio = audio_chunk.astype(np.float32) * self.gain
            return np.clip(float_audio, -32768, 32767).astype(np.int16)
        else:
            return (audio_chunk * self.gain).astype(audio_chunk.dtype)


class NormalizeProcessor(AudioProcessor):
    """Audio normalization processor"""
    
    def __init__(self, target_peak: float = 0.9):
        super().__init__(f"normalize_{target_peak}")
        self.target_peak = target_peak
        
    def process(self, audio_chunk: np.ndarray) -> np.ndarray:
        if len(audio_chunk) == 0:
            return audio_chunk
        
        # Convert to float
        if audio_chunk.dtype == np.int16:
            float_audio = audio_chunk.astype(np.float32) / 32768.0
        else:
            float_audio = audio_chunk.astype(np.float32)
        
        # Calculate peak
        peak = np.max(np.abs(float_audio))
        if peak > 0:
            gain = self.target_peak / peak
            float_audio = float_audio * gain
        
        # Convert back
        if audio_chunk.dtype == np.int16:
            return (float_audio * 32768.0).astype(np.int16)
        return float_audio.astype(audio_chunk.dtype)
