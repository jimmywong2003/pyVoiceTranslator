# VAD Tuning Guide for System Audio

## Problem: High Noise Floor with System Audio

When using system audio capture (BlackHole), you may see:
- Noise level: 100-200+ (very high)
- Threshold: 0.8 (maxed out)
- SNR: negative or very low
- Few/no speech segments detected

## Root Causes

1. **BlackHole captures silence/noise** - When no audio is playing, BlackHole still outputs a signal
2. **Audio not routed through BlackHole** - System output not set to BlackHole
3. **Audio too quiet** - Low signal-to-noise ratio
4. **Wrong device selected** - GUI using microphone instead of system audio

## Quick Fixes

### 1. Verify BlackHole is System Output

System Settings → Sound → Output:
- Select **BlackHole 2ch** (not MacBook Speakers)
- You won't hear audio (this is expected)

### 2. Use Multi-Output Device (Hear + Capture)

To hear audio AND capture it:

1. Open **Audio MIDI Setup** (Applications → Utilities)
2. Click **+** (bottom left) → **Create Multi-Output Device**
3. Check both:
   - ☑️ **BlackHole 2ch**
   - ☑️ **MacBook Pro Speakers** (or your speakers)
4. Select this Multi-Output Device in System Settings → Sound → Output

### 3. Test with Microphone First

Verify the pipeline works:
1. In GUI, select **🎤 Microphone** (not System Audio)
2. Click **Start Translation**
3. Speak clearly
4. Check if speech is detected

If microphone works but system audio doesn't → audio routing issue

### 4. Check Audio is Playing

The VAD noise=160 suggests silence/noise, not actual audio content.

Make sure:
- Audio/video is playing in some app
- The app is outputting to BlackHole (or Multi-Output Device)
- Volume is not muted

### 5. Lower VAD Threshold (More Sensitive)

In `src/audio/vad/silero_vad_adaptive.py`, adjust defaults:

```python
# Line ~20-25 in AdaptiveSileroVADProcessor.__init__
self.base_threshold = 0.3  # Lower from 0.5
self.min_threshold = 0.2   # Lower from 0.3
self.max_threshold = 0.6   # Lower from 0.8
```

## Diagnostic Commands

```bash
# Check BlackHole is installed
brew list | grep blackhole

# List audio devices
python -c "
import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    if 'BlackHole' in d['name']:
        print(f'{i}: {d[\"name\"]} (input channels: {d[\"max_input_channels\"]})')
"

# Check current default output
system_profiler SPAudioDataType | grep -A 3 "Default"
```

## Common Issues

### "Noise level 100+ but no speech detected"
→ BlackHole is getting silence/noise, not actual audio
→ Check System Settings → Sound → Output is set to BlackHole

### "Audio playing but nothing translates"
→ Audio playing through speakers, not BlackHole
→ Use Multi-Output Device or set BlackHole as output

### "Everything was working then stopped"
→ macOS reset output device after sleep/restart
→ Re-select BlackHole in System Settings

## Recommended Test

1. Play a YouTube video in browser
2. Set system output to BlackHole 2ch
3. Run GUI with **🔊 System Audio** selected
4. Check logs for `faster_whisper:Processing audio with duration...`

If you see that log, ASR is receiving audio!
