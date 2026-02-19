# Evaluation of Streaming Architecture Suggestions

> **Source**: AI Analysis of Overlap Documents
> 
> **Purpose**: Evaluate proposed architectural changes with pros, cons, and implementation feasibility
> 
> **Last Updated**: 2026-02-19

---

## Executive Summary

| Aspect | Assessment |
|--------|------------|
| **Overall Quality** | Excellent - identifies the real opportunity (intra-segment pipelining) |
| **Feasibility** | Mixed - some suggestions are production-ready, others require significant R&D |
| **Risk Level** | Medium-High - streaming changes affect core quality |
| **Recommended Priority** | Incremental ASR (High), Wait-k MT (Medium), AsyncIO (Low) |

---

## 1. Critique of the Critique ✓

**Original Assessment**: Correct
- The suggestion correctly identifies that "Inter-Segment Overlap = 0ms" is only about throughput
- The real opportunity is **Intra-Segment Pipelining** (process while speaking)

**Missing Nuance**:
| Factor | Impact |
|--------|--------|
| Quality vs. Latency Trade-off | Not fully quantified |
| Model Capability Constraints | Some suggestions assume models support features they don't |
| UI Complexity | Streaming display requires significant UI rework |

---

## 2. Strategy A: Incremental ASR (Lookback Window)

### Proposal Summary
Process audio in fixed chunks (e.g., 1.5s) with context buffer, instead of waiting for silence.

### Pros ✓

| Advantage | Explanation |
|-----------|-------------|
| **True Overlap** | ASR works while user still speaking |
| **Reduced TTFT** | First text appears after 1.5s instead of 5s |
| **Proven Approach** | Commercial systems (Google Live Transcribe) use this |
| **faster-whisper Support** | Can simulate with overlapping chunks |

### Cons ✗

| Disadvantage | Severity | Details |
|--------------|----------|---------|
| **Context Duplication** | Medium | 3s prefix + 1.5s new = 50% duplicate compute |
| **Accuracy Degradation** | High | Whisper designed for complete utterances |
| **Boundary Artifacts** | Medium | "hello world" → "hello worl" + "rld" issues |
| **Hallucination Risk** | High | Partial audio lacks context, more hallucinations |
| **Increased Compute** | Medium | 3x more ASR calls (5s segment → 3 chunks) |

### Implementation Reality Check

```python
# Suggested approach (theoretical)
def incremental_asr(audio_stream):
    buffer = []
    for chunk in audio_stream.chunks(1.5):  # Every 1.5s
        context = buffer[-3:]  # Last 3s
        result = model.transcribe(context + chunk)
        yield result

# Reality: Whisper issues
# Problem 1: Context handling
result = model.transcribe(4.5s_audio)  # First chunk
# -> "Hello world today"

result = model.transcribe(4.5s_audio)  # Second chunk (overlap)
# -> "Hello world today is" (inconsistent prefix!)
# Whisper is non-deterministic with overlapping windows

# Problem 2: Duplicated text
# Chunk 1 (0-1.5s): "Hello"
# Chunk 2 (0-3s): "Hello world"  <- "Hello" repeated!
# Chunk 3 (1.5-4.5s): "world today" <- Need deduplication logic
```

### Verdict: ⚠️ Partially Feasible

| Approach | Feasibility | Quality Impact | Effort |
|----------|-------------|----------------|--------|
| Naive chunking | High | **Severe** (~30% WER increase) | Low |
| Whisper streaming wrappers | Medium | Moderate (~15% WER increase) | Medium |
| True streaming model (RNN-T) | Low | Minimal | **High** (model change) |
| Hybrid: VAD for finalize + chunking for draft | **High** | Low-Medium | Medium |

### Recommended Implementation

```python
# Hybrid approach (pragmatic)
class HybridStreamingASR:
    def __init__(self):
        self.draft_buffer = []
        self.final_result = None
        
    async def process_stream(self, audio_stream):
        async for chunk in audio_stream.chunks(500):  # 500ms chunks
            self.draft_buffer.append(chunk)
            
            # Every 2 seconds, produce draft
            if len(self.draft_buffer) >= 4:  # 2s accumulated
                draft_text = await self._transcribe_draft(
                    concatenate(self.draft_buffer)
                )
                yield StreamingResult(
                    text=draft_text,
                    is_final=False,
                    confidence=0.6  # Lower confidence for drafts
                )
            
            # VAD silence = finalize
            if vad.detect_silence(chunk):
                final_text = await self._transcribe_final(
                    concatenate(self.draft_buffer)
                )
                yield StreamingResult(
                    text=final_text,
                    is_final=True,
                    confidence=0.9
                )
                self.draft_buffer.clear()
```

---

## 3. Strategy B: Wait-k Translation (Incremental MT)

### Proposal Summary
Start translating after k words received, with correction mechanism for updates.

### Pros ✓

| Advantage | Explanation |
|-----------|-------------|
| **Early Output** | User sees translation sooner |
| **Theoretically Sound** | Research area (Gu et al., 2017) |
| **Latency Reduction** | Can reduce end-to-end by 30-50% |

### Cons ✗

| Disadvantage | Severity | Details |
|--------------|----------|---------|
| **Model Limitation** | **Critical** | MarianMT/NLLB are **not** streaming models |
| **Grammatical Chaos** | High | Subject/object ordering differs across languages |
| **Correction Complexity** | High | Retracting displayed text is UX nightmare |
| **Context Window** | Medium | MT needs full sentence for context |
| **Research-Level** | High | Not production-ready for most language pairs |

### Example of the Problem

```python
# Japanese to English Wait-k (k=2)
# JA: "私は昨日東京に行きました"
#     [Watashi-wa] [kinou] [Tokyo-ni] [ikimashita]
#     I          yesterday Tokyo     went

# k=2 translation starts after "私は昨日"
# Input: "I yesterday"
# Output: "I yesterday..." (nonsensical, waiting for verb)

# k=3 adds "東京に"
# Input: "I yesterday Tokyo"
# Output: "I yesterday went to Tokyo" (wrong order!)
# Correction: Change "yesterday" position

# Final input: "私は昨日東京に行きました"
# Correct: "I went to Tokyo yesterday"
```

**Japanese is SOV** (Subject-Object-Verb), **English is SVO** (Subject-Verb-Object).
Wait-k fails catastrophically for language pairs with different word orders.

### Verdict: ❌ Not Recommended for Current Stack

| Factor | Assessment |
|--------|------------|
| Model Support | MarianMT/NLLB do not support incremental inference |
| Language Pairs | Works for similar-order languages (en↔es), fails for different-order (ja↔en) |
| UX Impact | High - text jumping/correcting is disorienting |
| Implementation | Requires custom model training or research-level systems |

### Alternative: Chunk-Based Translation

```python
# Instead of wait-k, use shorter segments
# Current: Wait for full sentence (5-8s)
# Better: Translate every 2-3 words if grammatically complete

def segment_for_translation(asr_tokens):
    # Complete phrases that can stand alone
    complete_units = [
        ["Hello", "world"],           # ✓ Complete greeting
        ["I", "went", "to"],          # ✗ Incomplete (needs object)
        ["I", "went", "to", "Tokyo"], # ✓ Complete sentence
    ]
    
    # Only translate complete units
    if is_complete_unit(asr_tokens):
        return translate(asr_tokens)
    else:
        return None  # Wait for more
```

---

## 4. Strategy C: Compute-IO Overlap

### Proposal Summary
Warm-up models, memory pinning, quantization to reduce latency.

### Pros ✓

| Advantage | Current Status | Effort |
|-----------|----------------|--------|
| **Model Warm-up** | Already implemented | Zero |
| **Quantization** | INT8 already used for ASR | Zero |
| **Memory Pinning** | Valid optimization | Low |
| **Thread Affinity** | Valid optimization | Low |

### Reality Check

```python
# Current implementation (from STATUS.md)
class FasterWhisperASR:
    def __init__(self):
        # Model already warmed on init
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",  # Already quantized
            cpu_threads=8
        )
        # First inference (warm-up)
        self.model.transcribe(np.zeros(16000))  # Warm-up
```

**Most suggestions already implemented!**

### Additional Optimizations

```python
# Memory pinning for GPU path (if CUDA available)
def pin_memory(audio_array):
    """Ensure array is in pinned memory for faster GPU transfer"""
    import torch
    tensor = torch.from_numpy(audio_array)
    return tensor.pin_memory()  # Non-blocking GPU transfer

# Thread affinity for CPU path
import os
os.sched_setaffinity(0, {0, 1, 2, 3})  # Bind to specific cores
```

### Verdict: ✓ Already Done / Low-Hanging Fruit

---

## 5. Strategy D: Reactive Stream Architecture (AsyncIO)

### Proposal Summary
Replace ThreadPool with AsyncIO and async generators for lower overhead.

### Pros ✓

| Advantage | Reality |
|-----------|---------|
| **Lower Overhead** | True for I/O bound tasks |
| **No GIL Contention** | True for pure Python, but... |
| **Backpressure Handling** | Async generators handle this well |
| **Modern Python** | asyncio is standard |

### Cons ✗

| Disadvantage | Explanation |
|--------------|-------------|
| **GIL Not the Bottleneck** | ASR/MT release GIL during inference (C++/CUDA) |
| **Model Inference is Sync** | faster-whisper, MarianMT are synchronous |
| **Complexity Increase** | Async + ML models = callback hell |
| **Debugging Harder** | Async stack traces are painful |

### Architecture Comparison

```python
# Current: ThreadPool (works well)
from concurrent.futures import ThreadPoolExecutor

def process_segment(segment):
    text = model.transcribe(segment)  # Releases GIL
    return text

with ThreadPoolExecutor(4) as executor:
    results = executor.map(process_segment, segments)
# Simple, debuggable, works with sync ML models


# Proposed: AsyncIO (more complex, same result)
import asyncio

async def process_segment(segment):
    # Must run sync model in executor
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(
        None,  # Default executor
        model.transcribe,
        segment
    )
    return text

# Same GIL behavior, more complexity
```

### When AsyncIO Helps

| Scenario | ThreadPool | AsyncIO |
|----------|------------|---------|
| Pure Python CPU work | GIL contention | ✅ Better |
| I/O waiting (network) | Threads waste memory | ✅ Better |
| ML inference (C++/CUDA) | ✅ Releases GIL | Same |
| Many concurrent connections | Limited by memory | ✅ Better |

**Current pipeline**: ML inference releases GIL → ThreadPool is fine

### Verdict: ❌ Not Recommended (Over-Engineering)

The current ThreadPool approach is appropriate for CPU-bound ML inference.

---

## 6. Revised Metrics (TTFT, Lag, Stability)

### Proposal Summary
Measure Time to First Token, Ear-to-Voice Lag, and Stability Score.

### Evaluation

| Metric | Value | Current | Target | Measurement |
|--------|-------|---------|--------|-------------|
| **TTFT** | < 1.5s | ~5s | 1.5s | Speech start → First word display |
| **Lag** | < 500ms | ~700ms | 500ms | Speech end → Translation complete |
| **Stability** | < 10% changes | N/A (no streaming) | 10% | Words that change before final |

### Assessment

**TTFT < 1.5s**: Achievable with incremental ASR (draft mode)
**Lag < 500ms**: Already achievable (~700ms current, can optimize)
**Stability < 10%**: Very hard with streaming - expect 20-40% for incremental approaches

---

## 7. Implementation Roadmap

### Phase 1: Draft Mode ASR (High Value, Medium Effort)

```python
class StreamingPipeline:
    def __init__(self):
        self.asr = FasterWhisperASR()
        self.vad = SileroVAD()
        self.chunk_buffer = []
        
    async def run(self):
        async for audio_chunk in self.audio_stream:
            self.chunk_buffer.append(audio_chunk)
            
            # Draft mode: Every 2 seconds
            if self._buffer_duration() >= 2.0:
                draft = await self._get_draft()
                self.ui.show_draft(draft)  # Grey, italic
            
            # Final mode: VAD silence
            if self.vad.is_silence(audio_chunk):
                final = await self._get_final()
                self.ui.show_final(final)  # Black, solid
                self.chunk_buffer.clear()
```

**Timeline**: 1-2 weeks
**Risk**: Quality degradation on drafts
**Rollback**: Easy (disable draft mode)

### Phase 2: Optimized Final Mode (Medium Value, Low Effort)

- Reduce `MAX_SEGMENT_DURATION_MS` from 8000 → 4000
- Optimize model warm-up
- Add memory pinning

**Timeline**: 2-3 days
**Risk**: None
**Rollback**: Config change

### Phase 3: Adaptive Quality (Low Value, High Effort)

- Wait-k translation (requires model research)
- True streaming ASR (requires model change)

**Timeline**: 2-3 months R&D
**Risk**: High
**Recommendation**: Defer

---

## 8. Summary Evaluation Table

| Suggestion | Value | Effort | Risk | Verdict |
|------------|-------|--------|------|---------|
| **Incremental ASR** | High | Medium | Medium | ✅ Implement (Hybrid mode) |
| **Wait-k Translation** | Medium | High | High | ❌ Defer (model limitations) |
| **Compute-IO Overlap** | Low | Low | Low | ✅ Already done |
| **AsyncIO Architecture** | Low | Medium | Low | ❌ Over-engineering |
| **New Metrics** | High | Low | None | ✅ Adopt immediately |
| **Streaming UI** | High | Medium | Low | ✅ Required for drafts |

---

## 9. Final Recommendation

**Do NOT rewrite `orchestrator_parallel.py` into a streaming pipeline yet.**

Instead, implement a **Hybrid Mode**:

```python
class HybridPipeline:
    """
    Combines batch accuracy with streaming responsiveness
    """
    
    MODES = {
        'batch': FullSegmentMode(),      # Current behavior
        'streaming': IncrementalMode(),   # Draft + Final
    }
    
    def __init__(self, mode='streaming'):
        self.mode = self.MODES[mode]
        
    async def process(self, audio_stream):
        if self.mode == 'streaming':
            # Show drafts every 2s
            # Show final on silence
            return self._streaming_process(audio_stream)
        else:
            # Wait for silence, process full segment
            return self._batch_process(audio_stream)
```

**Benefits**:
- Preserves current quality for batch mode
- Adds responsiveness for real-time mode
- Easy A/B testing
- Gradual rollout

---

## 10. References

- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Whisper streaming research: https://github.com/ufal/whisper_streaming
- Wait-k translation: Gu et al., "Learning to Translate in Real-time with Neural Machine Translation" (2017)
- MarianMT: https://marian-nmt.github.io/

---

*Evaluation document for architectural decision-making.*
