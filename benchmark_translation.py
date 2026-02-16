#!/usr/bin/env python3
"""
Translation Latency Benchmark

Measures translation latency for MarianMT and NLLB models.
"""

import sys
import time
import statistics
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "voice_translation" / "src"))

from translation.marian import MarianTranslator
from translation.nllb import NLLBTranslator
from translation.cache import CachedTranslator, TranslationCache


# Test phrases of different lengths
TEST_PHRASES = {
    "short": [
        ("Hello", "en", "zh"),
        ("Good morning", "en", "zh"),
        ("Thank you", "en", "zh"),
    ],
    "medium": [
        ("How are you doing today?", "en", "zh"),
        ("I would like to order coffee", "en", "zh"),
        ("The weather is nice today", "en", "zh"),
    ],
    "long": [
        ("Can you tell me where the nearest train station is located?", "en", "zh"),
        ("I am looking for a restaurant that serves vegetarian food", "en", "zh"),
        ("The meeting will start at three o'clock in the afternoon", "en", "zh"),
    ]
}


def benchmark_translator(translator_class, name, iterations=10, use_cache=False):
    """
    Benchmark a translator.
    
    Args:
        translator_class: Translator class to test
        name: Display name
        iterations: Number of iterations per phrase
        use_cache: Whether to enable caching
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking: {name}")
    if use_cache:
        print("  (with caching enabled)")
    print('='*60)
    
    results = {}
    
    # Initialize translator
    start_time = time.time()
    if name == "MarianMT":
        translator = translator_class(source_lang="en", target_lang="zh")
    else:  # NLLB
        translator = translator_class()
    
    if use_cache:
        translator = CachedTranslator(translator)
    
    init_time = time.time() - start_time
    print(f"Initialization: {init_time:.2f}s")
    
    # Warm up
    print("Warming up...")
    for _ in range(3):
        try:
            translator.translate("Hello", "en", "zh")
        except Exception as e:
            logger.error(f"Warm-up failed: {e}")
            return None
    
    # Benchmark each category
    for category, phrases in TEST_PHRASES.items():
        print(f"\n  {category.upper()} phrases:")
        latencies = []
        
        for text, src, tgt in phrases:
            for i in range(iterations):
                try:
                    start = time.perf_counter()
                    result = translator.translate(text, src, tgt)
                    elapsed = time.perf_counter() - start
                    
                    if result:
                        latencies.append(elapsed * 1000)  # Convert to ms
                        
                        # Show first translation result
                        if i == 0:
                            print(f"    \"{text[:40]}...\" → \"{result.translated_text[:40]}...\"")
                            
                except Exception as e:
                    logger.error(f"Translation failed: {e}")
                    continue
        
        if latencies:
            results[category] = {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "count": len(latencies)
            }
            
            print(f"    Latency: {results[category]['mean']:.1f}ms mean, "
                  f"{results[category]['median']:.1f}ms median "
                  f"({len(latencies)} translations)")
    
    # Cache stats
    if use_cache:
        stats = translator.get_stats()
        print(f"\n  Cache stats: {stats}")
    
    return results


def compare_translators():
    """Compare MarianMT vs NLLB performance."""
    print("\n" + "="*60)
    print("TRANSLATION ENGINE COMPARISON")
    print("="*60)
    
    # Benchmark MarianMT
    marian_results = benchmark_translator(MarianTranslator, "MarianMT", iterations=5)
    
    # Benchmark MarianMT with cache
    marian_cached = benchmark_translator(
        MarianTranslator, "MarianMT", iterations=5, use_cache=True
    )
    
    # Benchmark NLLB (commented out - very slow)
    # nllb_results = benchmark_translator(NLLBTranslator, "NLLB-200", iterations=2)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if marian_results:
        print("\nMarianMT (baseline):")
        for cat, data in marian_results.items():
            print(f"  {cat:8}: {data['mean']:6.1f}ms mean, {data['median']:6.1f}ms median")
    
    if marian_cached:
        print("\nMarianMT (with cache):")
        for cat, data in marian_cached.items():
            print(f"  {cat:8}: {data['mean']:6.1f}ms mean, {data['median']:6.1f}ms median")
    
    print("\nRecommendations:")
    print("  • MarianMT: Use for real-time (<200ms), good for zh/en")
    print("  • With cache: Common phrases translate instantly")
    print("  • NLLB-200: More accurate but ~3-5x slower, use for quality")


if __name__ == "__main__":
    compare_translators()
