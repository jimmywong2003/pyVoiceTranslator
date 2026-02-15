"""
Performance benchmarking for audio processing

Measure and analyze audio pipeline performance.
"""

import time
import statistics
import logging
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
import numpy as np

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Benchmark result"""
    name: str
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput_chunks_per_sec: float
    cpu_percent: float
    memory_mb: float
    total_chunks: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "avg_time_ms": self.avg_time_ms,
            "min_time_ms": self.min_time_ms,
            "max_time_ms": self.max_time_ms,
            "std_dev_ms": self.std_dev_ms,
            "throughput_chunks_per_sec": self.throughput_chunks_per_sec,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "total_chunks": self.total_chunks
        }
    
    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Avg time: {self.avg_time_ms:.3f}ms\n"
            f"  Min/Max: {self.min_time_ms:.3f}ms / {self.max_time_ms:.3f}ms\n"
            f"  Std dev: {self.std_dev_ms:.3f}ms\n"
            f"  Throughput: {self.throughput_chunks_per_sec:.1f} chunks/sec\n"
            f"  CPU: {self.cpu_percent:.1f}%"
        )


class AudioBenchmark:
    """
    Performance benchmarking for audio pipeline
    
    Usage:
        benchmark = AudioBenchmark(sample_rate=16000)
        
        # Benchmark VAD
        vad_result = benchmark.benchmark_vad(vad_processor, num_chunks=1000)
        print(vad_result)
        
        # Benchmark pipeline
        pipeline_result = benchmark.benchmark_pipeline(pipeline, num_chunks=1000)
        print(pipeline_result)
        
        # Full benchmark
        results = benchmark.run_full_benchmark(vad, pipeline)
    """
    
    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 30):
        """
        Initialize benchmark
        
        Args:
            sample_rate: Audio sample rate
            chunk_duration_ms: Chunk duration in milliseconds
        """
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        
        logger.info(f"Benchmark initialized: {sample_rate}Hz, {chunk_duration_ms}ms chunks")
    
    def generate_test_audio(
        self,
        num_chunks: int,
        pattern: str = "speech"
    ) -> List[np.ndarray]:
        """
        Generate test audio chunks
        
        Args:
            num_chunks: Number of chunks to generate
            pattern: Audio pattern ("speech", "silence", "mixed", "noise")
            
        Returns:
            List of audio chunks
        """
        chunks = []
        
        for i in range(num_chunks):
            if pattern == "speech":
                # Simulate speech with varying amplitude
                t = np.linspace(0, self.chunk_duration_ms / 1000, self.chunk_samples)
                freq = 200 + 100 * np.sin(i * 0.1)  # Varying frequency
                amplitude = 0.3 + 0.2 * np.sin(i * 0.2)  # Varying amplitude
                audio = (amplitude * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
            
            elif pattern == "silence":
                # Near-silence with small noise
                audio = (np.random.randn(self.chunk_samples) * 100).astype(np.int16)
            
            elif pattern == "mixed":
                # Mix of speech and silence
                if i % 10 < 7:  # 70% speech
                    t = np.linspace(0, self.chunk_duration_ms / 1000, self.chunk_samples)
                    freq = 200
                    audio = (0.3 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
                else:
                    audio = (np.random.randn(self.chunk_samples) * 100).astype(np.int16)
            
            else:  # noise
                audio = (np.random.randn(self.chunk_samples) * 1000).astype(np.int16)
            
            chunks.append(audio)
        
        return chunks
    
    def benchmark_vad(
        self,
        vad_processor,
        num_chunks: int = 1000,
        pattern: str = "mixed"
    ) -> BenchmarkResult:
        """
        Benchmark VAD processor
        
        Args:
            vad_processor: VAD processor to benchmark
            num_chunks: Number of chunks to process
            pattern: Test audio pattern
            
        Returns:
            BenchmarkResult with performance metrics
        """
        logger.info(f"Benchmarking VAD with {num_chunks} chunks...")
        
        # Generate test audio
        chunks = self.generate_test_audio(num_chunks, pattern)
        
        # Warmup
        logger.debug("Warming up...")
        for chunk in chunks[:10]:
            vad_processor.process_chunk(chunk)
        
        # Reset state
        vad_processor.reset()
        
        # Benchmark
        times = []
        process = psutil.Process() if HAS_PSUTIL else None
        
        if process:
            process.cpu_percent()  # Initialize CPU measurement
        
        start_time = time.perf_counter()
        
        for chunk in chunks:
            chunk_start = time.perf_counter()
            vad_processor.process_chunk(chunk)
            times.append((time.perf_counter() - chunk_start) * 1000)
        
        total_time = time.perf_counter() - start_time
        
        # Get CPU and memory
        cpu_percent = process.cpu_percent() if process else 0
        memory_mb = process.memory_info().rss / 1024 / 1024 if process else 0
        
        result = BenchmarkResult(
            name="VAD Processing",
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            throughput_chunks_per_sec=num_chunks / total_time,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            total_chunks=num_chunks
        )
        
        logger.info(f"VAD benchmark complete: {result.avg_time_ms:.3f}ms avg")
        return result
    
    def benchmark_pipeline(
        self,
        pipeline,
        num_chunks: int = 1000,
        pattern: str = "mixed"
    ) -> BenchmarkResult:
        """
        Benchmark full pipeline
        
        Args:
            pipeline: Audio pipeline to benchmark
            num_chunks: Number of chunks to process
            pattern: Test audio pattern
            
        Returns:
            BenchmarkResult with performance metrics
        """
        logger.info(f"Benchmarking pipeline with {num_chunks} chunks...")
        
        # Generate test audio
        chunks = self.generate_test_audio(num_chunks, pattern)
        
        # Start pipeline
        pipeline.start()
        
        # Warmup
        logger.debug("Warming up...")
        for chunk in chunks[:10]:
            pipeline.feed(chunk)
        
        pipeline.reset_metrics()
        
        # Benchmark
        process = psutil.Process() if HAS_PSUTIL else None
        if process:
            process.cpu_percent()
        
        start_time = time.perf_counter()
        
        for chunk in chunks:
            pipeline.feed(chunk)
        
        # Wait for processing to complete
        while pipeline.get_metrics().chunks_processed < num_chunks:
            time.sleep(0.01)
        
        total_time = time.perf_counter() - start_time
        
        # Get metrics
        metrics = pipeline.get_metrics()
        cpu_percent = process.cpu_percent() if process else 0
        memory_mb = process.memory_info().rss / 1024 / 1024 if process else 0
        
        pipeline.stop()
        
        result = BenchmarkResult(
            name="Full Pipeline",
            avg_time_ms=metrics.avg_processing_time_ms,
            min_time_ms=0,  # Not tracked for pipeline
            max_time_ms=metrics.max_processing_time_ms,
            std_dev_ms=0,
            throughput_chunks_per_sec=metrics.throughput_chunks_per_sec,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            total_chunks=metrics.chunks_processed
        )
        
        logger.info(f"Pipeline benchmark complete: {result.avg_time_ms:.3f}ms avg")
        return result
    
    def benchmark_capture(
        self,
        capture_manager,
        duration: float = 5.0
    ) -> Dict[str, Any]:
        """
        Benchmark audio capture
        
        Args:
            capture_manager: Audio manager to benchmark
            duration: Capture duration in seconds
            
        Returns:
            Dictionary with capture metrics
        """
        logger.info(f"Benchmarking capture for {duration}s...")
        
        chunks_received = []
        start_time = time.time()
        
        def callback(chunk):
            chunks_received.append(chunk)
        
        capture_manager.start_capture(callback=callback)
        time.sleep(duration)
        capture_manager.stop_capture()
        
        elapsed = time.time() - start_time
        expected_chunks = elapsed * 1000 / self.chunk_duration_ms
        
        metrics = {
            "duration": elapsed,
            "chunks_received": len(chunks_received),
            "expected_chunks": expected_chunks,
            "capture_rate": len(chunks_received) / elapsed,
            "drop_rate": (expected_chunks - len(chunks_received)) / expected_chunks
        }
        
        logger.info(f"Capture benchmark: {metrics['capture_rate']:.1f} chunks/sec")
        return metrics
    
    def run_full_benchmark(
        self,
        vad_processor,
        pipeline,
        num_chunks: int = 1000
    ) -> Dict[str, Any]:
        """
        Run complete benchmark suite
        
        Args:
            vad_processor: VAD processor to benchmark
            pipeline: Pipeline to benchmark
            num_chunks: Number of chunks for each test
            
        Returns:
            Dictionary with all benchmark results
        """
        logger.info("Running full benchmark suite...")
        
        results = {
            "vad": self.benchmark_vad(vad_processor, num_chunks),
            "pipeline": self.benchmark_pipeline(pipeline, num_chunks),
            "configuration": {
                "sample_rate": self.sample_rate,
                "chunk_duration_ms": self.chunk_duration_ms,
                "chunk_samples": self.chunk_samples,
                "num_chunks": num_chunks
            }
        }
        
        logger.info("Full benchmark complete")
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Pretty print benchmark results"""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        
        if "configuration" in results:
            config = results["configuration"]
            print(f"\nConfiguration:")
            print(f"  Sample rate: {config['sample_rate']} Hz")
            print(f"  Chunk duration: {config['chunk_duration_ms']} ms")
            print(f"  Chunk samples: {config['chunk_samples']}")
            print(f"  Test chunks: {config['num_chunks']}")
        
        for key, result in results.items():
            if isinstance(result, BenchmarkResult):
                print(f"\n{result}")
        
        print("=" * 60 + "\n")
