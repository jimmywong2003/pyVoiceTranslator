# Streaming Latency Optimization - Design Plan

> **Status**: Approved with Modifications  
> **Priority**: High (Real-time Mode)  
> **Effort**: 2-3 weeks  
> **Last Updated**: 2026-02-19 21:32 HKT (Rev 3 - Week 0 Critical Bug Fix Added)

---

## 1. Executive Summary

### Current State
- **Throughput Overlap**: 0% (architecturally correct for real-time)
- **End-to-End Latency**: ~700-850ms after speech ends
- **Time to First Token (TTFT)**: ~5s (wait for full sentence)
- **User Experience**: Wait for silence → See translation

### Target State
- **TTFT**: < 2s (show translation draft while speaking)
- **End-to-End Latency**: < 500ms (optimize processing)
- **User Experience**: See translated meaning appear while speaking, final on silence
- **Quality**: No degradation for final output
- **Data Integrity**: **0% sentence loss** (fix bug before optimization)

### ⚠️ CRITICAL: Week 0 - Fix Sentence Loss Bug First

**Before any streaming optimization, fix the sentence loss bug.**

| Issue | Impact | Solution |
|-------|--------|----------|
| Sentences dropped silently | User sees gaps in conversation | Add sequence tracking, queue monitoring |
| Unknown loss rate | Can't measure optimization impact | Stress test: 10-min, 0% loss requirement |
| Silent failures | Can't debug issues | Comprehensive error logging |

**Why this matters**: Optimizing a system that loses data is meaningless.

### Approach: Hybrid Streaming Mode with Partial Translation
Combine batch accuracy with streaming responsiveness:
1. **Draft Mode**: Show intermediate translations every 2 seconds (conditional on semantic completeness)
2. **Final Mode**: Accurate translation on VAD silence (high confidence)

**Critical Design Decisions (Revised)**:
| Aspect | Original | Revised | Rationale |
|--------|----------|---------|-----------|
| Draft Translation | No (ASR only) | **Yes (Conditional)** | Users need meaning, not just words |
| Draft Trigger | Every 2s | **Adaptive** | Skip if speech pauses briefly |
| Context Window | Chunk-based | **Cumulative** | Ensures grammatical consistency |
| Compute Strategy | Standard | **INT8 for Drafts** | Reduces 3x compute overhead |
| UI Transition | Replace | **Diff-based** | Smooth transition, highlight changes |

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
Speech:       [████████████████████] (5s)
Process:                              [ASR+MT] (0.8s) → Output at 5.8s

Proposed (Overlapped with Partial Translation):
Speech:       [████████████████████] (5s)
Draft ASR 1:       [ASR] (0.5s) → "Hello world"
Draft MT 1:            [MT] (0.25s) → "Hola mundo" at 2.75s ✓ MEANING!
Draft ASR 2:                [ASR] (0.5s) → "Hello world today"
Draft MT 2:                     [MT] (0.25s) → "Hola mundo hoy" at 4.5s
Final:                                        [ASR+MT] → "Hola mundo hoy" at 5.3s
```

---

## 3. Architecture Changes

### 3.1 New Component: StreamingASR

**File**: `src/core/asr/streaming_asr.py`

```python
class StreamingASR:
    """
    Hybrid ASR with cumulative context and adaptive drafting.
    
    Key Features:
    - Cumulative context: Draft N includes all audio from 0 to N
    - INT8 quantization for drafts (faster)
    - FP16/Standard for final (accurate)
    """
    
    def __init__(self, base_asr: FasterWhisperASR):
        self.base_asr = base_asr
        self.audio_buffer = []  # Cumulative buffer
        self.draft_interval_ms = 2000
        self.last_draft_time = 0
        
    async def transcribe_stream(
        self, 
        audio_stream: AsyncIterator[np.ndarray]
    ) -> AsyncIterator[ASRResult]:
        async for chunk in audio_stream:
            self.audio_buffer.append(chunk)
            current_time = self._buffer_duration()
            
            # Adaptive Draft: Only if enough new audio and speech continues
            if (current_time - self.last_draft_time >= self.draft_interval_ms and
                not self.vad.is_recent_pause(500)):  # Skip if paused recently
                
                draft = await self._generate_draft()
                yield ASRResult(
                    text=draft,
                    is_final=False,
                    confidence=0.6,
                    timestamp=time.time()
                )
                self.last_draft_time = current_time
            
            # Final on silence
            if self.vad.is_silence(chunk):
                final = await self._generate_final()
                yield ASRResult(
                    text=final,
                    is_final=True,
                    confidence=0.9,
                    timestamp=time.time()
                )
                self.audio_buffer.clear()
                self.last_draft_time = 0
    
    async def _generate_draft(self) -> str:
        """Fast draft with INT8 quantization."""
        # Cumulative context: Process all audio from start
        audio = concatenate(self.audio_buffer)
        result = self.base_asr.transcribe(
            audio,
            beam_size=1,
            best_of=1,
            patience=1.0,
            compute_type="int8"  # Faster for drafts
        )
        return result.text
    
    async def _generate_final(self) -> str:
        """High-quality final with standard precision."""
        audio = concatenate(self.audio_buffer)
        result = self.base_asr.transcribe(
            audio,
            beam_size=5,
            best_of=5,
            patience=2.0,
            compute_type="int8"  # Keep int8 for consistency
        )
        return result.text
```

### 3.2 New Component: StreamingTranslator with Semantic Gating

**File**: `src/core/translation/streaming_translator.py`

```python
class StreamingTranslator:
    """
    Translator with semantic completeness gating for drafts.
    
    Only translates drafts that contain complete semantic units:
    - Contains verb (action complete)
    - Ends with punctuation (phrase boundary)
    """
    
    def __init__(self, base_translator: MarianTranslator):
        self.base_translator = base_translator
        self.previous_draft = ""
        
    async def translate_streaming(
        self, 
        asr_result: ASRResult
    ) -> TranslationResult:
        if asr_result.is_final:
            # Final: Always translate with full quality
            translation = await self.base_translator.translate(
                asr_result.text,
                beam_size=5
            )
            return TranslationResult(
                text=translation,
                is_final=True,
                stability=1.0
            )
        else:
            # Draft: Only translate if semantically complete
            if self._is_semantically_complete(asr_result.text):
                translation = await self.base_translator.translate(
                    asr_result.text,
                    beam_size=1,  # Fast for drafts
                    int8=True
                )
                return TranslationResult(
                    text=translation,
                    is_final=False,
                    stability=self._calculate_stability(translation)
                )
            else:
                # Skip translation, return placeholder
                return TranslationResult(
                    text=None,  # Will show "..."
                    is_final=False,
                    stability=0.0
                )
    
    def _is_semantically_complete(self, text: str, target_lang: str) -> bool:
        """
        Check if text contains a complete thought worth translating.
        
        Rules:
        1. Contains verb (for SVO/SOV languages)
        2. Ends with punctuation (.!?)
        3. Minimum word count (2+ words)
        4. SOV language safety (wait for sentence end)
        """
        # Language-specific verb lists
        verbs = self._get_verbs_for_language(self.source_lang)
        
        has_verb = any(verb in text.lower() for verb in verbs)
        has_punctuation = any(text.endswith(p) for p in ['.', '!', '?', '。', '！', '？'])
        has_min_words = len(text.split()) >= 2
        
        # SOV language safety check
        # SOV languages (Japanese, Korean, German, Turkish) put verb at END
        # Translating before verb arrives = grammatical chaos
        SOV_LANGUAGES = ['ja', 'ko', 'de', 'tr']
        if target_lang in SOV_LANGUAGES:
            # Must wait for sentence end (punctuation) for SOV targets
            if not has_punctuation:
                return False
        
        return has_min_words and (has_verb or has_punctuation)
    
    def _calculate_stability(self, current: str) -> float:
        """
        Calculate stability score vs previous draft.
        Returns 0.0-1.0 (1.0 = identical to previous)
        """
        if not self.previous_draft:
            return 0.0
        
        # Use sequence similarity (difflib or rapidfuzz)
        similarity = SequenceMatcher(None, current, self.previous_draft).ratio()
        self.previous_draft = current
        return similarity
```

### 3.3 New Component: StreamingOrchestrator

**File**: `src/core/pipeline/orchestrator_streaming.py`

```python
class StreamingOrchestrator:
    """
    Orchestrates hybrid streaming pipeline with partial translation.
    
    Flow:
        Audio → VAD → StreamingASR → StreamingTranslator → StreamingUI
                         ↓ (draft)          ↓ (conditional)
                         ↓ (final)          ↓ (final)
    """
    
    def __init__(self, config: StreamingConfig):
        self.audio_capture = AudioCapture(config.audio)
        self.vad = SileroVAD(config.vad)
        self.asr = StreamingASR(FasterWhisperASR(config.asr))
        self.translator = StreamingTranslator(MarianTranslator(config.translation))
        self.ui = StreamingUI()
        
    async def run(self):
        audio_stream = self.audio_capture.stream()
        vad_stream = self.vad.process_stream(audio_stream)
        
        async for asr_result in self.asr.transcribe_stream(vad_stream):
            # Translate (conditional for drafts)
            trans_result = await self.translator.translate_streaming(asr_result)
            
            if not asr_result.is_final:
                # Draft: Show if translation available
                if trans_result.text:
                    self.ui.show_draft_translation(
                        source=asr_result.text,
                        translation=trans_result.text,
                        stability=trans_result.stability
                    )
                else:
                    # Semantically incomplete, show placeholder
                    self.ui.show_draft_placeholder(asr_result.text)
            else:
                # Final: Show with diff highlighting
                self.ui.show_final_with_diff(
                    source=asr_result.text,
                    translation=trans_result.text,
                    previous_draft=self.translator.previous_draft,
                    latency=time.time() - asr_result.timestamp
                )
```

### 3.4 New Component: StreamingUI with Diff Visualization

**File**: `src/gui/streaming_ui.py`

```python
class StreamingUI:
    """
    UI with diff-based transitions and stability indicators.
    """
    
    def __init__(self):
        self.previous_source = ""
        self.previous_translation = ""
        
    def show_draft_translation(self, source: str, translation: str, stability: float):
        """
        Display draft translation:
        - Grey color
        - Italic font
        - Stability indicator (fading)
        """
        self.source_label.setText(source)
        self.translation_label.setText(translation)
        
        # Stability affects opacity
        opacity = int(0.3 + 0.5 * stability)  # 0.3-0.8 based on stability
        self.translation_label.setStyleSheet(
            f"color: rgba(128, 128, 128, {opacity}); font-style: italic;"
        )
        
        # Stability indicator
        if stability < 0.5:
            self.stability_indicator.setText("● Unstable")
            self.stability_indicator.setStyleSheet("color: orange;")
        else:
            self.stability_indicator.setText("○ Stabilizing")
            self.stability_indicator.setStyleSheet("color: grey;")
    
    def show_draft_placeholder(self, partial_source: str):
        """Show when draft not yet translatable."""
        self.source_label.setText(partial_source + "...")
        self.translation_label.setText("Translating...")
        self.translation_label.setStyleSheet("color: lightgrey; font-style: italic;")
    
    def show_final_with_diff(self, source: str, translation: str, 
                             previous_draft: str, latency: float):
        """
        Display final with smooth transition from draft.
        
        If translation changed significantly from draft:
        - Highlight changed words briefly
        - Fade in final text
        """
        # Calculate diff
        diff_ratio = SequenceMatcher(None, translation, previous_draft).ratio()
        
        if diff_ratio > 0.8:
            # Minor change: Fade transition
            self._fade_transition(self.translation_label, translation)
        else:
            # Major change: Highlight differences
            self._highlight_changes(self.translation_label, 
                                   previous_draft, translation)
        
        self.source_label.setText(source)
        self.translation_label.setText(translation)
        self.translation_label.setStyleSheet("color: black; font-weight: bold;")
        self.latency_indicator.setText(f"{latency*1000:.0f}ms")
        
        # Clear stability indicator
        self.stability_indicator.clear()
        
        # Update state
        self.previous_source = source
        self.previous_translation = translation
    
    def _highlight_changes(self, label, old: str, new: str):
        """Highlight word-level changes between draft and final."""
        # Use diff-match-patch or similar
        # Flash changed words yellow briefly
        pass
```

---

## 4. Implementation Phases (Revised with Week 0)

### Phase 0: CRITICAL - Fix Sentence Loss Bug (Week 0) 🔴

**⚠️ MUST complete before any streaming optimization!**

**Why**: Optimizing a system that loses data is meaningless. User trust depends on 100% reliability.

**Tasks**:
1. **Add segment sequence tracking** - UUID per segment, trace full pipeline
2. **Add queue depth monitoring** - Alert if queue > 3 segments
3. **Add comprehensive error logging** - No silent failures anywhere
4. **Stress test** - 10-minute continuous speech, verify **0% sentence loss**
5. **Fix root cause** - Queue overflow? VAD threshold? Race condition?
6. **Platform-specific INT8 validation** - Intel i7 (OpenVINO), Mac M1 (CoreML)

**Files**:
- `src/core/pipeline/segment_tracker.py` - New: UUID-based tracing
- `src/core/utils/queue_monitor.py` - New: Queue depth alerts
- `src/core/utils/error_logger.py` - Enhanced: No silent failures
- `tests/stress_test_10min.py` - New: Continuous speech test

**Success Criteria**:
- Sentence Loss Rate: **0%** (verified over 10-minute test)
- Queue overflow: **Zero occurrences**
- Silent failures: **Zero occurrences**

**Platform Testing**:
| Platform | Hardware | INT8 Backend | Target Latency |
|----------|----------|--------------|----------------|
| Windows | Intel i7 + 16GB | OpenVINO | Draft: < 200ms |
| macOS | Mac M1 Pro 16GB | CoreML/NEON | Draft: < 150ms |

---

### Phase 1: Metrics & Adaptive Config (Week 1)

**Tasks**:
1. Add TTFT, Ear-to-Voice Lag, Stability Score metrics
2. Add compute monitoring (track ASR call frequency)
3. Reduce `MAX_SEGMENT_DURATION_MS` 8000 → 4000
4. Implement adaptive draft skipping

**Files**:
- `src/core/pipeline/orchestrator.py` - Add metrics
- `src/core/utils/metrics.py` - New metrics collection
- `src/audio/vad/silero_vad_adaptive.py` - Adaptive threshold

**Key Code**:
```python
class AdaptiveDraftController:
    """Decides when to trigger draft based on context."""
    
    def should_trigger_draft(self, buffer_duration, last_draft_time, vad_state):
        # Basic: Every 2 seconds
        if buffer_duration - last_draft_time < 2000:
            return False
        
        # Adaptive: Skip if recent pause detected
        if vad_state.recent_pause_ms > 500:
            return False
        
        # Adaptive: Skip if compute queue is backed up
        if self.compute_queue_depth > 2:
            return False
        
        return True
```

### Phase 2: Streaming ASR with Cumulative Context (Week 1-2)

**Tasks**:
1. Implement `StreamingASR` with cumulative buffer
2. Add INT8 quantization for drafts
3. Add deduplication logic
4. Unit tests

**Files**:
- `src/core/asr/streaming_asr.py`
- `tests/test_streaming_asr.py`

**Key Design Decisions (Revised)**:
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Context Window | **Cumulative (0-N)** | Ensures grammatical consistency |
| Draft Quantization | **INT8** | Reduces 3x compute overhead |
| Draft Beam Size | 1 | Fast inference acceptable for drafts |
| Final Beam Size | 5 | High quality for committed text |
| Deduplication | **Prefix-based** | Only show new text in UI |

### Phase 3: Partial Translation with Semantic Gating (Week 2)

**Tasks**:
1. Implement `StreamingTranslator` with verb/punctuation detection
2. Add language-specific semantic rules
3. Add stability scoring
4. Integration with ASR

**Files**:
- `src/core/translation/streaming_translator.py`
- `src/core/translation/semantic_rules.py` (language-specific)

**Semantic Completeness Rules**:
| Language | Verb List Example | Punctuation |
|----------|-------------------|-------------|
| English | "is", "are", "went", "have" | `.`, `!`, `?` |
| Japanese | "です", "ます", "行く", "食べる" | `。`, `！`, `？` |
| Chinese | "是", "去", "吃", "有" | `。`, `！`, `？` |

### Phase 4: Diff-Based UI (Week 2-3)

**Tasks**:
1. Implement diff visualization
2. Add stability indicators
3. Smooth transitions (fade/highlight)
4. User testing with A/B

**Files**:
- `src/gui/streaming_ui.py`
- `src/gui/diff_visualizer.py`

### Phase 5: Integration & Optimization (Week 3)

**Tasks**:
1. End-to-end integration
2. Compute optimization (monitor 3x overhead)
3. Configuration UI (toggle streaming mode)
4. Performance regression testing

---

## 5. Risk Assessment & Mitigation (Revised)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **3x Compute Overhead** | High | High | INT8 for drafts; adaptive skipping; monitor queue depth |
| **Draft Quality Too Low** | Medium | Medium | Cumulative context; semantic gating; stability scoring |
| **Translation Instability** | Medium | High | Only translate complete phrases; diff-based UI |
| **Whisper Inconsistency** | High | Medium | Cumulative context reduces variance; deduplication |
| **UI Snap Effect** | Medium | Medium | Diff visualization; highlight changes; fade transitions |
| **Language-Specific Issues** | Medium | Medium | Configurable semantic rules per language |

### Risk: 3x Compute Overhead (Critical)

**Problem**: 5s segment → 3 ASR calls (2s, 4s, 5s) = 3x compute

**Mitigation Strategy**:
```python
class ComputeGovernor:
    """Prevents compute overload."""
    
    def __init__(self):
        self.max_concurrent_asr = 2
        self.draft_quantization = "int8"
        self.skip_threshold = 0.8  # Skip draft if queue > 80%
    
    def should_run_draft(self, queue_depth: int) -> bool:
        # Skip drafts if system is overloaded
        if queue_depth >= self.max_concurrent_asr:
            return False
        return True
```

---

## 6. Success Metrics (Revised)

### 6.1 Latency & Data Integrity Metrics

| Metric | Current | Target | Priority | Measurement |
|--------|---------|--------|----------|-------------|
| **Sentence Loss Rate** | Bug exists | **0%** | 🔴 **P0 (Week 0)** | 10-min stress test |
| **TTFT (Meaning)** | ~5000ms | < 2000ms | 🟡 P1 (Week 2) | Speech start → First draft |
| **Meaning Latency** | ~5000ms | < 2000ms | 🟡 P1 (Week 2) | Speech start → Translation |
| **Ear-to-Voice Lag** | ~700ms | < 500ms | 🟢 P2 (Week 3) | Silence → Final output |
| **Draft Frequency** | N/A | Every 2s (adaptive) | 🟢 P2 (Week 2) | Time between drafts |

### 6.2 Quality Metrics

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| **Final WER** | Baseline | ≤ Baseline | P0 |
| **Draft Translation Accuracy** | N/A | > 70% vs Final | P1 |
| **Draft Stability** | N/A | > 70% similarity | P1 |
| **User Satisfaction** | Baseline | +20% | P0 |

### 6.3 Performance Metrics

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| **ASR Calls per Segment** | 1 | 2-3 | Monitor for 3x overhead |
| **CPU Usage** | Baseline | < 200% | Acceptable increase |
| **Draft Latency** | N/A | < 300ms | INT8 should help |

### 6.4 New Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Semantic Skip Rate** | % of drafts skipped (incomplete) | < 30% |
| **Translation Correction Rate** | % of drafts that change significantly | < 30% |
| **Compute Efficiency** | (Useful drafts) / (Total ASR calls) | > 60% |

---

## 7. Alternative Approaches (Updated)

### 7.1 Rejected: Draft Without Translation

**Why Rejected**: Showing ASR drafts without translation provides "listening feedback" but not "meaning." Users want to understand content, not just see that the system is working.

**Revised**: Conditional translation with semantic gating provides meaning when available.

### 7.2 Selected: Hybrid Mode with Partial Translation

**Why**:
- Provides meaning early (translated drafts)
- Maintains final quality (silence-triggered)
- Manageable compute overhead (INT8, adaptive)
- Smooth UX (diff visualization)

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# Test semantic completeness detection
async def test_semantic_gating():
    translator = StreamingTranslator(mock_mt)
    
    # Complete thought (has verb) → Translate
    result = await translator.translate_streaming(
        ASRResult("I went to store", is_final=False)
    )
    assert result.text is not None
    
    # Incomplete (no verb) → Skip
    result = await translator.translate_streaming(
        ASRResult("I the store", is_final=False)
    )
    assert result.text is None

# Test cumulative context
async def test_cumulative_context():
    asr = StreamingASR(mock_base)
    
    # Draft 1 at 2s
    asr.audio_buffer = [chunk_0_2s]
    draft1 = await asr._generate_draft()
    
    # Draft 2 at 4s (includes 0-2s + 2-4s)
    asr.audio_buffer = [chunk_0_2s, chunk_2_4s]
    draft2 = await asr._generate_draft()
    
    # Draft 2 should extend Draft 1, not replace
    assert draft1 in draft2 or draft2.startswith(draft1[:10])
```

### 8.2 Compute Benchmarks

```python
# Test compute overhead is manageable
async def test_compute_overhead():
    pipeline = StreamingOrchestrator(config)
    
    # Process 5s audio
    asr_calls = 0
    async for result in pipeline.process(test_5s_audio):
        if result.stage == "ASR":
            asr_calls += 1
    
    # Should be 2-3 calls, not > 5
    assert 2 <= asr_calls <= 3
```

### 8.3 User Testing

**A/B Test Protocol**:
- Group A: Current batch mode (wait for silence)
- Group B: Streaming mode with partial translation
- Tasks: Follow a conversation, respond to questions
- Metrics: Response time, comprehension accuracy, satisfaction

---

## 9. Implementation Checklist

### Week 0: CRITICAL - Fix Sentence Loss Bug 🔴
**⚠️ MUST complete before any optimization!**

- [ ] Add segment sequence tracking (UUID per segment)
- [ ] Add queue depth monitoring with alerts (>3 segments)
- [ ] Add comprehensive error logging (no silent failures)
- [ ] Stress test: 10-min continuous speech, verify **0% loss**
- [ ] Fix root cause (queue overflow? VAD threshold? race condition?)
- [ ] Platform test: Intel i7 (OpenVINO INT8 performance)
- [ ] Platform test: Mac M1 Pro (CoreML INT8 performance)

**Success Criteria**:
- [ ] Sentence Loss Rate = **0%**
- [ ] Zero queue overflow events
- [ ] Zero silent failures
- [ ] Draft latency < 200ms (i7), < 150ms (M1)

---

### Week 1
- [ ] Add TTFT, Lag, Stability, Meaning Latency metrics
- [ ] Implement adaptive draft controller
- [ ] Reduce segment duration 8000 → 4000
- [ ] Benchmark baseline (post Week 0 fixes)

### Week 2
- [ ] Implement StreamingASR (cumulative context, INT8)
- [ ] Implement StreamingTranslator (semantic gating + SOV rules)
- [ ] Add language-specific semantic rules (VERBS dict)
- [ ] Unit tests for new components

### Week 3
- [ ] Implement StreamingUI (diff visualization, stability indicators)
- [ ] End-to-end integration
- [ ] Compute overhead validation (target: < 1.5x)
- [ ] A/B user testing
- [ ] Documentation updates

---

## 10. References

- Evaluation Document: `docs/evaluation_streaming_suggestions.md`
- Overlap Analysis: `docs/overlap_think_on_real_time_translator.md`
- Task Breakdown: `docs/task_breakdown_overlap_analysis.md`
- Git Tag: `v1.0.0-stable` (baseline before streaming)

---

**Status**: Approved with modifications. Ready for implementation.

**Next Step**: Begin Phase 1 (Metrics & Adaptive Config).

---

*Design plan for streaming latency optimization - Revision 2.*
