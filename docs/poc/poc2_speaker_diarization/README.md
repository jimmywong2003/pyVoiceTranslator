# PoC 2: Speaker Diarization Integration

**Objective:** Test turn-based speaker detection with real audio and measure latency impact.

**Critical Test:** Must use REAL audio buffers (not empty arrays) for accurate latency benchmarks.

---

## Tests

1. **test_latency.py** - CRITICAL: Real audio latency measurement
2. **test_integration.py** - Integration with streaming pipeline
3. **speaker_test.py** - Turn-based diarization logic

---

## Success Criteria

- [ ] Speaker detection adds < 50ms latency
- [ ] Works with 2-4 speaker scenarios
- [ ] Can coexist with draft/final streaming modes
- [ ] Thread-safe operation verified

## Fallback

If latency > 50ms, delay speaker recognition to V2 (minutes without speaker ID).
