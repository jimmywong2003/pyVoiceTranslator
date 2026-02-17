# Latency Analysis and Buffer Optimization Guide

## 📏 Maximum Sentence Length for Real-Time Translation

### Current System Constraints

| Component | Constraint | Impact |
|-----------|-----------|--------|
| **ASR Model** | 30-second audio chunks (Whisper) | Hard limit per segment |
| **Improved VAD** | 8-10 second max segment | Configurable, prevents overload |
| **Translation Model** | 512 tokens (MarianMT) | ~300-400 words typical |
| **Memory** | Model-dependent | Batch size affects capacity |

### Practical Maximums

```
Audio Duration:     8-10 seconds per segment (recommended)
Words per Segment:  15-25 words typical
Characters:         ~100-200 characters per segment
Processing Time:    500ms-2000ms (model-dependent)
```

### Model-Specific Performance

| Model | RTF* | Max Practical Duration | Latency |
|-------|------|------------------------|---------|
| tiny | 0.3x | 15-20s | 300-500ms |
| base | 0.5x | 10-12s | 500-800ms |
| small | 0.8x | 8-10s | 800-1200ms |
| medium | 1.5x | 5-8s | 1500-2500ms |

*RTF = Real-Time Factor (processing_time / audio_duration)
- RTF < 1.0 = Real-time capable
- RTF > 1.0 = Slower than real-time

### Sentence Splitting Strategy

The system automatically splits long sentences:

```python
# VAD Configuration
max_segment_duration_ms = 8000  # 8 seconds
pause_threshold_ms = 800        # Split at 800ms pauses

# Behavior:
# 1. Speech detected → Start accumulating
# 2. 8-second limit reached → Look for natural pause
# 3. Natural pause found → Split at pause
# 4. No pause found → Force split with 300ms overlap
```

**Example:**
```
Long sentence (15 seconds):
"Over the course of training the neural network might learn that their 
 footage is super important in predicting housing pricing so we'd multiply..."

Splits into:
- Segment 1 (8s): "Over the course of training the neural network..."
- Segment 2 (7s): "might learn that their footage is super important..."
```

---

## ⏱️ Measuring Latency

### Latency Components

```
Total Latency = Audio Capture + VAD + ASR + Translation + Output

Component         Typical Range    Measurement Point
─────────────────────────────────────────────────────────
Audio Capture     30-100ms         sounddevice callback → VAD
VAD Processing    10-50ms          audio chunk → speech detected
ASR Processing    200-2000ms       file write → transcription
Translation       100-500ms        text in → translation out
Pipeline Overhead 50-100ms         queue management, etc.
─────────────────────────────────────────────────────────
TOTAL             400-3000ms       speech ends → translation displayed
```

### Built-in Measurement

The system now includes comprehensive latency tracking:

```python
from voice_translation.src.utils.latency_analyzer import (
    LatencyAnalyzer, BufferOptimizer
)

# Create analyzer
analyzer = LatencyAnalyzer()

# Mark events during processing
def on_audio_captured(chunk):
    analyzer.start_segment(segment_id, audio_duration_ms=len(chunk)/16)

def on_vad_complete(segment):
    analyzer.mark_event(segment_id, "vad_end")

def on_asr_complete(result):
    analyzer.mark_event(segment_id, "asr_end")
    analyzer.update_metrics(
        segment_id,
        asr_latency_ms=result.processing_time,
        source_text_length=len(result.text)
    )

def on_translation_complete(text):
    analyzer.mark_event(segment_id, "translation_end")
    metrics = analyzer.finalize_segment(segment_id)
    
    # Real-time feedback
    if metrics.total_latency_ms > 2000:
        print(f"⚠️ High latency: {metrics.total_latency_ms:.0f}ms")
```

### Viewing Metrics

**During Runtime:**
```python
# Print summary
analyzer.print_summary()

# Output:
# ======================================================================
# 📊 LATENCY ANALYSIS SUMMARY
# ======================================================================
# Runtime: 120.5s
# Total Segments: 45
# Throughput: 22.4 segments/min
#
# --- Component Latencies ---
# VAD             : mean=  25.3ms, p95=  42.1ms, max=  58.3ms
# ASR             : mean= 542.1ms, p95= 892.4ms, max=1234.5ms
# TRANSLATION     : mean= 125.6ms, p95= 234.8ms, max= 345.2ms
#
# END-TO-END      : mean= 712.4ms, p95=1156.2ms, max=1589.3ms
#
# Real-Time Factor (RTF): 0.45x
#   (RTF < 1.0 = real-time capable, RTF > 1.0 = slower than real-time)
#   ✅ System is real-time capable
# ======================================================================
```

**Export for Analysis:**
```python
# Export to JSON
analyzer.export_json("latency_report.json")

# Analyze later
from voice_translation.src.utils.latency_analyzer import analyze_pipeline_performance
analyze_pipeline_performance("latency_report.json")
```

---

## 📦 Buffer Compensation Strategy

### Why Buffers Are Needed

```
Without Buffer:
Speech → [Capture] → [ASR 1s] → [Translate 0.5s] → Display
                          ↑
                    User waits 1.5s before seeing translation

With Buffer:
Speech → [Buffer 1s] → [Capture] → [ASR 1s] → [Translate 0.5s] → Display
        ↑
   Pre-fill buffer while processing
        
Result: User sees translation immediately when speech ends!
```

### Buffer Size Formula

```
Recommended Buffer = p95_latency + safety_margin

Where:
- p95_latency = 95th percentile of measured end-to-end latency
- safety_margin = 200ms (for jitter protection)

Example:
- Measured p95 latency: 1200ms
- Safety margin: 200ms
- Recommended buffer: 1400ms
```

### Dynamic Buffer Optimization

```python
from voice_translation.src.utils.latency_analyzer import BufferOptimizer

# Create optimizer
optimizer = BufferOptimizer(
    target_latency_ms=1000.0,  # Target 1s total latency
    max_buffer_ms=5000.0,      # Cap at 5s
    min_buffer_ms=500.0        # Minimum 500ms
)

# During processing
for segment in segments:
    latency = process_segment(segment)
    optimizer.report_latency(latency)
    
    # Get recommended buffer
    buffer_ms = optimizer.get_recommended_buffer_ms()
    print(f"Recommended buffer: {buffer_ms:.0f}ms")

# Check status
status = optimizer.get_status()
# {
#     "status": "optimized",  # or "degraded" if latency too high
#     "current_buffer_ms": 1400,
#     "p95_latency_ms": 1200,
#     "target_latency_ms": 1000
# }
```

### Buffer Size Recommendations

| System Specs | Recommended Buffer | Notes |
|--------------|-------------------|-------|
| M1/M2 Mac, tiny model | 500-800ms | Fast, minimal buffering |
| Intel CPU, base model | 800-1200ms | Balanced |
| Older CPU, small model | 1500-2500ms | Needs more buffering |
| GPU (CUDA), any model | 300-500ms | Fastest, minimal buffering |

---

## 🐛 Debugging and Analysis

### Enable Detailed Logging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Component-specific logging
logging.getLogger('voice_translation.src.pipeline').setLevel(logging.DEBUG)
logging.getLogger('audio_module.vad').setLevel(logging.DEBUG)
```

### Real-Time Debug Panel (GUI)

Add to your GUI initialization:

```python
from PySide6.QtWidgets import QLabel, QVBoxLayout

class DebugPanel(QWidget):
    def __init__(self, analyzer: LatencyAnalyzer):
        super().__init__()
        self.analyzer = analyzer
        
        layout = QVBoxLayout()
        
        # Real-time metrics
        self.rtf_label = QLabel("RTF: --")
        self.latency_label = QLabel("Latency: --")
        self.buffer_label = QLabel("Buffer: --")
        
        layout.addWidget(self.rtf_label)
        layout.addWidget(self.latency_label)
        layout.addWidget(self.buffer_label)
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(1000)  # Update every second
    
    def _update(self):
        summary = self.analyzer.get_summary()
        
        rtf = summary.get('real_time_factor', {}).get('mean', 0)
        self.rtf_label.setText(f"RTF: {rtf:.2f}x {'✅' if rtf < 1 else '⚠️'}")
        
        latency = summary.get('total_latency_ms', {}).get('mean', 0)
        self.latency_label.setText(f"Avg Latency: {latency:.0f}ms")
```

### Performance Bottleneck Detection

```python
def diagnose_performance(analyzer: LatencyAnalyzer):
    summary = analyzer.get_summary()
    
    # Check each component
    vad = summary.get('vad_latency_ms', {}).get('mean', 0)
    asr = summary.get('asr_latency_ms', {}).get('mean', 0)
    trans = summary.get('translation_latency_ms', {}).get('mean', 0)
    
    print("Performance Diagnosis:")
    print("-" * 40)
    
    if vad > 100:
        print("⚠️ VAD latency high (>100ms)")
        print("   💡 Consider simpler VAD model or reduce sensitivity")
    
    if asr > 1000:
        print("⚠️ ASR latency high (>1000ms)")
        print("   💡 Use smaller model (tiny/base instead of small/medium)")
        print("   💡 Enable GPU acceleration")
        print("   💡 Reduce max_segment_duration_ms")
    
    if trans > 500:
        print("⚠️ Translation latency high (>500ms)")
        print("   💡 Use lighter translation model")
        print("   💡 Enable translation caching")
    
    # Check RTF
    rtf = summary.get('real_time_factor', {}).get('mean', 0)
    if rtf > 1.0:
        print("\n🔴 System is NOT real-time capable")
        print(f"   RTF: {rtf:.2f}x (must be < 1.0)")
        print("   💡 Increase buffer size to compensate")
        print("   💡 Use faster ASR model")
```

### Exporting Detailed Metrics

```python
# Export after session
analyzer.export_json(f"session_{time.strftime('%Y%m%d_%H%M%S')}.json")

# File contents:
# {
#     "summary": {
#         "runtime_seconds": 125.5,
#         "total_segments": 52,
#         "vad_latency_ms": {"mean": 25.3, "p95": 42.1, ...},
#         "asr_latency_ms": {"mean": 542.1, "p95": 892.4, ...},
#         "real_time_factor": {"mean": 0.45, ...}
#     },
#     "segments": [
#         {
#             "segment_id": 1,
#             "timestamp": 1234567890.123,
#             "vad_latency_ms": 23.5,
#             "asr_latency_ms": 523.1,
#             "total_latency_ms": 712.4,
#             ...
#         },
#         ...
#     ]
# }
```

---

## 📊 Interpreting Results

### Real-Time Factor (RTF)

```
RTF = Processing Time / Audio Duration

RTF < 0.5:  Excellent - System is very fast
RTF 0.5-1.0: Good - System can keep up in real-time
RTF 1.0-2.0: Poor - System falling behind, needs larger buffer
RTF > 2.0:   Critical - Major performance issues
```

### Latency Guidelines

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| End-to-End | <500ms | 500-1000ms | >1000ms |
| ASR Only | <300ms | 300-800ms | >800ms |
| Translation | <200ms | 200-500ms | >500ms |
| VAD | <50ms | 50-100ms | >100ms |

### When to Adjust Buffers

```
Scenario 1: Low latency, stable RTF < 0.5
→ Buffer: 500ms (minimal)

Scenario 2: Moderate latency, RTF < 1.0
→ Buffer: 1000-1500ms (recommended)

Scenario 3: High latency spikes, RTF > 1.0 occasionally
→ Buffer: 2000-3000ms (compensate for spikes)

Scenario 4: Consistently RTF > 1.0
→ Buffer won't help! Need faster hardware or smaller model
```

---

## 🎯 Quick Reference

### Command-Line Analysis

```bash
# Run with latency analysis
python voice_translate_gui.py --analyze-latency

# Export detailed metrics
# (Use export button in GUI after session)

# Analyze exported JSON
python -c "
from voice_translation.src.utils.latency_analyzer import analyze_pipeline_performance
analyze_pipeline_performance('latency_session_20260217_143000.json')
"
```

### Optimal Settings by Hardware

```python
# High-end (M1/M2 Mac, GPU)
config = PipelineConfig(
    asr_model_size="small",
    max_segment_duration_ms=10000,
    # Buffer not critical, system is fast
)

# Mid-range (Modern Intel/AMD CPU)
config = PipelineConfig(
    asr_model_size="base",
    max_segment_duration_ms=8000,
    vad_lookback_ms=800,  # Slightly longer buffer
)

# Entry-level (Older CPU)
config = PipelineConfig(
    asr_model_size="tiny",
    max_segment_duration_ms=5000,
    vad_lookback_ms=1500,  # Larger buffer for slow processing
)
```

---

## Summary

1. **Maximum Sentence Length**: 8-10 seconds (configurable), automatically split if longer
2. **Measure Latency**: Use built-in `LatencyAnalyzer` class for component-level tracking
3. **Buffer Compensation**: Use `BufferOptimizer` to calculate required buffer size based on p95 latency + 200ms
4. **Debugging**: Enable logging, use debug panels, export JSON for detailed analysis

The system is designed to handle real-time translation with proper buffering and automatic sentence splitting for longer inputs!
