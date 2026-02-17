# Dynamic Environment Handling Guide

## The Problem

When using real-time translation, you may move between different acoustic environments:
- Quiet office → Noisy street
- Home (quiet) → Coffee shop (moderate noise)
- Inside car → Outside traffic

**Challenge:** The VAD (Voice Activity Detection) needs to quickly adapt to these changes to maintain accurate speech detection.

## The Solution: Environment-Aware VAD

The system now includes an **Environment-Aware VAD** that:
1. **Detects environment changes rapidly** (within 1-2 seconds)
2. **Adapts quickly** when a change is detected
3. **Stays stable** in consistent environments
4. **Provides feedback** about current environment state

## How It Works

### Environment States

| State | Noise Level | Threshold | Use Case |
|-------|-------------|-----------|----------|
| **QUIET** | < -50 dB | 0.35 | Home office, studio |
| **MODERATE** | -50 to -40 dB | 0.50 | Office, library |
| **NOISY** | -40 to -30 dB | 0.65 | Street, restaurant |
| **VERY_NOISY** | > -30 dB | 0.75 | Traffic, construction |
| **TRANSITIONING** | Variable | 0.55 | Detecting change |

### Adaptation Behavior

**When environment is stable:**
- Uses slow, smooth adaptation (preserves accuracy)
- Noise floor updates gradually

**When environment changes:**
- Detects >10dB change in ~1.5 seconds
- Switches to fast adaptation mode
- Quickly locks onto new noise floor

## Log Messages Explained

### Normal Operation
```
INFO: Environment: MODERATE | Noise: -45.2dB | Signal: -35.1dB | SNR: 10.1dB | Threshold: 0.52
```
✅ Normal operation in moderate environment

### Environment Change Detected
```
INFO: Environment change detected: 18.5dB shift, fast adaptation
INFO: Environment: NOISY | Noise: -28.3dB | Signal: -20.1dB | SNR: 8.2dB | Threshold: 0.72
```
✅ System detected moving to noisier environment and adapted

### High Noise with Low Signal
```
INFO: Environment: VERY_NOISY | Noise: -22.1dB | Signal: -21.5dB | SNR: 0.6dB
```
⚠️ Very noisy environment with poor signal. Speech detection may be difficult.

## Tips for Dynamic Environments

### 1. Allow 1-2 Seconds for Adaptation

When moving to a new environment:
- Wait 1-2 seconds before expecting optimal performance
- The VAD needs a moment to measure the new noise floor

### 2. Keep Speaking Clearly

- Don't whisper in noisy environments
- Maintain consistent volume
- Face the microphone

### 3. Monitor the Logs

Watch for:
- **"Environment change detected"** - Normal when moving locations
- **"VERY_NOISY"** with **SNR < 3dB** - May miss speech, consider moving

### 4. Manual Environment Override (If Needed)

If automatic detection isn't working well, you can force an environment:

```python
# In your code, after VAD initialization
vad.force_environment("noisy")  # Options: quiet, moderate, noisy, very_noisy
```

### 5. Reset When Needed

If the VAD gets "stuck" with wrong settings:

```python
vad.reset_environment()  # Forces fresh adaptation
```

## Troubleshooting

### "Environment keeps switching rapidly"

**Cause:** Threshold too close to boundary
**Fix:** The hysteresis (3dB) should prevent this. If still happening:
- Check if audio source is inconsistent
- Consider forcing a fixed environment

### "Speech not detected after moving to quiet place"

**Cause:** Noise floor still high from previous noisy environment
**Fix:** Wait 2-3 seconds for adaptation, or call `vad.reset_environment()`

### "Lots of false triggers in noisy environment"

**Cause:** Threshold too low for noise level
**Fix:** This should adapt automatically. If not:
```python
vad.force_environment("very_noisy")
```

## Configuration Options

You can tune the environment detection in `config/environment_aware_config`:

```python
EnvironmentAwareConfig(
    # How quickly to detect changes (lower = faster)
    env_change_threshold_db=10.0,
    
    # How fast to adapt (0.5 = fast, 0.1 = slow)
    fast_adaptation_rate=0.5,
    normal_adaptation_rate=0.1,
    
    # Minimum SNR for speech consideration
    min_snr_db=3.0,
)
```

## Summary

The Environment-Aware VAD automatically handles location changes:
- ✅ Detects environment shifts in ~1.5 seconds
- ✅ Adapts threshold to maintain accuracy
- ✅ Provides clear feedback about current state
- ✅ Works seamlessly without manual intervention

Just use the system normally - it will adapt as you move!
