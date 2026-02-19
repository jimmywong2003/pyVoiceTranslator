# Speech Loss Evaluation Guide

> **Purpose**: How to use timestamped logging to evaluate speech loss and pipeline timing
> 
> **Version**: v2.0.0
> 
> **Date**: 2026-02-19

---

## 📋 Overview

Timestamped logging provides millisecond-precision timestamps for all key pipeline events. This allows you to:

- **Detect speech loss**: Compare input audio duration vs processed segments
- **Measure latency**: Track time from speech detection to output
- **Identify bottlenecks**: See which stage takes longest
- **Verify completeness**: Ensure all speech is processed

---

## 🕐 Log Format

All timestamped logs follow this format:

```
YYYY-MM-DD HH:MM:SS.mmm | LEVEL    | logger_name | [TIMESTAMP] Event at unix_time.s | details
```

Example:
```
2026-02-19 23:45:12.345 | INFO     | src.core.pipeline.orchestrator_parallel | [TIMESTAMP] Segment created at 1708356312.345s | ID 1 | Duration 3240ms
2026-02-19 23:45:12.891 | INFO     | src.core.pipeline.orchestrator_parallel | [TIMESTAMP] ASR complete at 1708356312.891s | Segment 1 | 'Hello world...' (546ms)
2026-02-19 23:45:13.102 | INFO     | src.core.pipeline.orchestrator_parallel | [TIMESTAMP] Translation complete at 1708356313.102s | Segment 1 | 'Hello...' -> '你好...' (211ms)
2026-02-19 23:45:13.156 | INFO     | src.core.pipeline.orchestrator_parallel | [TIMESTAMP] Output emitted at 1708356313.156s | Segment 1 | 'Hello world...' -> '你好世界...' (811ms)
```

---

## 🔍 Key Events to Monitor

### 1. Segment Creation (VAD Detection)

```
[TIMESTAMP] Segment created at {unix_time}s | ID {segment_id} | Duration {ms}ms | Queue {size}
```

**Indicates**: Speech detected by VAD, segment queued for ASR

**Use for**:
- Counting total speech segments detected
- Measuring audio duration per segment
- Tracking queue depth

### 2. ASR Completion

```
[TIMESTAMP] ASR complete at {unix_time}s | Segment {id} | '{text}...' ({time}ms)
```

**Indicates**: Speech recognition finished

**Use for**:
- Measuring ASR latency
- Verifying text was recognized

### 3. ASR Filtered (Potential Loss)

```
[TIMESTAMP] ASR filtered at {unix_time}s | Segment {id} | ({time}ms) - skipping translation
```

**Indicates**: Segment failed quality check (hallucination, low confidence)

**Use for**:
- Identifying false positives (valid speech filtered)
- Tuning filter thresholds

### 4. Translation Completion

```
[TIMESTAMP] Translation complete at {unix_time}s | Segment {id} | '{source}...' -> '{target}...' ({time}ms)
```

**Indicates**: Translation finished

**Use for**:
- Measuring translation latency
- Verifying translation occurred

### 5. Output Emission

```
[TIMESTAMP] Output emitted at {unix_time}s | Segment {id} | '{source}...' -> '{target}...' ({total_time}ms)
```

**Indicates**: Final output delivered to user

**Use for**:
- Measuring end-to-end latency
- Verifying output delivery

---

## 📊 Speech Loss Calculation

### Method 1: Segment Count Comparison

```python
# Count segments in log
total_segments_created = count_log_lines("[TIMESTAMP] Segment created")
total_segments_emitted = count_log_lines("[TIMESTAMP] Output emitted")
total_segments_filtered = count_log_lines("[TIMESTAMP] ASR filtered")

# Calculate loss
segments_processed = total_segments_emitted + total_segments_filtered
segments_lost = total_segments_created - segments_processed
loss_rate = segments_lost / total_segments_created * 100

print(f"Total created: {total_segments_created}")
print(f"Total emitted: {total_segments_emitted}")
print(f"Total filtered: {total_segments_filtered}")
print(f"Loss rate: {loss_rate:.2f}%")
```

### Method 2: Audio Duration Comparison

```python
# Sum audio durations from segment creation logs
total_audio_duration_ms = sum(parse_durations_from_logs())

# Calculate expected vs actual
expected_segments = total_audio_duration_ms / average_segment_duration
actual_segments = count_emitted_segments()

loss_rate = (expected_segments - actual_segments) / expected_segments * 100
```

### Method 3: Timestamp Gap Analysis

```python
# Find gaps between segment emissions
emission_times = parse_emission_timestamps()

for i in range(1, len(emission_times)):
    gap = emission_times[i] - emission_times[i-1]
    if gap > threshold:  # e.g., > 5 seconds
        print(f"Gap detected: {gap:.1f}s between segments {i-1} and {i}")
```

---

## 🔧 Analyzing Log Files

### Save Log to File

```bash
# Run with logging to file
python src/gui/main.py 2>&1 | tee translation_log_$(date +%Y%m%d_%H%M%S).txt

# Or set log file in code
setup_timestamped_logging(log_file="translation.log")
```

### Parse Timestamps with Script

```python
#!/usr/bin/env python3
"""Parse translation logs for speech loss analysis."""

import re
from datetime import datetime

def parse_log_file(log_file):
    """Parse timestamped log file."""
    events = []
    
    with open(log_file) as f:
        for line in f:
            # Parse timestamp line
            if "[TIMESTAMP]" in line:
                event = parse_timestamp_line(line)
                events.append(event)
    
    return events

def parse_timestamp_line(line):
    """Extract data from timestamped log line."""
    # Example: "2026-02-19 23:45:12.345 | INFO | ... | [TIMESTAMP] Event at 1708356312.345s | ..."
    
    # Extract unix timestamp
    match = re.search(r'at (\d+\.\d+)s', line)
    unix_time = float(match.group(1)) if match else 0
    
    # Extract event type
    if "Segment created" in line:
        event_type = "created"
    elif "ASR complete" in line:
        event_type = "asr_complete"
    elif "ASR filtered" in line:
        event_type = "asr_filtered"
    elif "Translation complete" in line:
        event_type = "translation_complete"
    elif "Output emitted" in line:
        event_type = "emitted"
    else:
        event_type = "unknown"
    
    # Extract segment ID
    match = re.search(r'(?:Segment|ID) (\d+)', line)
    segment_id = int(match.group(1)) if match else -1
    
    return {
        'timestamp': unix_time,
        'type': event_type,
        'segment_id': segment_id,
        'raw': line.strip()
    }

def calculate_latency(events):
    """Calculate latencies between stages."""
    latencies = []
    
    # Group by segment ID
    segments = {}
    for event in events:
        sid = event['segment_id']
        if sid not in segments:
            segments[sid] = {}
        segments[sid][event['type']] = event['timestamp']
    
    # Calculate per-segment latency
    for sid, times in segments.items():
        if 'created' in times and 'emitted' in times:
            total_latency = times['emitted'] - times['created']
            latencies.append({
                'segment_id': sid,
                'total_ms': total_latency * 1000,
                'created': times['created'],
                'emitted': times['emitted']
            })
    
    return latencies

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parse_log.py <log_file>")
        return
    
    log_file = sys.argv[1]
    events = parse_log_file(log_file)
    
    # Count events
    created = len([e for e in events if e['type'] == 'created'])
    emitted = len([e for e in events if e['type'] == 'emitted'])
    filtered = len([e for e in events if e['type'] == 'asr_filtered'])
    
    print("=" * 60)
    print("Speech Loss Analysis")
    print("=" * 60)
    print(f"Total segments created: {created}")
    print(f"Total segments emitted: {emitted}")
    print(f"Total segments filtered: {filtered}")
    print(f"Loss rate: {(created - emitted - filtered) / created * 100:.2f}%")
    print()
    
    # Latency analysis
    latencies = calculate_latency(events)
    if latencies:
        avg_latency = sum(l['total_ms'] for l in latencies) / len(latencies)
        max_latency = max(l['total_ms'] for l in latencies)
        min_latency = min(l['total_ms'] for l in latencies)
        
        print("=" * 60)
        print("Latency Analysis")
        print("=" * 60)
        print(f"Average latency: {avg_latency:.1f}ms")
        print(f"Min latency: {min_latency:.1f}ms")
        print(f"Max latency: {max_latency:.1f}ms")

if __name__ == "__main__":
    main()
```

---

## 📈 Example Analysis

### Good Pipeline (0% Loss)

```
[TIMESTAMP] Segment created at 1000.000s | ID 1
[TIMESTAMP] ASR complete at 1000.546s | Segment 1
[TIMESTAMP] Translation complete at 1000.757s | Segment 1
[TIMESTAMP] Output emitted at 1000.811s | Segment 1

[TIMESTAMP] Segment created at 1005.234s | ID 2
[TIMESTAMP] ASR complete at 1005.780s | Segment 2
[TIMESTAMP] Translation complete at 1005.991s | Segment 2
[TIMESTAMP] Output emitted at 1006.045s | Segment 2

Analysis: 2 created, 2 emitted = 0% loss
```

### With Filtered Segments

```
[TIMESTAMP] Segment created at 1000.000s | ID 1
[TIMESTAMP] ASR filtered at 1000.546s | Segment 1

[TIMESTAMP] Segment created at 1005.234s | ID 2
[TIMESTAMP] ASR complete at 1005.780s | Segment 2
[TIMESTAMP] Output emitted at 1006.045s | Segment 2

Analysis: 2 created, 1 emitted, 1 filtered = 0% loss (filtered is intentional)
```

### With Speech Loss

```
[TIMESTAMP] Segment created at 1000.000s | ID 1
[TIMESTAMP] ASR complete at 1000.546s | Segment 1
[TIMESTAMP] Output emitted at 1000.811s | Segment 1

# Gap - no segment creation log for audio at 1003s-1008s

[TIMESTAMP] Segment created at 1009.000s | ID 2
[TIMESTAMP] Output emitted at 1009.811s | Segment 2

Analysis: Audio gap of ~5 seconds with no segment created = SPEECH LOSS
```

---

## 🎯 Best Practices

### 1. Always Log to File

```bash
python src/gui/main.py 2>&1 | tee log_$(date +%Y%m%d_%H%M%S).txt
```

### 2. Run Controlled Tests

- Use known audio duration
- Count expected sentences
- Verify against log output

### 3. Check for Patterns

- Consistent loss at specific times
- Correlation with audio quality
- Queue overflow events

### 4. Validate Filters

- Review filtered segments
- Tune thresholds if needed
- Check for false positives

---

## 📊 Expected Metrics

| Metric | Target | Acceptable |
|--------|--------|------------|
| Segment Loss | 0% | <1% |
| Filter Rate | <5% | <10% |
| Avg Latency | <1000ms | <2000ms |
| Max Latency | <2000ms | <5000ms |

---

## 🔗 Related Documents

- [STATUS.md](STATUS.md) - Development status
- [docs/overlap_think_on_real_time_translator.md](docs/overlap_think_on_real_time_translator.md) - Architecture
- [docs/guides/PARALLEL_PIPELINE_GUIDE.md](docs/guides/PARALLEL_PIPELINE_GUIDE.md) - Pipeline guide

---

## 📝 Summary

Timestamped logging enables precise evaluation of:
- ✅ Speech detection completeness
- ✅ Processing latency per stage
- ✅ Filter effectiveness
- ✅ End-to-end pipeline performance

Use the provided parser script or write custom analysis tools to evaluate your specific use case.
