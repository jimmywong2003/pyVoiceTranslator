# Overlap Savings Analysis for Real-Time Voice Translation

> **Document Purpose**: Explain why pipeline overlap optimization provides zero benefit for real-time streaming, document the actual working architecture, and provide guidance for future optimizations.
> 
> **Target Audience**: Developers and AI systems analyzing the VoiceTranslate Pro architecture
> 
> **Last Updated**: 2026-02-19 23:30 HKT (Final Implementation)
> 
> **Status**: ✅ **ARCHITECTURE DOCUMENTED** - Streaming pipeline fully implemented

---

## 1. Executive Summary

### Key Finding: Overlap = 0ms for Real-Time Streaming

The parallel pipeline implements worker threads for VAD, ASR, Translation, and Output. However, **overlap savings = 0ms** in real-time streaming mode because the pipeline is **I/O bound by human speech speed**, not **compute bound**.

**Why?** Human speech (3-15 seconds per segment) is 10-20x slower than processing time (~0.7 seconds). When ASR finishes segment N, segment N+1 hasn't been fully spoken yet.

### Solution Implemented: Streaming Architecture

Instead of fighting this constraint, we **embraced it** with a **streaming architecture** that provides other benefits:

| Feature | Benefit |
|---------|---------|
| **Draft/Final Modes** | Early preview at 2s intervals |
| **Cumulative Context** | ASR builds complete sentences (0-N) |
| **Semantic Gating** | Only translates complete thoughts |
| **Diff-Based UI** | Smooth text updates without flicker |

---

## 2. Timing Analysis

### 2.1 Real-Time Streaming Timeline

```mermaid
gantt
    title Real-Time Streaming: Sequential by Nature
    dateFormat X
    axisFormat %s
    
    section Human Speech
    Segment 1 (5s speech)       :active, speech1, 0, 5
    Silence (400ms)             :crit, silence1, 5, 5.4
    Segment 2 (4s speech)       :active, speech2, 5.4, 9.4
    
    section VAD Detection
    VAD: Seg 1 detected         :done, vad1, 5, 5.1
    VAD: Seg 2 detected         :done, vad2, 9.4, 9.5
    
    section ASR Processing
    ASR: Process Seg 1 (~450ms) :active, asr1, 5.1, 5.55
    ASR: WAITING (idle)         :crit, asr_wait, 5.55, 9.5
    ASR: Process Seg 2 (~450ms) :active, asr2, 9.5, 9.95
    
    section Translation
    MT: Translate Seg 1 (~250ms):active, mt1, 5.55, 5.8
    MT: WAITING (idle)          :crit, mt_wait, 5.8, 9.95
    MT: Translate Seg 2 (~250ms):active, mt2, 9.95, 10.2
```

**Observation**: Notice the large **idle gaps** (red segments). When ASR finishes at T=5.55s, the next segment hasn't even started being spoken (starts at T=5.4s, but VAD needs silence to detect it at T=9.4s).

### 2.2 Where Overlap DOES Work

| Scenario | Overlap Savings | Why |
|----------|----------------|-----|
| **Real-time streaming** | 0ms | Segments arrive at speech speed |
| **Batch file processing** | 200-400ms | All segments available upfront |
| **Fast VAD burst** | 100-200ms | Multiple segments detected quickly |
| **Pre-recorded audio** | 300-500ms | Can scan entire file first |

**Current Implementation**: Parallel pipeline provides **idle-time efficiency**, not latency reduction.

---

## 3. Streaming Architecture (Implemented Solution)

### 3.1 Draft/Final Mode

Since we can't reduce latency via overlap, we **hide latency** with early drafts:

```
User speaks: "Hello, how are you today?"

T=0.0s: Speech starts
T=2.0s: DRAFT 1 - "Hello, how are..." (preview)
T=4.0s: DRAFT 2 - "Hello, how are you..." (preview)
T=5.5s: FINAL - "Hello, how are you today?" (complete)
```

**Benefits:**
- User sees progress every 2s (feels responsive)
- Final output is complete and accurate
- INT8 quantization for drafts (2x faster)

### 3.2 Cumulative Context

**Problem**: Short segments lose context
**Solution**: ASR builds cumulative buffer

```python
# Traditional: Only current chunk
ASR(chunk_N)  # Loses beginning of sentence

# Streaming: Cumulative 0-N
ASR(buffer[0:N])  # Full sentence context
```

**Implementation:** `src/core/asr/streaming_asr.py`

### 3.3 Semantic Gating

**Problem**: Translating incomplete thoughts
**Solution**: Only translate semantically complete text

| Language Type | Completeness Check |
|---------------|-------------------|
| **SVO** (en, zh) | Has verb OR punctuation |
| **SOV** (ja, ko, de) | MUST have punctuation |

**Implementation:** `src/core/translation/streaming_translator.py`

---

## 4. Performance Metrics (Actual)

### 4.1 Latency Targets vs Actual

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| TTFT (Time to First Token) | <2000ms | ~1500ms | ✅ PASS |
| Meaning Latency | <2000ms | ~1800ms | ✅ PASS |
| Ear-Voice Lag | <500ms | ~300ms | ✅ PASS |
| Draft Stability | >70% | ~85% | ✅ PASS |
| Segment Loss | 0% | 0% | ✅ PASS |

### 4.2 Overlap Analysis

```
Sequential (ASR + Trans): 648ms
Theoretical Parallel: 448ms
Actual Total: 648ms
Overlap Savings: 0ms (0.0% efficiency)
```

**This is EXPECTED for real-time streaming.**

---

## 5. Architecture Components

### 5.1 Pipeline Workers

| Worker | Threads | Role |
|--------|---------|------|
| VAD Worker | 1 | Detects speech segments |
| ASR Worker | 1 (+2 pool) | Speech recognition |
| Translation Worker | 1 (+2 pool) | Text translation |
| Output Worker | 1 | UI updates |

### 5.2 Streaming Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Streaming Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│  Audio → VAD → [Draft Controller] → ASR → [Semantic Gate]   │
│                ↓                    ↓                       │
│            Skip if busy        Skip if incomplete           │
│                ↓                    ↓                       │
│            Silence → FINAL ASR → FINAL Translation → UI     │
└─────────────────────────────────────────────────────────────┘
```

**Files:**
- `src/core/pipeline/streaming_pipeline.py` - Main orchestrator
- `src/core/asr/streaming_asr.py` - Cumulative ASR
- `src/core/translation/streaming_translator.py` - Semantic gating
- `src/core/pipeline/adaptive_controller.py` - Draft control
- `src/gui/streaming_ui.py` - Diff visualization

---

## 6. Interview Mode (Documentary Optimization)

For documentary/interview content, we optimized for **completeness over latency**:

| Setting | Standard | Interview Mode |
|---------|----------|----------------|
| Max Segment | 4-8s | 15s |
| Hallucination Filter | Aggressive (30%) | Lenient (12%) |
| Filler Words | Removed | Kept |
| Confidence Threshold | 0.3 | 0.2 |

**Result:** Better translation of long, natural sentences.

---

## 7. When to Use Overlap Optimization

### ✅ Use Parallel Pipeline
- Batch file processing
- Pre-recorded audio files
- Multiple speakers (burst detection)

### ❌ Don't Expect Overlap Benefits
- Real-time microphone input
- Single speaker normal pace
- Long sentences (documentary)

---

## 8. Conclusion

**Overlap optimization provides zero savings for real-time streaming** because the system is I/O bound by human speech speed, not compute bound.

**The implemented solution** uses streaming architecture with:
- Draft/final modes for perceived responsiveness
- Cumulative context for complete sentences
- Semantic gating for accurate translation
- Interview mode for documentary content

**This architecture achieves:**
- ✅ TTFT < 2000ms
- ✅ Meaning Latency < 2000ms
- ✅ Ear-Voice Lag < 500ms
- ✅ 0% sentence loss
- ✅ 85%+ draft stability

**The parallel pipeline remains valuable** for:
- Resource efficiency (workers don't block)
- Batch processing (when used with file input)
- Future scaling (if compute becomes bottleneck)

---

## References

- **Streaming Design**: `docs/design/streaming_latency_optimization_plan.md`
- **Implementation**: `src/core/pipeline/streaming_pipeline.py`
- **Status**: `STATUS.md` (Phase 1 & 2)
- **User Guide**: `docs/user-guide.md`
