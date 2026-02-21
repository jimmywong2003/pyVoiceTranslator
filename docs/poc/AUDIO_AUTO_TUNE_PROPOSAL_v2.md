# Automatic Audio Tuning Proposal v2

**Feature:** Smart Microphone Gain Optimization  
**Status:** Revised Proposal (Post-Review)  
**Target Version:** v2.2.0 (macOS/Windows), v2.3.0 (Linux)  
**Revised Timeline:** 8-10 weeks  
**Author:** VoiceTranslate Pro Team  

---

## Executive Summary (Revised)

Based on technical review, this proposal has been updated to address critical platform API limitations. The key change is a **dual-mode architecture** that supports both hardware gain control AND software digital gain fallback.

### Critical Risk Acknowledgment
> **Hardware Gain Control is NOT universally available.** Many USB microphones (Blue Yeti, Rode NT-USB) handle gain internally via hardware knobs and ignore OS API commands. **Digital Gain Fallback is mandatory, not optional.**

---

## Revised Architecture

### Dual-Mode Gain Control

```
┌─────────────────────────────────────────────────────────────┐
│                 AudioAutoTuner v2                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ LevelAnalyzer│  │     GainController (Composite)       │ │
│  │              │  │  ┌────────────────────────────────┐  │ │
│  │ • measure()  │  │  │  HardwareGainController        │  │ │
│  │ • analyze()  │  │  │  ├─ MacOSCoreAudio             │  │ │
│  │ • calibrate()│  │  │  ├─ WindowsWASAPI              │  │ │
│  │              │  │  │  └─ LinuxPipeWire              │  │ │
│  └──────────────┘  │  └────────────────────────────────┘  │ │
│         ↓          │  ┌────────────────────────────────┐  │ │
│  ┌──────────────┐  │  │  DigitalGainProcessor          │  │ │
│  │   Settings   │  │  │  (Software PCM multiplier)     │  │ │
│  │   Manager    │←─┼──┤  • apply_gain()                │  │ │
│  └──────────────┘  │  │  • process_buffer()            │  │ │
│                    │  └────────────────────────────────┘  │ │
│                    └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Gain Application Strategy

```python
class AudioAutoTuner:
    def apply_optimal_gain(self, device_id: int, target_db: float) -> GainResult:
        """
        Attempts hardware gain first, falls back to digital gain.
        """
        # Step 1: Check if hardware gain is available
        if self.hardware_controller.supports_hardware_gain(device_id):
            # Step 2: Try to set hardware gain
            success = self.hardware_controller.set_gain(device_id, target_db)
            if success:
                return GainResult(mode=HARDWARE, gain_db=target_db)
        
        # Step 3: Fall back to digital gain
        self.digital_processor.set_gain_multiplier(device_id, target_db)
        return GainResult(mode=DIGITAL, gain_db=target_db, 
                         warning="Hardware gain not available, using digital gain")
```

---

## Revised Component Design

### 1. LevelAnalyzer (Enhanced)

```python
class LevelAnalyzer:
    """Analyze audio levels with proper float handling."""
    
    def calculate_rms(self, audio_buffer: np.ndarray) -> float:
        """Calculate RMS in dB for float audio (-1.0 to 1.0)."""
        # Correct RMS calculation with epsilon to avoid log(0)
        rms = np.sqrt(np.mean(audio_buffer ** 2))
        db = 20 * np.log10(rms + 1e-10)
        return db
    
    def detect_clipping(self, audio_buffer: np.ndarray, 
                       threshold: float = 0.99) -> int:
        """Count samples at/near clipping level."""
        clipped = np.sum(np.abs(audio_buffer) >= threshold)
        return int(clipped)
    
    def iterative_calibration(self, device_id: int, 
                             target_rms_db: float = -18.0,
                             max_iterations: int = 3) -> CalibrationResult:
        """
        Iterative calibration with verification.
        
        Process:
        1. Measure current level
        2. Calculate delta to target
        3. Apply gain adjustment
        4. Wait 500ms (hardware latency)
        5. Re-measure
        6. If error > 2dB, repeat (max 3 tries)
        """
        for iteration in range(max_iterations):
            # Measure
            metrics = self.measure(device_id, duration=2.0)
            current_db = metrics.rms_db
            
            # Calculate delta
            delta_db = target_rms_db - current_db
            
            # Check if within tolerance
            if abs(delta_db) <= 2.0:
                return CalibrationResult(
                    success=True, 
                    final_db=current_db,
                    iterations=iteration + 1
                )
            
            # Apply gain
            self.tuner.apply_optimal_gain(device_id, target_rms_db)
            
            # Wait for hardware latency
            time.sleep(0.5)
        
        # Max iterations reached
        return CalibrationResult(
            success=False,
            final_db=current_db,
            error=f"Failed to reach target after {max_iterations} attempts"
        )
```

### 2. GainController (Revised with Detection)

```python
class GainController(ABC):
    """Abstract base for platform-specific gain control."""
    
    @abstractmethod
    def supports_hardware_gain(self, device_id: int) -> bool:
        """
        Check if the OS allows changing mic gain for this device.
        
        Many USB mics (Blue Yeti, Rode NT-USB) have hardware knobs
        and ignore OS gain commands. This method detects that.
        """
        pass
    
    @abstractmethod
    def set_gain(self, device_id: int, gain_db: float) -> bool:
        """Set microphone gain in dB. Returns success/failure."""
        pass
    
    @abstractmethod
    def get_gain_range(self, device_id: int) -> Tuple[float, float]:
        """
        Get min/max gain range.
        
        Note: Many APIs return 0.0-1.0 scalar with non-linear dB mapping.
        If API only provides scalar, use relative adjustments rather than
        trying to set exact dB values.
        """
        pass
    
    @abstractmethod
    def get_gain(self, device_id: int) -> float:
        """Get current microphone gain in dB."""
        pass


class MacOSCoreAudioController(GainController):
    """macOS implementation with hardware detection."""
    
    def supports_hardware_gain(self, device_id: int) -> bool:
        """Check if device supports software gain control."""
        # Query kAudioDevicePropertyVolumeScalar
        # If property exists and is writable, return True
        # If returns fixed value (0/1) or error, return False
        pass
    
    def set_gain(self, device_id: int, gain_db: float) -> bool:
        """Set gain via CoreAudio."""
        # Check sandbox restrictions first
        if self._is_sandboxed():
            return False
        
        # Attempt to set kAudioDevicePropertyVolumeScalar
        # Return success/failure
        pass


class WindowsWASAPIController(GainController):
    """Windows implementation with pycaw/comtypes fallback."""
    
    def __init__(self):
        self._use_policy_config = False
        self._try_init_pycaw()
    
    def _try_init_pycaw(self):
        """Try pycaw first, fall back to PolicyConfig."""
        try:
            from pycaw.pycaw import AudioUtilities
            # Test if we can actually change volume
            test_device = AudioUtilities.GetMicrophone()
            # Try a test set (and restore)
            self._pycaw_available = True
        except Exception:
            self._pycaw_available = False
    
    def supports_hardware_gain(self, device_id: int) -> bool:
        """Check if Windows allows changing this mic's gain."""
        # IAudioEndpointVolume often reports 100% for input devices
        # Check if we can actually change it
        pass
    
    def set_gain(self, device_id: int, gain_db: float) -> bool:
        """Set gain via WASAPI or PolicyConfig."""
        # Try pycaw first
        if self._pycaw_available:
            return self._set_gain_pycaw(device_id, gain_db)
        
        # Fall back to IPolicyConfig (undocumented but often works)
        return self._set_gain_policy_config(device_id, gain_db)


class LinuxPipeWireController(GainController):
    """Linux implementation prioritizing PipeWire/PulseAudio."""
    
    def __init__(self):
        self._pipewire_available = self._check_pipewire()
        self._pulse_available = self._check_pulse()
    
    def _check_pipewire(self) -> bool:
        """Check if PipeWire is available."""
        try:
            import dbus
            # Check for PipeWire service
            return True
        except ImportError:
            return False
    
    def _check_pulse(self) -> bool:
        """Check if PulseAudio is available."""
        try:
            import pulsectl
            return True
        except ImportError:
            return False
    
    def supports_hardware_gain(self, device_id: int) -> bool:
        """Check ALSA/PipeWire gain control availability."""
        # Direct ALSA often conflicts with sound server
        # Prefer PipeWire/PulseAudio control
        pass
```

### 3. DigitalGainProcessor (New)

```python
class DigitalGainProcessor:
    """
    Software gain applied to PCM audio buffers.
    
    This is the FALLBACK when hardware gain control is unavailable.
    It multiplies audio samples before they reach the ASR engine.
    
    Limitations:
    - Cannot fix hardware clipping (distortion inside the mic)
    - Can amplify noise along with signal
    - Best for fixing low signal issues
    """
    
    def __init__(self):
        self._gain_multipliers: Dict[int, float] = {}
        self._max_gain_db = 20.0  # Limit to +20dB to prevent runaway
    
    def set_gain_multiplier(self, device_id: int, target_db: float) -> float:
        """
        Calculate and store gain multiplier for a device.
        
        Args:
            device_id: Audio device ID
            target_db: Target gain adjustment in dB
        
        Returns:
            Actual multiplier applied (may be limited)
        """
        # Limit to prevent excessive amplification
        target_db = max(-20.0, min(target_db, self._max_gain_db))
        
        # Convert dB to linear multiplier
        multiplier = 10 ** (target_db / 20)
        self._gain_multipliers[device_id] = multiplier
        
        return multiplier
    
    def process_buffer(self, device_id: int, 
                       audio_buffer: np.ndarray) -> np.ndarray:
        """
        Apply digital gain to audio buffer.
        
        Called by the audio pipeline before ASR processing.
        """
        if device_id not in self._gain_multipliers:
            return audio_buffer
        
        multiplier = self._gain_multipliers[device_id]
        
        # Apply gain
        amplified = audio_buffer * multiplier
        
        # Soft clipping to prevent digital distortion
        # Use tanh for smooth limiting
        if np.max(np.abs(amplified)) > 0.95:
            amplified = np.tanh(amplified)
        
        return amplified
    
    def get_gain_db(self, device_id: int) -> float:
        """Get current digital gain in dB."""
        if device_id not in self._gain_multipliers:
            return 0.0
        multiplier = self._gain_multipliers[device_id]
        return 20 * np.log10(multiplier)
```

---

## Revised UI Design

### Hardware Limit Detection

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Hardware Limit Reached                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Your microphone is at maximum hardware gain but the signal  │
│ is still too quiet.                                         │
│                                                             │
│ Options:                                                    │
│ 1. 🔧 Apply Digital Gain (+12 dB) - May increase noise     │
│ 2. 🎤 Adjust Physical Knob - Increase volume on your mic   │
│ 3. 📍 Move Closer to Microphone - Improve signal at source │
│                                                             │
│ [Apply Digital Gain]  [Open Sound Settings]  [Cancel]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Manual Override Slider

```
┌─ Gain Control ────────────────────────────────────────────┐
│                                                           │
│ Mode: 🔧 Hardware (or 💻 Digital Fallback)               │
│                                                           │
│ Gain:  [━━━━━●━━━━━━]  -8 dB                             │
│       -20dB         0dB         +20dB                    │
│                                                           │
│ [🔄 Auto-Tune]  [💾 Save Profile]  [↩️ Reset]            │
│                                                           │
│ Status: ✅ Optimal (Peak: -6 dB, RMS: -18 dB)            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Clipping Warning

```
┌─────────────────────────────────────────────────────────────┐
│ 🔴 Clipping Detected                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Your microphone is clipping (distorting).                   │
│                                                             │
│ This CANNOT be fixed with software gain.                    │
│                                                             │
│ Solutions:                                                  │
│ • Decrease physical volume knob on your microphone         │
│ • Move further from microphone                             │
│ • Use a pop filter or windscreen                           │
│                                                             │
│ [I've Adjusted Hardware - Re-Test]  [Continue Anyway]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Revised Implementation Timeline

### Phase 1: Spike & Validation (Week 1)
**Goal:** Validate API availability before committing to architecture

**Tasks:**
- [ ] **Day 1-2:** Test macOS CoreAudio on 5 devices
  - MacBook Pro built-in mic
  - MacBook Air built-in mic
  - USB headset (Jabra/Plantronics)
  - USB mic with hardware knob (Blue Yeti if available)
  - Bluetooth headset
- [ ] **Day 3-4:** Test Windows WASAPI on 5 devices
  - Similar device matrix
- [ ] **Day 5:** Analyze results and document:
  - Success rate for hardware gain control
  - Common failure modes
  - Decision: Proceed with hardware control or pivot to digital-first?

**Decision Point:**
- If hardware control works on >70% of devices → Proceed with dual-mode
- If <50% success → Pivot to digital-gain-primary with hardware as bonus

### Phase 2: Core Framework (Week 2-3)
- [ ] Implement LevelAnalyzer with correct RMS calculation
- [ ] Implement DigitalGainProcessor (fallback always works)
- [ ] Create GainController abstraction
- [ ] Implement iterative calibration (measure → adjust → verify)

### Phase 3: Platform Support (Week 4-6)
- [ ] **Week 4:** macOS CoreAudio implementation
  - Hardware detection
  - Sandbox permission handling
  - Error fallback
- [ ] **Week 5:** Windows WASAPI implementation
  - pycaw primary
  - PolicyConfig fallback
  - Permission handling
- [ ] **Week 6:** Linux PipeWire/PulseAudio (Deferred to v2.3.0?)
  - Assess if timeline allows

### Phase 4: UI Integration (Week 7)
- [ ] Enhanced Audio Test dialog
- [ ] Hardware limit detection UI
- [ ] Manual override slider
- [ ] Clipping warnings
- [ ] Profile save/load

### Phase 5: Testing & Edge Cases (Week 8-10)
- [ ] Test with 20+ microphone models
- [ ] Test virtual audio devices (Voicemeeter, BlackHole)
- [ ] Test Bluetooth headsets (variable latency)
- [ ] Test XLR audio interfaces (Focusrite, etc.)
- [ ] Edge case: Multiple mics switching
- [ ] Edge case: Sample rate changes

**Total: 10 weeks (with Linux deferred)**

---

## Dependencies (Updated)

### Core Dependencies
```
numpy>=1.24.0          # Already required, for efficient audio math
platformdirs>=3.0.0    # NEW: OS-specific config paths
```

### Platform-Specific (Optional/Fallback)
```
# macOS
pyobjc-framework-CoreAudio>=9.0  # Optional, can fall back to ctypes

# Windows
pycaw>=20230407        # Primary
dependency  
comtypes>=1.2.0        # Required by pycaw
# Note: PolicyConfig fallback uses ctypes (no extra dep)

# Linux (v2.3.0)
pulsectl>=22.3.0       # PulseAudio control
dbus-next>=0.2.3       # PipeWire via DBus
# Note: ALSA fallback uses subprocess (no extra dep)
```

### Installation Strategy
```python
# setup.py / requirements.txt
install_requires=[
    'numpy>=1.24.0',
    'platformdirs>=3.0.0',
    # Platform-specific as extras
]

extras_require={
    'macos': ['pyobjc-framework-CoreAudio>=9.0'],
    'windows': ['pycaw>=20230407', 'comtypes>=1.2.0'],
    'linux': ['pulsectl>=22.3.0', 'dbus-next>=0.2.3'],
}
```

---

## Testing Matrix

### Devices to Test (Minimum)

| Device Type | macOS | Windows | Priority |
|-------------|-------|---------|----------|
| Built-in Laptop Mic | ✅ | ✅ | High |
| USB Headset (Jabra) | ✅ | ✅ | High |
| USB Mic w/ Hardware Knob | ✅ | ✅ | Critical |
| USB Mic w/o Hardware Knob | ✅ | ✅ | High |
| Bluetooth Headset | ✅ | ✅ | Medium |
| XLR Interface (Focusrite) | ✅ | ✅ | Medium |
| Virtual Cable (BlackHole/VB-Cable) | ✅ | ✅ | Low |
| Streaming Software (Voicemeeter) | N/A | ✅ | Low |

### Test Scenarios

1. **Hardware Gain Available**
   - Verify gain changes take effect
   - Verify iterative calibration converges
   - Verify profile persistence

2. **Hardware Gain Unavailable (USB knob)**
   - Verify graceful fallback to digital
   - Verify warning message shown
   - Verify digital gain actually helps

3. **Clipping Scenarios**
   - Hardware clipping (cannot fix)
   - Digital clipping (can fix with gain reduction)
   - Verify appropriate warnings

4. **Permission Denied**
   - macOS sandbox
   - Windows UAC
   - Verify graceful degradation

---

## Success Criteria (Revised)

### Must Have (v2.2.0 Release)
- [ ] Digital gain fallback ALWAYS works (no hardware dependency)
- [ ] Level analysis accurate within ±2 dB
- [ ] Profile save/load functional
- [ ] UI shows clear status (hardware vs digital mode)
- [ ] macOS support (hardware + digital)
- [ ] Windows support (hardware + digital)

### Should Have (v2.2.0 if time permits)
- [ ] Hardware gain works on 70%+ of tested devices
- [ ] Iterative calibration converges in ≤3 attempts
- [ ] Manual override slider
- [ ] Clipping detection and warnings

### Nice to Have (v2.3.0)
- [ ] Linux support (PipeWire/PulseAudio)
- [ ] Advanced 15-second mode
- [ ] Environment presets (office/cafe/studio)
- [ ] Automatic re-tuning on device change

---

## Risk Mitigation Summary

| Risk | Mitigation | Status |
|------|------------|--------|
| Hardware gain unavailable | Digital gain fallback (mandatory) | ✅ Addressed |
| Windows API unstable | pycaw + PolicyConfig dual approach | ✅ Addressed |
| macOS sandboxing | Detect sandbox, use digital-only | ✅ Addressed |
| Linux fragmentation | Prioritize PipeWire, defer to v2.3.0 | ✅ Addressed |
| Timeline overrun | Spike task in Week 1 validates feasibility | ✅ Addressed |
| Device compatibility | 20+ device test matrix | ✅ Planned |

---

## Spike Task Detail: Week 1 API Validation

### Objective
Validate that platform APIs can actually control microphone gain before investing 10 weeks of development.

### Test Script
```python
#!/usr/bin/env python3
"""Spike test for hardware gain control availability."""

import sys
import time

# Platform-specific imports
try:
    if sys.platform == 'darwin':
        from spike_macos import test_macos_gain
        results = test_macos_gain()
    elif sys.platform == 'win32':
        from spike_windows import test_windows_gain
        results = test_windows_gain()
    else:
        print("Linux deferred to v2.3.0")
        sys.exit(0)
    
    # Analyze results
    success_rate = sum(1 for r in results if r.success) / len(results)
    print(f"\n{'='*50}")
    print(f"SUCCESS RATE: {success_rate:.0%} ({sum(1 for r in results if r.success)}/{len(results)})")
    print(f"{'='*50}")
    
    if success_rate >= 0.7:
        print("✅ PROCEED: Hardware gain viable, use dual-mode architecture")
    elif success_rate >= 0.4:
        print("⚠️  CAUTION: Mixed results, prioritize digital gain fallback")
    else:
        print("❌ PIVOT: Hardware gain unreliable, use digital-only with manual guidance")
        
except Exception as e:
    print(f"Spike test failed: {e}")
    sys.exit(1)
```

### Decision Matrix

| Success Rate | Decision | Architecture |
|--------------|----------|--------------|
| ≥70% | Proceed | Dual-mode (hardware primary, digital fallback) |
| 40-69% | Caution | Dual-mode (digital primary, hardware bonus) |
| <40% | Pivot | Digital-only + manual instructions |

---

## Conclusion

This revised proposal addresses the critical technical risks identified in the review:

1. **Digital gain fallback is now mandatory**, not optional
2. **Hardware capability detection** before attempting control
3. **Iterative calibration** with verification
4. **Week 1 spike task** validates feasibility
5. **Linux deferred** to ensure macOS/Windows quality
6. **Timeline revised** to 10 weeks for realistic delivery

The feature remains high-value but now has a **robust fallback strategy** that ensures it works on ALL devices, even if hardware control is unavailable.

---

**Status:** Revised Proposal Ready  
**Next Step:** Approve and begin Week 1 spike task  
**Fallback Plan:** Digital gain always works, hardware control is a bonus  

---

*Last Updated: 2026-02-21 (Revision 2)*  
*Reviewed By: Technical Team*  
