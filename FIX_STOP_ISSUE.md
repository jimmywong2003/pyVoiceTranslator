# Fix for Background Process Not Stopping

## Problem

When clicking "Stop Translation", the GUI appears to stop but background processes continue running:
- Processing thread keeps running
- ASR model still processing queued segments
- Audio capture thread may still be active
- Python process continues using CPU

## Root Causes

### 1. Blocking Final Segment Processing

**Issue:** The `stop()` method called `_process_segment()` on the final VAD segment, which could take 17+ seconds for long segments.

```python
# BEFORE (blocking)
def stop(self):
    ...
    final_segment = self._vad.force_finalize()
    if final_segment:
        self._process_segment(final_segment)  # <-- BLOCKS for seconds!
```

**Fix:** Made final segment processing optional with timeout:
```python
# AFTER (non-blocking)
def stop(self, timeout=5.0, process_final=False):
    ...
    if process_final and self._vad:
        final_segment = self._vad.force_finalize()
        if final_segment:
            # Process with timeout protection
            final_thread = threading.Thread(target=process_with_timeout)
            final_thread.start()
            final_thread.join(timeout=3.0)  # Max 3 seconds
```

### 2. Worker Thread Join Timeout Too Short

**Issue:** Worker waited 5 seconds, but processing could take longer.

```python
# BEFORE
self.wait(5000)  # 5 seconds
```

**Fix:** Shorter timeout + force terminate:
```python
# AFTER
if not self.wait(3000):  # Wait 3 seconds
    logger.warning("Worker did not stop gracefully, forcing termination")
    self.terminate()  # Force kill thread
    self.wait(1000)
```

### 3. Pipeline Stop Not Clearing Queue

**Issue:** Segments remaining in queue were still being processed after stop.

**Fix:** Clear the queue during stop:
```python
# Clear any remaining queue items
if self._segment_queue:
    try:
        while not self._segment_queue.empty():
            self._segment_queue.get_nowait()
    except:
        pass
```

### 4. No Cleanup on GUI Stop

**Issue:** UI stopped but didn't ensure all resources were released.

**Fix:** Added comprehensive cleanup:
```python
def _stop_translation(self):
    # Stop update timer first
    if self.update_timer.isActive():
        self.update_timer.stop()
    
    # Stop worker thread
    if self.worker:
        if self.worker.isRunning():
            self.worker.stop()
        self.worker = None
    
    # Ensure UI is reset
    QTimer.singleShot(100, self._on_worker_stopped)
```

---

## Changes Made

### 1. `voice_translation/src/pipeline/orchestrator.py`

**Modified `stop()` method:**
- Added `timeout` parameter (default 5.0s)
- Added `process_final` parameter (default False)
- Made final segment processing optional and time-limited
- Added queue clearing
- Better exception handling

### 2. `voice_translate_gui.py`

**Modified `TranslationWorker.stop()`:**
- Shorter timeout (2s for pipeline, 3s for worker)
- Force terminate if thread doesn't stop gracefully
- Better cleanup of audio manager

**Modified `MainWindow._stop_translation()`:**
- Stop timer first
- Better error handling
- Delayed UI reset to ensure clean state

---

## Behavior After Fix

### Normal Stop
1. User clicks "Stop"
2. Timer stops immediately
3. Pipeline stops with 2-second timeout
4. Final segment is NOT processed (skipped)
5. Worker thread stops with 3-second timeout
6. If thread doesn't stop, it's force-terminated
7. UI resets to stopped state

### Force Stop (if needed)
```python
# Hard stop - skip everything
worker.terminate()  # Force kill
```

---

## Testing

### Check if Background Stopped

1. **Activity Monitor** (macOS) or **Task Manager** (Windows)
   - Check if Python process CPU usage drops to 0%

2. **Console Output**
   ```
   INFO:voice_translation.src.pipeline.orchestrator:✅ Translation pipeline stopped
   INFO:__main__:Translation worker stopped
   ```

3. **Log Files**
   - Should see "Stopping translation..." followed by "stopped"

### Expected Stop Sequence

```
User clicks Stop:
  ↓
_stop_translation() called
  ↓
Timer stopped
  ↓
Worker.stop() called
  ↓
Pipeline.stop(timeout=2.0, process_final=False)
  ↓
Audio capture stopped
  ↓
Processing thread join (2s timeout)
  ↓
Queue cleared
  ↓
Worker thread join (3s timeout)
  ↓
[If timeout] Worker.terminate() called
  ↓
UI reset
  ↓
✅ Fully stopped
```

---

## Configuration

### Adjust Timeouts

If you need longer graceful shutdown:

```python
# In TranslationWorker.stop()
self.pipeline.stop(timeout=5.0)  # Increase from 2.0
self.wait(5000)  # Increase from 3000
```

### Enable Final Segment Processing

If you want to process the final segment (may be slow):

```python
# In TranslationWorker.stop()
self.pipeline.stop(timeout=2.0, process_final=True)
```

---

## Debugging

### Enable Verbose Logging

```python
# At start of script
logging.basicConfig(level=logging.DEBUG)
```

### Check Thread Status

```python
import threading
print(f"Active threads: {threading.active_count()}")
for t in threading.enumerate():
    print(f"  - {t.name}: alive={t.is_alive()}")
```

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| CPU still high after stop | Thread not terminated | Check logs for "forcing termination" |
| Long stop time | Processing final segment | Set `process_final=False` |
| Memory not released | Thread still running | Ensure `worker = None` after stop |

---

## Summary

The fix ensures:
- ✅ **Fast stop** - No more waiting 17+ seconds
- ✅ **Clean termination** - Force kill if needed
- ✅ **Queue cleared** - No pending processing
- ✅ **Resource cleanup** - Audio, threads, timers stopped
- ✅ **UI responsive** - Immediate feedback
