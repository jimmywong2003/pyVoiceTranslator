# System Audio Selection - Fix & Guide

## Problem Identified

The **Audio Source** combo box was at the end of a crowded horizontal layout, making it:
- Hard to see (pushed to the right)
- Potentially cut off on smaller screens
- Not obvious that system audio was an option

## Fix Applied

### Before (Crowded Horizontal Layout)
```
[Source: ▼] → [Target: ▼] [ASR Model: ▼] [Audio Source: ▼]  ← Easily cut off!
```

### After (Two-Row Layout)
```
Row 1: [Source: ▼] → [Target: ▼] [ASR Model: ▼]
Row 2: 🎙️ Audio Input Source: [🎤 Microphone ▼] ✅ Available: BlackHole 2ch
                                    ↑
                              Wider + Status indicator!
```

## Changes Made

1. **Split settings into two rows**
   - Row 1: Language and ASR model settings
   - Row 2: Audio source (prominent placement)

2. **Better visual styling**
   - Added microphone icon (🎙️)
   - Bold label with teal color
   - Minimum width of 200px
   - Status indicator showing availability

3. **Real-time status check**
   - When "System Audio" is selected, automatically checks if BlackHole is available
   - Shows ✅ if available, ⚠️ if not installed
   - Shows device name when available

4. **Improved tooltip**
   - Clear instructions for setup
   - Step-by-step guide for BlackHole installation

---

## How to Use System Audio

### Step 1: Install BlackHole (One-time setup)

```bash
# Open Terminal and run:
brew install blackhole-2ch

# If you don't have Homebrew, install it first:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Configure System Audio

1. Open **System Settings** → **Sound**
2. Click **Output**
3. Select **BlackHole 2ch** as the output device

**Important:** You won't hear audio from your speakers when BlackHole is selected - it's being redirected to the virtual device for capture.

### Step 3: Run the GUI

```bash
python voice_translate_gui.py
```

### Step 4: Select System Audio

1. Look for the **🎙️ Audio Input Source** section (now prominently displayed)
2. Click the dropdown (currently showing "🎤 Microphone")
3. Select **"🔊 System Audio"**
4. Check the status indicator:
   - ✅ **Available: BlackHole 2ch** - Ready to use!
   - ⚠️ **BlackHole not detected** - Install BlackHole first

### Step 5: Start Translation

1. Click **▶ Start Translation**
2. Play audio/video from any application
3. Watch the translation appear in real-time!

---

## Troubleshooting

### Issue: "BlackHole not detected" warning

**Solution:**
```bash
# 1. Install BlackHole
brew install blackhole-2ch

# 2. Restart the GUI
# 3. Check System Settings → Sound → Output
# 4. Select BlackHole 2ch
```

### Issue: No translation appearing

**Check:**
1. Is BlackHole selected as output in System Settings?
2. Is audio actually playing? (You won't hear it)
3. Check the audio level indicator in the GUI
4. Try adjusting the VAD threshold (lower = more sensitive)

### Issue: "Invalid number of channels" error

**Solution:**
- This was a bug with device selection - fixed in recent updates
- Make sure you're using the latest code
- The system now auto-detects the correct device

### Issue: Can't hear audio when using System Audio

**This is expected!** When BlackHole is the output device:
- Audio is captured by the translation system
- It's NOT sent to your speakers
- To hear audio AND capture it, use a **Multi-Output Device** (see below)

---

## Advanced: Multi-Output Device (Hear + Capture)

To hear audio through speakers AND capture it for translation:

1. Open **Audio MIDI Setup** (search in Spotlight)
2. Click **+** (bottom left) → **Create Multi-Output Device**
3. Check both:
   - ☑️ **BlackHole 2ch**
   - ☑️ **MacBook Pro Speakers** (or your preferred output)
4. In System Settings → Sound → Output, select the **Multi-Output Device**

Now you'll hear audio AND it will be captured for translation!

---

## Verification Checklist

- [ ] BlackHole installed: `brew list | grep blackhole`
- [ ] BlackHole selected in System Settings → Sound → Output
- [ ] GUI shows: "✅ Available: BlackHole 2ch"
- [ ] "🔊 System Audio" selected in dropdown
- [ ] Audio playing from some application
- [ ] Translation appearing in GUI

---

## Quick Test

```bash
# 1. Check if BlackHole is installed
brew list blackhole-2ch

# 2. List audio devices
python -c "
from audio_module import AudioManager, AudioConfig, AudioSource
manager = AudioManager(AudioConfig())
devices = manager.list_devices(AudioSource.SYSTEM_AUDIO)
print('System audio devices:', [d['name'] for d in devices])
"

# 3. Run GUI and test
python voice_translate_gui.py
```

---

## Summary

The system audio selection is now:
- ✅ **More visible** (dedicated row with icon)
- ✅ **Easier to use** (status indicator + instructions)
- ✅ **Auto-validating** (checks availability on selection)
- ✅ **Better documented** (clear setup instructions)

**Ready to use system audio for translation!** 🎉
