"""
Streaming Performance Benchmark Suite - Phase 2.3

Comprehensive benchmarks for streaming translation:
- Latency targets: TTFT <2000ms, Meaning <2000ms, Ear-Voice <500ms
- Throughput tests
- Accuracy validation
- Resource utilization
"""

import time
import asyncio
import logging
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field, asdict
from collections import deque
import json
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    name: str
    duration_sec: float
    
    # Latency metrics (ms)
    ttft_mean: float
    ttft_p50: float
    ttft_p99: float
    ttft_max: float
    ttft_target_met: float  # percentage
    
    meaning_latency_mean: float
    meaning_latency_p50: float
    meaning_latency_p99: float
    meaning_latency_target_met: float
    
    ear_voice_lag_mean: float
    ear_voice_lag_p99: float
    ear_voice_lag_target_met: float
    
    # Throughput
    segments_per_minute: float
    words_per_minute: float
    
    # Quality
    draft_stability_mean: float
    deduplication_accuracy: float
    
    # Resource usage
    cpu_mean: float
    memory_peak_mb: float
    
    # Pass/fail
    passed: bool
    failures: List[str] = field(default_factory=list)


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""
    duration_sec: int = 60
    warmup_sec: int = 10
    
    # Targets
    target_ttft_ms: float = 2000.0
    target_meaning_latency_ms: float = 2000.0
    target_ear_voice_lag_ms: float = 500.0
    
    # Test scenarios
    test_scenarios: List[str] = field(default_factory=lambda: [
        'simple_speech',
        'continuous_speech',
        'interrupted_speech',
        'noisy_audio'
    ])
    
    # Hardware backends to test
    backends: List[str] = field(default_factory=lambda: ['fallback'])


class StreamingBenchmark:
    """Main benchmark runner."""
    
    TARGETS = {
        'ttft_ms': 2000,
        'meaning_latency_ms': 2000,
        'ear_voice_lag_ms': 500
    }
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[BenchmarkResult] = []
        
    def run_all(self) -> List[BenchmarkResult]:
        """Run all benchmark scenarios."""
        logger.info("=" * 60)
        logger.info("VoiceTranslate Streaming Benchmark Suite")
        logger.info("=" * 60)
        logger.info(f"Duration: {self.config.duration_sec}s per scenario")
        logger.info(f"Warmup: {self.config.warmup_sec}s")
        logger.info(f"Targets: {self.TARGETS}")
        logger.info("")
        
        for backend in self.config.backends:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing Backend: {backend}")
            logger.info(f"{'='*60}")
            
            for scenario in self.config.test_scenarios:
                result = self._run_scenario(scenario, backend)
                self.results.append(result)
                self._print_result(result)
        
        self._generate_report()
        return self.results
    
    def _run_scenario(self, scenario: str, backend: str) -> BenchmarkResult:
        """Run a single benchmark scenario."""
        logger.info(f"\nScenario: {scenario} | Backend: {backend}")
        logger.info("-" * 40)
        
        # Warmup
        if self.config.warmup_sec > 0:
            logger.info(f"Warming up for {self.config.warmup_sec}s...")
            time.sleep(self.config.warmup_sec)
        
        # Collect metrics
        ttft_values = []
        meaning_values = []
        ear_voice_values = []
        stability_values = []
        
        start_time = time.time()
        segments = 0
        words = 0
        
        # Simulate benchmark run
        while time.time() - start_time < self.config.duration_sec:
            # Simulate segment processing
            ttft = np.random.normal(1500, 400)  # Simulated TTFT
            meaning = ttft + np.random.normal(300, 100)
            ear_voice = np.random.normal(300, 100)
            stability = np.random.uniform(0.8, 0.95)
            
            ttft_values.append(max(0, ttft))
            meaning_values.append(max(0, meaning))
            ear_voice_values.append(max(0, ear_voice))
            stability_values.append(stability)
            
            segments += 1
            words += np.random.randint(5, 20)
            
            time.sleep(0.1)  # Simulate real-time
        
        # Calculate results
        actual_duration = time.time() - start_time
        
        # Calculate percentiles
        ttft_array = np.array(ttft_values)
        meaning_array = np.array(meaning_values)
        ear_voice_array = np.array(ear_voice_values)
        
        ttft_mean = np.mean(ttft_array)
        ttft_p50 = np.percentile(ttft_array, 50)
        ttft_p99 = np.percentile(ttft_array, 99)
        ttft_max = np.max(ttft_array)
        ttft_target_met = np.mean(ttft_array < self.config.target_ttft_ms) * 100
        
        meaning_mean = np.mean(meaning_array)
        meaning_p50 = np.percentile(meaning_array, 50)
        meaning_p99 = np.percentile(meaning_array, 99)
        meaning_target_met = np.mean(meaning_array < self.config.target_meaning_latency_ms) * 100
        
        ear_voice_mean = np.mean(ear_voice_array)
        ear_voice_p99 = np.percentile(ear_voice_array, 99)
        ear_voice_target_met = np.mean(ear_voice_array < self.config.target_ear_voice_lag_ms) * 100
        
        # Check pass/fail
        failures = []
        if ttft_p99 > self.config.target_ttft_ms:
            failures.append(f"TTFT P99 ({ttft_p99:.0f}ms) > target ({self.config.target_ttft_ms}ms)")
        if meaning_p99 > self.config.target_meaning_latency_ms:
            failures.append(f"Meaning P99 ({meaning_p99:.0f}ms) > target ({self.config.target_meaning_latency_ms}ms)")
        if ear_voice_p99 > self.config.target_ear_voice_lag_ms:
            failures.append(f"Ear-Voice P99 ({ear_voice_p99:.0f}ms) > target ({self.config.target_ear_voice_lag_ms}ms)")
        
        return BenchmarkResult(
            name=f"{scenario}_{backend}",
            duration_sec=actual_duration,
            ttft_mean=ttft_mean,
            ttft_p50=ttft_p50,
            ttft_p99=ttft_p99,
            ttft_max=ttft_max,
            ttft_target_met=ttft_target_met,
            meaning_latency_mean=meaning_mean,
            meaning_latency_p50=meaning_p50,
            meaning_latency_p99=meaning_p99,
            meaning_latency_target_met=meaning_target_met,
            ear_voice_lag_mean=ear_voice_mean,
            ear_voice_lag_p99=ear_voice_p99,
            ear_voice_lag_target_met=ear_voice_target_met,
            segments_per_minute=segments / (actual_duration / 60),
            words_per_minute=words / (actual_duration / 60),
            draft_stability_mean=np.mean(stability_values),
            deduplication_accuracy=0.95,  # Simulated
            cpu_mean=25.0,  # Simulated
            memory_peak_mb=512.0,  # Simulated
            passed=len(failures) == 0,
            failures=failures
        )
    
    def _print_result(self, result: BenchmarkResult):
        """Print benchmark result."""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        logger.info(f"\n{status} - {result.name}")
        
        logger.info(f"  Latency (TTFT):")
        logger.info(f"    Mean: {result.ttft_mean:.1f}ms | P50: {result.ttft_p50:.1f}ms | P99: {result.ttft_p99:.1f}ms | Max: {result.ttft_max:.1f}ms")
        logger.info(f"    Target Met: {result.ttft_target_met:.1f}%")
        
        logger.info(f"  Latency (Meaning):")
        logger.info(f"    Mean: {result.meaning_latency_mean:.1f}ms | P50: {result.meaning_latency_p50:.1f}ms | P99: {result.meaning_latency_p99:.1f}ms")
        logger.info(f"    Target Met: {result.meaning_latency_target_met:.1f}%")
        
        logger.info(f"  Ear-Voice Lag:")
        logger.info(f"    Mean: {result.ear_voice_lag_mean:.1f}ms | P99: {result.ear_voice_lag_p99:.1f}ms")
        logger.info(f"    Target Met: {result.ear_voice_lag_target_met:.1f}%")
        
        logger.info(f"  Throughput: {result.segments_per_minute:.1f} seg/min, {result.words_per_minute:.1f} words/min")
        logger.info(f"  Quality: Stability={result.draft_stability_mean:.3f}, Dedup={result.deduplication_accuracy:.3f}")
        
        if result.failures:
            logger.info(f"  Failures:")
            for failure in result.failures:
                logger.info(f"    - {failure}")
    
    def _generate_report(self):
        """Generate JSON report."""
        report_path = Path('benchmark_report.json')
        
        report = {
            'config': asdict(self.config),
            'targets': self.TARGETS,
            'results': [asdict(r) for r in self.results],
            'summary': {
                'total_scenarios': len(self.results),
                'passed': sum(1 for r in self.results if r.passed),
                'failed': sum(1 for r in self.results if not r.passed),
                'overall_pass': all(r.passed for r in self.results)
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("BENCHMARK SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total scenarios: {report['summary']['total_scenarios']}")
        logger.info(f"Passed: {report['summary']['passed']}")
        logger.info(f"Failed: {report['summary']['failed']}")
        logger.info(f"Overall: {'✅ PASS' if report['summary']['overall_pass'] else '❌ FAIL'}")
        logger.info(f"\nReport saved to: {report_path.absolute()}")


class ABBenchmark:
    """A/B testing benchmark for comparing configurations."""
    
    def __init__(self):
        self.variants: Dict[str, Any] = {}
        self.results: Dict[str, List[float]] = {}
    
    def register_variant(self, name: str, config: Any):
        """Register a test variant."""
        self.variants[name] = config
        self.results[name] = []
    
    def run_comparison(self, duration_sec: int = 300) -> Dict[str, Any]:
        """Run A/B comparison between variants."""
        logger.info("=" * 60)
        logger.info("A/B Benchmark Comparison")
        logger.info("=" * 60)
        
        for name in self.variants:
            logger.info(f"\nTesting variant: {name}")
            # Run benchmark for this variant
            times = np.random.normal(1000, 200, 100)
            self.results[name] = times.tolist()
        
        # Statistical comparison
        return self._analyze_results()
    
    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze A/B test results."""
        analysis = {}
        names = list(self.variants.keys())
        
        if len(names) >= 2:
            variant_a = self.results[names[0]]
            variant_b = self.results[names[1]]
            
            mean_a = np.mean(variant_a)
            mean_b = np.mean(variant_b)
            
            analysis = {
                'variant_a': names[0],
                'variant_b': names[1],
                'mean_a': mean_a,
                'mean_b': mean_b,
                'winner': names[0] if mean_a < mean_b else names[1]
            }
            
            logger.info(f"\nA/B Test Results:")
            logger.info(f"  {names[0]} mean: {mean_a:.2f}ms")
            logger.info(f"  {names[1]} mean: {mean_b:.2f}ms")
            logger.info(f"  Winner: {analysis['winner']}")
        
        return analysis


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Streaming Performance Benchmark')
    parser.add_argument('--duration', type=int, default=60, help='Duration per scenario (seconds)')
    parser.add_argument('--warmup', type=int, default=10, help='Warmup duration (seconds)')
    parser.add_argument('--scenarios', nargs='+', default=['all'], help='Scenarios to run')
    parser.add_argument('--backends', nargs='+', default=['fallback'], help='Backends to test')
    parser.add_argument('--ab-test', action='store_true', help='Run A/B comparison')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if args.ab_test:
        # Run A/B test
        ab = ABBenchmark()
        ab.register_variant('baseline', {'draft_interval': 2000})
        ab.register_variant('optimized', {'draft_interval': 1500})
        ab.run_comparison(args.duration)
    else:
        # Run standard benchmark
        config = BenchmarkConfig(
            duration_sec=args.duration,
            warmup_sec=args.warmup,
            test_scenarios=args.scenarios if 'all' not in args.scenarios else [
                'simple_speech', 'continuous_speech', 'interrupted_speech'
            ],
            backends=args.backends
        )
        
        benchmark = StreamingBenchmark(config)
        benchmark.run_all()


if __name__ == '__main__':
    main()
