# Automatic Audio Tuning Proposal

**Feature:** Smart Microphone Gain Optimization  
**Status:** Proposal / Design Phase  
**Target Version:** v2.2.0  
**Author:** VoiceTranslate Pro Team  

---

## Executive Summary

Implement automatic microphone gain calibration in the Audio Test dialog to optimize audio input levels for best speech recognition accuracy. The system will analyze audio characteristics and adjust gain to achieve optimal signal-to-noise ratio without clipping.

---

## Problem Statement

### Current Issues
1. **Inconsistent Input Levels:** Users have different microphone sensitivities
2. **Clipping/Overload:** Too high gain causes distortion, degrading ASR accuracy
3. **Low Signal:** Too low gain makes speech hard to detect
4. **Background Noise:** No noise floor measurement
5. **Manual Trial-and-Error:** Users must manually adjust system settings

### Impact on ASR
| Issue | ASR Accuracy Impact |
|-------|---------------------|
| Clipping | -40% to -60% (garbled text) |
| Low Signal | -30% to -50% (missed words) |
| High Noise Floor | -20% to -30% (false triggers) |
| Inconsistent Levels | -15% to -25% (unreliable) |

---

## Proposed Solution

### Core Features

#### 1. Auto-Gain Calibration 🔧
```
Process:
1. Measure current input level (3-second sample)
2. Calculate peak, RMS, and noise floor
3. Determine optimal gain adjustment
4. Apply gain setting (platform-specific)
5. Verify with second measurement
6. Save optimal settings
```

#### 2. Multi-Parameter Optimization 📊
| Parameter | Target Range | Measurement |
|-----------|--------------|-------------|
| Peak Level | -6 dB to -3 dB | Prevent clipping |
| RMS Level | -20 dB to -12 dB | Optimal speech |
| Noise Floor | < -50 dB | Clean signal |
| Dynamic Range | > 30 dB | Good SNR |
| Clipping Events | 0 | No distortion |

#### 3. Platform-Specific Implementation

**macOS:**
```python
# Use CoreAudio API via ctypes or pyobjc
# Access: AudioObjectGetPropertyData for input devices
# Controls: kAudioHardwarePropertyDevices
# Gain: kAudioDevicePropertyVolumeScalar
```

**Windows:**
```python
# Use pycaw or comtypes for Core Audio
# Access: IAudioEndpointVolume interface
# Controls: Master volume level, mute state
# Alternative: NAudio via pythonnet
```

**Linux (ALSA):**
```python
# Use alsaaudio or amixer subprocess
# Access: ALSA mixer controls
# Controls: Capture volume, mic boost
```

#### 4. Calibration Modes

**Quick Mode (5 seconds):**
- Single measurement
- Basic gain adjustment
- Suitable for most users

**Advanced Mode (15 seconds):**
- Multiple test phrases
- Noise floor analysis
- Dynamic range measurement
- Clipping stress test
- Frequency response check

**Silent Mode (10 seconds):**
- Measure ambient noise
- Set noise gate threshold
- Optimize for quiet environments

---

## Technical Architecture

### Component Design

```
┌─────────────────────────────────────────────────────────────┐
│                 AudioAutoTuner                               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LevelAnalyzer│  │ GainController│  │SettingsManager│     │
│  │              │  │              │  │              │      │
│  │ - measure()  │  │ - set_gain() │  │ - save()     │      │
│  │ - analyze()  │  │ - get_gain() │  │ - load()     │      │
│  │ - calibrate()│  │ - reset()    │  │ - profiles() │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│  Platform Adapters: macOS | Windows | Linux                │
└─────────────────────────────────────────────────────────────┘
```

### Class Structure

```python
@dataclass
class AudioProfile:
    """Optimized audio settings profile."""
    device_id: int
    device_name: str
    gain_db: float
    noise_floor_db: float
    peak_level_db: float
    rms_level_db: float
    snr_db: float
    sample_rate: int
    timestamp: datetime
    confidence_score: float  # 0.0-1.0

class LevelAnalyzer:
    """Analyze audio levels and characteristics."""
    
    def measure(self, duration: float = 3.0) -> AudioMetrics:
        """Measure current audio characteristics."""
        # Record sample
        # Calculate: peak, RMS, noise floor
        # Detect clipping events
        # Return metrics
    
    def analyze_noise_floor(self, duration: float = 2.0) -> float:
        """Measure ambient noise level (silence required)."""
        # Record with no speech
        # Return noise floor in dB
    
    def calculate_optimal_gain(self, metrics: AudioMetrics) -> float:
        """Calculate optimal gain adjustment."""
        # Target: RMS -18 dB, Peak -6 dB
        # Return gain adjustment in dB

class GainController(ABC):
    """Abstract base for platform-specific gain control."""
    
    @abstractmethod
    def set_gain(self, device_id: int, gain_db: float) -> bool:
        """Set microphone gain in dB."""
    
    @abstractmethod
    def get_gain(self, device_id: int) -> float:
        """Get current microphone gain in dB."""
    
    @abstractmethod
    def get_gain_range(self, device_id: int) -> Tuple[float, float]:
        """Get min/max gain range for device."""

class MacOSGainController(GainController):
    """macOS CoreAudio implementation."""
    # Uses CoreAudio framework via ctypes

class WindowsGainController(GainController):
    """Windows Core Audio implementation."""
    # Uses pycaw or WASAPI

class LinuxGainController(GainController):
    """Linux ALSA implementation."""
    # Uses alsaaudio or amixer

class AudioAutoTuner:
    """Main auto-tuning coordinator."""
    
    def __init__(self):
        self.analyzer = LevelAnalyzer()
        self.controller = self._create_platform_controller()
        self.settings = SettingsManager()
    
    def quick_tune(self, device_id: int) -> AudioProfile:
        """Quick 5-second auto-tuning."""
        # 1. Measure current state
        # 2. Calculate optimal gain
        # 3. Apply gain
        # 4. Verify result
        # 5. Return profile
    
    def advanced_tune(self, device_id: int) -> AudioProfile:
        """Advanced 15-second tuning with full analysis."""
        # 1. Measure noise floor (silence)
        # 2. Measure speech at different levels
        # 3. Stress test for clipping
        # 4. Optimize for dynamic range
        # 5. Create comprehensive profile
```

---

## User Interface Design

### Audio Test Dialog Enhancements

```
┌─────────────────────────────────────────────────────────────┐
│ 🎤 Audio Test & Auto-Tune                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Microphone: [GO Work USB ▼]                                │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📊 Current Levels                                       ││
│ │                                                         ││
│ │ Peak:   [████████░░░░░░░░░░] -12 dB  🟢               ││
│ │ RMS:    [████░░░░░░░░░░░░░░] -24 dB  🟡               ││
│ │ Noise:  [░░░░░░░░░░░░░░░░░░] -60 dB  🟢               ││
│ │                                                         ││
│ │ Status: ✅ Optimal (SNR: 36 dB)                        ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 🤖 Auto-Tune                                            ││
│ │                                                         ││
│ │ [🔧 Quick Tune (5s)]  [🔬 Advanced Tune (15s)]        ││
│ │                                                         ││
│ │ Instructions:                                           ││
│ │ 1. Click "Quick Tune"                                   ││
│ │ 2. Speak normally for 5 seconds                         ││
│ │ 3. System will optimize gain automatically              ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 🔄 Loopback Test                                        ││
│ │                                                         ││
│ │ [⏺ Record (3s)]  [▶ Play Back]  [💾 Save Profile]     ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ [Close]                                                    │
└─────────────────────────────────────────────────────────────┘
```

### Visual Indicators

| Indicator | Meaning | Color |
|-----------|---------|-------|
| 🟢 Optimal | All parameters in target range | Green |
| 🟡 Acceptable | Minor adjustments needed | Yellow |
| 🔴 Needs Tuning | Significant issues detected | Red |
| ⚠️ Clipping | Audio is distorting | Orange |
| 🔇 No Signal | No audio detected | Gray |

### Post-Tuning Report

```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Auto-Tune Complete                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Before Tuning:                                              │
│   Peak: -3 dB ⚠️ (clipping risk)                          │
│   RMS:  -30 dB 🔴 (too quiet)                             │
│   Noise: -45 dB                                           │
│                                                             │
│ After Tuning:                                               │
│   Peak: -6 dB 🟢                                          │
│   RMS:  -18 dB 🟢                                         │
│   Noise: -48 dB                                           │
│   Gain Adjusted: +8.5 dB                                  │
│                                                             │
│ Quality Score: 94/100 ⭐⭐⭐⭐                              │
│                                                             │
│ [💾 Save Profile]  [🔄 Re-Tune]  [✓ Done]                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Framework (Week 1)
- [ ] Create `LevelAnalyzer` class
- [ ] Implement audio metrics calculation
- [ ] Add basic UI elements to AudioTestDialog
- [ ] Create platform abstraction layer

### Phase 2: Platform Support (Week 2-3)
- [ ] macOS CoreAudio implementation
- [ ] Windows WASAPI/pycaw implementation
- [ ] Linux ALSA implementation
- [ ] Platform detection and adapter selection

### Phase 3: Auto-Tune Logic (Week 4)
- [ ] Quick tune algorithm
- [ ] Advanced tune with noise analysis
- [ ] Profile management (save/load)
- [ ] Integration with pipeline settings

### Phase 4: Testing & Polish (Week 5)
- [ ] Test with various microphones
- [ ] Test on all platforms
- [ ] UI/UX refinement
- [ ] Documentation

---

## Technical Challenges & Solutions

### Challenge 1: Platform API Differences
**Problem:** Each OS has different APIs for gain control

**Solution:** 
- Abstract interface with platform-specific implementations
- Feature detection (graceful degradation if API unavailable)
- Fallback to manual instructions with visual guidance

### Challenge 2: Permission Requirements
**Problem:** macOS requires microphone permission, some APIs need elevated privileges

**Solution:**
- Check permissions before tuning
- Provide clear instructions for manual adjustment if automatic fails
- Store settings in user-accessible location

### Challenge 3: Device-Specific Behavior
**Problem:** Different microphones have different gain ranges and behaviors

**Solution:**
- Measure actual gain range per device
- Adaptive tuning algorithm
- Profile per device ID

### Challenge 4: Real-Time Adjustment
**Problem:** Some APIs don't support real-time gain changes

**Solution:**
- Pre-measure with current gain
- Calculate target gain
- Apply and re-measure
- Iterate if needed (max 3 attempts)

---

## Dependencies

### New Dependencies
```
# macOS
pyobjc-framework-CoreAudio  # CoreAudio bindings

# Windows
pycaw>=20230407            # Core Audio wrapper
comtypes>=1.2.0            # COM interface

# Linux
alsaaudio>=0.10.0          # ALSA bindings (optional)
```

### Fallback Strategy
If platform-specific libraries unavailable:
1. Still provide level analysis
2. Show manual adjustment instructions
3. Visual feedback during manual adjustment
4. Save settings to config file

---

## Settings Persistence

### Profile Storage
```python
# ~/.voicetranslate/audio_profiles.json
{
    "profiles": [
        {
            "device_id": 2,
            "device_name": "GO Work USB",
            "platform": "darwin",
            "gain_db": -8.5,
            "noise_floor_db": -58.2,
            "peak_level_db": -6.1,
            "rms_level_db": -17.8,
            "snr_db": 40.4,
            "sample_rate": 16000,
            "timestamp": "2026-02-21T23:45:00Z",
            "confidence_score": 0.94
        }
    ],
    "active_profile": 2
}
```

### Pipeline Integration
```python
# In pipeline initialization
if audio_profile:
    # Apply saved gain settings
    gain_controller.set_gain(device_id, audio_profile.gain_db)
    # Set noise gate threshold
    vad_config.noise_floor_db = audio_profile.noise_floor_db
```

---

## Success Metrics

### Quality Improvements
| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Clipping Rate | ~15% | <2% | Detected in audio test |
| Low Signal Rate | ~25% | <5% | RMS < -30 dB |
| User Satisfaction | N/A | >4.0/5 | Survey |
| Setup Time | 5+ min | <30 sec | Time to optimal settings |

### ASR Accuracy Impact
- Expected improvement: +10% to +20% accuracy
- Reduced hallucinations from clipping
- Better recognition of quiet speech
- More consistent results across sessions

---

## Future Enhancements

### V2.3.0: Advanced Features
- [ ] Automatic noise suppression toggle
- [ ] Frequency equalization (EQ) for voice
- [ ] Echo cancellation settings
- [ ] Multiple microphone profiles
- [ ] Environment presets (quiet office, noisy cafe, etc.)

### V2.4.0: AI-Powered
- [ ] Machine learning for optimal settings prediction
- [ ] Voice characteristic detection (male/female/child)
- [ ] Accent-based optimization hints
- [ ] Automatic re-tuning when device changes

---

## Appendix: Platform-Specific Details

### macOS CoreAudio
```python
import ctypes
from ctypes import CDLL, c_uint32, c_void_p, c_float

# Key constants
kAudioHardwarePropertyDevices = 0x61646576  # 'adev'
kAudioDevicePropertyVolumeScalar = 0x76736F6C  # 'vsol'

# Pseudocode
coreaudio = CDLL('/System/Library/Frameworks/CoreAudio.framework/CoreAudio')
# Get device list
# Find input device
# Get/set volume property
```

### Windows WASAPI
```python
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Get default microphone
device = AudioUtilities.GetMicrophone()
interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

# Get/set level (0.0 to 1.0 scalar)
current = volume.GetMasterVolumeLevelScalar()
volume.SetMasterVolumeLevelScalar(0.8, None)
```

### Linux ALSA
```python
import alsaaudio

# Open mixer
mixer = alsaaudio.Mixer('Capture', cardindex=0)

# Get/set volume (0-100)
volumes = mixer.getvolume()  # Returns list of channel volumes
mixer.setvolume(80)  # Set to 80%
```

---

## Conclusion

The Automatic Audio Tuning feature will significantly improve user experience by:
1. Eliminating manual trial-and-error for microphone setup
2. Optimizing audio quality for best ASR accuracy
3. Providing visual feedback and clear guidance
4. Persisting optimal settings per device

**Estimated Development Time:** 5 weeks  
**Priority:** High (impacts all users)  
**Dependencies:** Platform-specific audio libraries  

---

*Last Updated: 2026-02-21*  
*Status: Proposal - Awaiting Review*
