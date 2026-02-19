# Streaming Latency Optimization - Design Plan

> **Status**: Draft - Pending Review  
> **Priority**: High (Real-time Mode)  
> **Effort**: 2-3 weeks  
> **Last Updated**: 2026-02-19

---

## 1. Executive Summary

### Current State
- **Throughput Overlap**: 0% (architecturally correct for real-time)
- **End-to-End Latency**: ~700-850ms after speech ends
- **Time to First Token (TTFT)**: ~5s (wait for full sentence)
- **User Experience**: Wait for silence → See translation

### Target State
- **TTFT**: < 2s (show draft while speaking)
- **End-to-End Latency**: < 500ms (optimize processing)
- **User Experience**: See draft text appear while speaking, final on silence
- **Quality**: No degradation for final output

### Approach: Hybrid Streaming Mode
Combine batch accuracy with streaming responsiveness:
1. **Draft Mode**: Show intermediate results every 2 seconds (low confidence)
2. **Final Mode**: Accurate translation on VAD silence (high confidence)

---

## 2. Background & Problem Statement

### 2.1 Why Current Overlap = 0ms

See detailed analysis: `docs/overlap_think_on_real_time_translator.md`

```
Human Speech:     [████████████ 5s ████████████]silence[████ 4s ████]
Processing:       WAIT → ASR(0.5s) → MT(0.3s) → Output
                  ^^^^^^
                  5s waiting for speech!

Issue: Processing (0.8s) < Speech duration (5s) → No overlap possible
```

### 2.2 The Real Opportunity: Intra-Segment Overlap

Instead of waiting for silence, process audio **while** it's being spoken.

```
Current (Sequential):
Speech:  [████████████████████] (5s)
Process:                         [ASR+MT] (0.8s) → Output at 5.8s

Proposed (Overlapped):
Speech:  [████████████████████] (5s)
Draft 1:      [ASR] (0.5s) → "Hello..." at 2s
Draft 2:           [ASR] (0.5s) → "Hello world..." at 3.5s
Draft 3:                [ASR] (0.5s) → "Hello world today" at 5s
Final:                              [MT] (0.3s) → "Hola mundo hoy" at 5.3s
```

---

## 3. Architecture Changes

### 3.1 New Component: StreamingASR

**File**: `src/core/asr/streaming_asr.py`

```python
class StreamingASR:
    """
    Hybrid ASR that produces draft and final results.
    
    Draft: Low-confidence intermediate transcription
    Final: High-confidence complete transcription
    """
    
    def __init__(self, base_asr: FasterWhisperASR):
        self.base_asr = base_asr
        self.chunk_buffer = []
        self.draft_interval_ms = 2000  # Draft every 2s
        
    async def transcribe_stream(
        self, 
        audio_stream: AsyncIterator[np.ndarray]
    ) -> AsyncIterator[ASRResult]:
        """
        Yields:
            ASRResult(text, is_final=False, confidence=0.6)  # Draft
            ASRResult(text, is_final=True, confidence=0.9)   # Final
        """
        async for chunk in audio_stream:
            self.chunk_buffer.append(chunk)
            
            # Draft mode: Every 2 seconds of accumulated audio
            if self._buffer_duration() >= self.draft_interval_ms:
                draft = await self._generate_draft()
                yield ASRResult(
                    text=draft,
                    is_final=False,
                    confidence=0.6,
                    timestamp=time.time()
                )
            
            # Final mode: VAD silence detected
            if self.vad.is_silence(chunk):
                final = await self._generate_final()
                yield ASRResult(
                    text=final,
                    is_final=True,
                    confidence=0.9,
                    timestamp=time.time()
                )
                self.chunk_buffer.clear()
    
    async def _generate_draft(self) -> str:
        """Quick transcription of accumulated buffer."""
        audio = concatenate(self.chunk_buffer)
        # Use faster decoding for draft
        result = self.base_asr.transcribe(
            audio,
            beam_size=1,  # Faster, less accurate
            best_of=1,
            patience=1.0
        )
        return result.text
    
    async def _generate_final(self) -> str:
        """Full-quality transcription."""
        audio = concatenate(self.chunk_buffer)
        # Use standard decoding for final
        result = self.base_asr.transcribe(
            audio,
            beam_size=5,  # Slower, more accurate
            best_of=5,
            patience=2.0
        )
        return result.text
```

### 3.2 New Component: StreamingOrchestrator

**File**: `src/core/pipeline/orchestrator_streaming.py`

```python
class StreamingOrchestrator:
    """
    Orchestrates hybrid streaming pipeline.
    
    Flow:
        Audio Capture → VAD → StreamingASR → Translation → UI
                              ↓ (draft)     ↓ (draft)
                              ↓ (final)     ↓ (final)
    """
    
    def __init__(self, config: StreamingConfig):
        self.audio_capture = AudioCapture(config.audio)
        self.vad = SileroVAD(config.vad)
        self.asr = StreamingASR(FasterWhisperASR(config.asr))
        self.translator = MarianTranslator(config.translation)
        self.ui = StreamingUI()  # New UI component
        
    async def run(self):
        """Main streaming loop."""
        # Audio stream from microphone
        audio_stream = self.audio_capture.stream()
        
        # VAD-processed stream (detects speech/silence)
        vad_stream = self.vad.process_stream(audio_stream)
        
        # ASR produces draft and final results
        async for asr_result in self.asr.transcribe_stream(vad_stream):
            
            if not asr_result.is_final:
                # Draft: Show in UI without translation (too unstable)
                self.ui.show_draft(asr_result.text)
                
            else:
                # Final: Translate and show
                translation = await self.translator.translate(asr_result.text)
                self.ui.show_final(
                    source=asr_result.text,
                    translation=translation,
                    latency=time.time() - asr_result.timestamp
                )
```

### 3.3 New Component: StreamingUI

**File**: `src/gui/streaming_ui.py`

```python
class StreamingUI:
    """
    UI that handles draft (unstable) and final (stable) text.
    """
    
    def show_draft(self, text: str):
        """
        Display draft text:
        - Grey color
        - Italic font
        - May change
        """
        self.draft_label.setText(text)
        self.draft_label.setStyleSheet("color: grey; font-style: italic;")
        
    def show_final(self, source: str, translation: str, latency: float):
        """
        Display final translation:
        - Black color
        - Bold font
        - Stable
        - Show latency indicator
        """
        self.source_label.setText(source)
        self.translation_label.setText(translation)
        self.translation_label.setStyleSheet("color: black; font-weight: bold;")
        self.latency_indicator.setText(f"{latency*1000:.0f}ms")
        
        # Clear draft
        self.draft_label.clear()
```

---

## 4. Implementation Phases

### Phase 1: Metrics & Baseline (Week 1)

**Tasks**:
1. Add TTFT (Time to First Token) metric
2. Add Ear-to-Voice Lag metric
3. Add Stability Score metric
4. Reduce `MAX_SEGMENT_DURATION_MS` from 8000 → 4000

**Files to Modify**:
- `src/core/pipeline/orchestrator.py` - Add metrics logging
- `src/audio/vad/silero_vad_adaptive.py` - Update max segment
- `src/core/utils/latency_analyzer.py` - Add new metrics

**Success Criteria**:
- Metrics visible in logs
- Baseline established

```python
# New metrics to track
metrics = {
    'ttft_ms': 0,           # Speech start -> First output
    'ear_to_voice_ms': 0,   # Speech end -> Translation complete
    'draft_stability': 0.0,  # % of draft words that changed
    'final_quality': 0.0,    # BLEU score (optional)
}
```

### Phase 2: Hybrid Streaming ASR (Week 1-2)

**Tasks**:
1. Implement `StreamingASR` class
2. Add draft generation (every 2s)
3. Add final generation (on silence)
4. Unit tests

**Files to Create**:
- `src/core/asr/streaming_asr.py`
- `tests/test_streaming_asr.py`

**Key Design Decisions**:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Draft interval | 2 seconds | Balance between responsiveness and compute |
| Draft beam size | 1 | Faster inference, lower quality acceptable |
| Final beam size | 5 | Standard quality for final output |
| Draft confidence threshold | 0.6 | Don't show very uncertain text |
| Final confidence threshold | 0.9 | High confidence for committed text |

**Success Criteria**:
- Draft appears within 2.5s of speech start
- Final appears within 1s of silence
- Final quality matches current pipeline

### Phase 3: Streaming UI (Week 2)

**Tasks**:
1. Modify existing UI to support draft/final modes
2. Add visual indicators (color, font style)
3. Add latency display
4. User testing

**Files to Modify**:
- `src/gui/main.py` - Add streaming mode

**Visual Design**:

```
┌─────────────────────────────────────┐
│  VoiceTranslate Pro                 │
├─────────────────────────────────────┤
│                                     │
│  Source (Japanese):                 │
│  ┌─────────────────────────────┐   │
│  │ こんにちは世界               │   │  ← Final (Black, Bold)
│  └─────────────────────────────┘   │
│                                     │
│  Draft: こんにちは...              │   │  ← Draft (Grey, Italic)
│                                     │
│  Translation (English):             │
│  ┌─────────────────────────────┐   │
│  │ Hello world                 │   │  ← Final (Black, Bold)
│  └─────────────────────────────┘   │
│                                     │
│  Latency: 320ms    [Streaming ●]   │
│                                     │
└─────────────────────────────────────┘
```

### Phase 4: Integration & Testing (Week 3)

**Tasks**:
1. Integrate StreamingOrchestrator with existing pipeline
2. Add mode switch (Batch vs Streaming)
3. A/B testing with users
4. Performance optimization

**Files to Modify**:
- `src/app/main.py` - Add --streaming flag
- `src/core/pipeline/orchestrator_parallel.py` - Integrate streaming

**Configuration**:

```python
class PipelineConfig:
    # Existing options
    mode: str = "batch"  # or "streaming"
    
    # New streaming options
    streaming_config = {
        'draft_interval_ms': 2000,
        'draft_beam_size': 1,
        'final_beam_size': 5,
        'show_drafts': True,
        'min_draft_confidence': 0.6,
    }
```

---

## 5. Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Draft quality too low** | Medium | High | Don't translate drafts; show ASR only |
| **Compute overhead** | Medium | Medium | Draft every 2s, not every chunk; make toggleable |
| **User confusion** | Low | Medium | Clear visual distinction (grey vs black) |
| **Whisper inconsistency** | High | Medium | Deduplication logic for overlapping chunks |
| **Increased latency** | Low | High | Benchmark before/after; easy rollback |

### Risk: Whisper Inconsistency

**Problem**: Overlapping chunks may produce inconsistent text.

```python
# Chunk 1 (0-2s): "Hello world"
# Chunk 2 (0-4s): "Hello world today"
# Problem: Re-processing "Hello world" may yield different text!
```

**Mitigation**:
```python
def deduplicate(current: str, previous: str) -> str:
    """
    Find common prefix between current and previous draft.
    Only show new text.
    """
    common_len = common_prefix_length(current, previous)
    return current[common_len:]

# Draft 1: "Hello world"
# Draft 2: "Hello world today" -> dedupe -> " today"
```

---

## 6. Success Metrics

### 6.1 Latency Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **TTFT** | ~5000ms | < 2000ms | Speech start → First draft visible |
| **Ear-to-Voice Lag** | ~700ms | < 500ms | Silence → Final translation |
| **Draft Frequency** | N/A | Every 2s | Time between draft updates |

### 6.2 Quality Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Final WER** | Baseline | ≤ Baseline | Word Error Rate on final output |
| **Draft Stability** | N/A | > 80% | % of draft text that matches final |
| **User Satisfaction** | Baseline | +20% | User survey |

### 6.3 Performance Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **CPU Usage** | Baseline | < 150% | Draft adds ~50% overhead |
| **Memory Usage** | Baseline | < 120% | Buffer management |
| **Real-time Factor** | 0.1 | < 0.3 | Process time / Audio duration |

---

## 7. Alternative Approaches Considered

### 7.1 Rejected: Wait-k Translation

**Approach**: Start translating after k words received.

**Rejected Because**:
- MarianMT/NLLB don't support incremental inference
- Language pairs with different word order (JA↔EN) fail catastrophically
- High implementation complexity

See: `docs/evaluation_streaming_suggestions.md` Section 3

### 7.2 Rejected: Full AsyncIO Rewrite

**Approach**: Replace ThreadPool with AsyncIO.

**Rejected Because**:
- ML models (faster-whisper, MarianMT) release GIL during inference
- ThreadPool performance is equivalent for CPU-bound tasks
- AsyncIO adds complexity without benefit

See: `docs/evaluation_streaming_suggestions.md` Section 5

### 7.3 Selected: Hybrid Mode

**Why**:
- Preserves current quality for final output
- Adds responsiveness with drafts
- Easy to implement incrementally
- Can be toggled on/off
- Low risk, high value

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# test_streaming_asr.py

async def test_draft_generation():
    asr = StreamingASR(mock_base_asr)
    
    # Simulate 3 seconds of audio
    chunks = [audio_chunk] * 6  # 500ms chunks
    
    results = []
    async for result in asr.transcribe_stream(iter(chunks)):
        results.append(result)
    
    # Should have 1 draft at 2s, 1 draft at 4s, 1 final at 6s
    assert len(results) == 3
    assert results[0].is_final == False
    assert results[2].is_final == True

async def test_final_quality_preserved():
    """Ensure final output matches batch mode quality."""
    streaming_result = await streaming_asr.transcribe(audio)
    batch_result = await batch_asr.transcribe(audio)
    
    assert streaming_result.text == batch_result.text
```

### 8.2 Integration Tests

```python
# Test end-to-end pipeline
async def test_streaming_pipeline():
    pipeline = StreamingOrchestrator(config)
    
    # Feed test audio file
    results = []
    async for result in pipeline.process(test_audio_file):
        results.append(result)
    
    # Verify drafts precede final
    drafts = [r for r in results if not r.is_final]
    finals = [r for r in results if r.is_final]
    
    assert len(drafts) > 0
    assert len(finals) > 0
    assert all(d.timestamp < finals[0].timestamp for d in drafts)
```

### 8.3 User Testing

**A/B Test**:
- Group A: Current batch mode
- Group B: New streaming mode
- Measure: User satisfaction, perceived responsiveness

---

## 9. Documentation Updates

Files to update after implementation:

| Document | Update |
|----------|--------|
| `README.md` | Add streaming mode documentation |
| `STATUS.md` | Update performance metrics |
| `docs/overlap_think_on_real_time_translator.md` | Add streaming solution |
| `docs/task_breakdown_overlap_analysis.md` | Update overlap matrix |
| `docs/user-guide.md` | Add streaming mode usage |

---

## 10. References

- Evaluation Document: `docs/evaluation_streaming_suggestions.md`
- Overlap Analysis: `docs/overlap_think_on_real_time_translator.md`
- Task Breakdown: `docs/task_breakdown_overlap_analysis.md`

---

**Next Step**: Review and approve this design plan, then begin Phase 1 implementation.

---

*Design plan for streaming latency optimization.*
