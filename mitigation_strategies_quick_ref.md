# Risk Mitigation Strategies - Quick Reference

## Critical Risks (Immediate Action Required)

### R1: End-to-End Latency >500ms
**Quick Fix:**
- Use 200ms audio chunks
- Implement streaming ASR (Whisper streaming)
- Use WebSocket for cloud APIs
- Target: <300ms for edge, <500ms for cloud

### R2: Speech Recognition Errors
**Quick Fix:**
- Add RNNoise for noise suppression
- Use Whisper Small (good balance)
- Implement confidence threshold (0.7)
- Fall back to cloud when confidence <0.7

### R3: Translation Quality (Asian Languages)
**Quick Fix:**
- Use NLLB-200-distilled-600M
- Maintain 3-sentence context window
- Post-process named entities
- Allow user glossary

### R4: Edge Model RAM Requirements
**Quick Fix:**
- Use INT8 quantization (4x reduction)
- Load models on-demand
- Start with Whisper Tiny (39MB)
- Memory map large models

### R5: Real-time CPU Usage
**Quick Fix:**
- Use GPU if available (CUDA/MPS)
- Implement adaptive quality
- Lower process priority
- Batch process when possible

### R6: PyAudio Installation Issues
**Quick Fix:**
- Use `sounddevice` instead (better wheels)
- Pre-built wheels in distribution
- Bundle PortAudio
- Provide conda environment

### R7: Large Model Downloads
**Quick Fix:**
- Bundle Whisper Tiny (39MB) in installer
- Progressive download in background
- Resume support for downloads
- CDN with multiple mirrors

### R8: Processing Backlog
**Quick Fix:**
- Drop audio older than 5 seconds
- Implement priority queue
- Alert user when overloaded
- Switch to faster model under load

### R9: Battery Impact
**Quick Fix:**
- Detect battery mode
- Reduce processing to 50% when on battery
- Prefer cloud processing on battery
- Allow system sleep

### R10: UI Freezing
**Quick Fix:**
- Move all processing to QThread
- Use asyncio for async operations
- Update UI at 30fps max
- Show progress indicators

---

## High Risks (Action Required)

### R11: Buffer Underruns
**Mitigation:**
- Increase buffer size to 100ms
- Implement jitter buffer
- Monitor buffer levels

### R12: Cloud API Latency Spikes
**Mitigation:**
- Implement timeout (3s)
- Cache frequent requests
- Use edge fallback

### R13: Code-Switching Failures
**Mitigation:**
- Use multilingual models
- Detect language per utterance
- Allow manual language selection

### R14: Memory Leaks
**Mitigation:**
- Profile with memory_profiler
- Use weakrefs for callbacks
- Periodic garbage collection
- Monitor memory in telemetry

### R15: macOS System Audio Capture
**Mitigation:**
- Document BlackHole installation
- Request screen recording permission
- Provide setup wizard
- Test on clean macOS install

### R16: Apple Silicon Optimization
**Mitigation:**
- Use PyTorch MPS backend
- Test on M1 Pro specifically
- Use ARM64 native libraries
- Avoid Rosetta translation

### R17: macOS Virtual Audio Driver
**Mitigation:**
- Automate BlackHole setup
- Provide uninstall script
- Handle permission gracefully

### R18: Qt/PyQt Packaging
**Mitigation:**
- Use PyInstaller with --onefile
- Test on clean Windows/macOS
- Include all Qt plugins
- Sign binaries for macOS

### R19: Memory Leak Accumulation
**Mitigation:**
- Run 8-hour stress tests
- Monitor with psutil
- Implement max session duration
- Auto-restart on memory threshold

### R20: GPU Acceleration Unavailable
**Mitigation:**
- Detect GPU at runtime
- Provide CPU-optimized models
- Warn users about performance
- Offer cloud processing option

### R21: Context Loss in Translation
**Mitigation:**
- Use 3-sentence sliding window
- Overlap context between chunks
- Cache entity translations

### R22: Named Entity Mistranslation
**Mitigation:**
- Use spaCy NER
- Maintain entity dictionary
- Allow user corrections
- Don't translate capitalized words

---

## Recommended Tech Stack

### Audio Capture
```python
# Recommended: sounddevice
import sounddevice as sd
# Better cross-platform support than PyAudio
# Pre-built wheels available
```

### ASR
```python
# Recommended: faster-whisper (CTranslate2)
from faster_whisper import WhisperModel
model = WhisperModel("small", compute_type="int8")
# 4x faster than original Whisper
# INT8 quantization reduces memory
```

### Translation
```python
# Recommended: transformers with NLLB
translator = pipeline("translation", model="facebook/nllb-200-distilled-600M")
# Good quality, reasonable size
```

### GUI
```python
# Recommended: PyQt6
from PyQt6.QtWidgets import QApplication
# Modern, well-documented, cross-platform
```

### Packaging
```python
# Recommended: PyInstaller
pyinstaller --onefile --windowed app.py
# For Windows and macOS
```

---

## Testing Checklist

### Performance Tests
- [ ] Measure latency with 100 utterances
- [ ] Test with background noise
- [ ] Benchmark on M1 Pro
- [ ] Benchmark on typical Windows laptop
- [ ] Test 8-hour continuous operation

### Accuracy Tests
- [ ] Test 100 sentences per language pair
- [ ] Include technical vocabulary
- [ ] Test with different accents
- [ ] Measure WER and BLEU scores

### Compatibility Tests
- [ ] Windows 10/11 clean install
- [ ] macOS Intel clean install
- [ ] macOS Apple Silicon clean install
- [ ] Different audio devices
- [ ] Different Python versions

### Stress Tests
- [ ] Rapid speech input
- [ ] Multiple audio sources
- [ ] Low memory conditions
- [ ] Network interruptions
- [ ] Thermal throttling

---

## Monitoring Metrics

### Critical Metrics
1. End-to-end latency (p50, p95, p99)
2. ASR confidence scores
3. CPU usage percentage
4. Memory usage (MB)
5. Error rate by component

### Alert Thresholds
| Metric | Warning | Critical |
|--------|---------|----------|
| Latency | >1s | >2s |
| Memory | >80% | >95% |
| CPU | >80% | >95% |
| ASR Confidence | <70% | <50% |
| Error Rate | >5% | >10% |

---

## Emergency Fallbacks

### If Edge Processing Fails
1. Switch to cloud API immediately
2. Notify user of mode change
3. Queue audio for later processing
4. Log failure for analysis

### If Cloud API Fails
1. Switch to edge processing
2. Reduce quality if needed
3. Retry cloud with exponential backoff
4. Notify user of degraded service

### If Both Fail
1. Save audio to disk
2. Notify user of failure
3. Offer batch processing later
4. Provide manual export option

---

## Resource Requirements Summary

### Minimum Requirements
- CPU: 4 cores, 2.0 GHz
- RAM: 4 GB
- Storage: 2 GB
- OS: Windows 10 / macOS 10.15

### Recommended Requirements
- CPU: 8 cores, 2.5 GHz
- RAM: 8 GB
- Storage: 5 GB
- GPU: CUDA or MPS compatible
- OS: Windows 11 / macOS 12+

### Development Requirements
- Python 3.9+
- PyTorch 2.0+
- 10 GB disk space (for all models)
- Good internet connection
