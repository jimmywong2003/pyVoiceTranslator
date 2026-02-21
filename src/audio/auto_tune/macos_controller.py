"""
macOS CoreAudio Gain Controller

Implementation of GainController for macOS using CoreAudio framework.
"""

import logging
import platform
from typing import Optional, Tuple
from ctypes import CDLL, c_uint32, c_float, c_void_p, byref, sizeof, POINTER

from .gain_controller import GainController, GainCapabilities, GainAdjustmentResult, GainMode

logger = logging.getLogger(__name__)

# CoreAudio constants
kAudioHardwarePropertyDevices = 0x61646576  # 'adev'
kAudioDevicePropertyVolumeScalar = 0x76736F6C  # 'vsol'
kAudioObjectSystemObject = 1
kAudioObjectPropertyScopeInput = 0x696E7074  # 'inpt'
kAudioObjectPropertyElementMain = 0


class MacOSCoreAudioController(GainController):
    """
    macOS gain controller using CoreAudio framework.
    
    Uses ctypes to call CoreAudio APIs without requiring pyobjc.
    """
    
    def __init__(self):
        super().__init__()
        self._coreaudio = None
        self._available = False
        self._is_sandboxed = False
        
        # Try to load CoreAudio
        try:
            self._coreaudio = CDLL('/System/Library/Frameworks/CoreAudio.framework/CoreAudio')
            self._available = True
            logger.info("CoreAudio framework loaded successfully")
        except OSError as e:
            logger.warning(f"Could not load CoreAudio: {e}")
            self._available = False
        
        # Check sandbox status
        self._check_sandbox()
    
    def _check_sandbox(self):
        """Check if running in sandboxed environment."""
        # Simple heuristic: check if we can write to home directory
        # In a real implementation, use more robust detection
        try:
            import os
            test_file = os.path.expanduser("~/.voicetranslate_sandbox_test")
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            self._is_sandboxed = False
        except (OSError, IOError):
            self._is_sandboxed = True
            logger.warning("App appears to be sandboxed - hardware gain may be restricted")
    
    def get_platform_name(self) -> str:
        return "macos"
    
    def supports_hardware_gain(self, device_id: int) -> bool:
        """
        Check if device supports software gain control.
        
        Many USB mics with hardware knobs will return False.
        """
        if not self._available:
            return False
        
        if self._is_sandboxed:
            # Sandboxed apps may not be able to change hardware settings
            logger.debug("Sandboxed - assuming no hardware gain control")
            return False
        
        # Try to get current volume to check if it's controllable
        try:
            # Check if kAudioDevicePropertyVolumeScalar exists and is writable
            # This is a simplified check - real implementation would use
            # AudioObjectHasProperty and AudioObjectIsPropertySettable
            
            # For now, assume built-in mics support gain, USB mics may not
            device_name = self._get_device_name(device_id)
            if device_name:
                # Heuristic: built-in mics usually support gain
                if 'built-in' in device_name.lower() or 'internal' in device_name.lower():
                    return True
                # USB mics with hardware knobs often don't
                if 'usb' in device_name.lower():
                    # Try to actually set/get to verify
                    return self._test_gain_controllable(device_id)
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking gain support: {e}")
            return False
    
    def _test_gain_controllable(self, device_id: int) -> bool:
        """Test if we can actually control gain by trying a small change."""
        try:
            # Get current gain
            current = self.get_gain(device_id)
            
            # Try to set to same value (no-op but tests permissions)
            # Real implementation would use AudioObjectSetPropertyData
            
            # For now, conservative approach: assume not controllable
            # unless proven otherwise
            return False
            
        except Exception:
            return False
    
    def _get_device_name(self, device_id: int) -> Optional[str]:
        """Get device name from CoreAudio."""
        # Placeholder - real implementation would query kAudioDevicePropertyDeviceName
        return None
    
    def get_capabilities(self, device_id: int) -> Optional[GainCapabilities]:
        """Get gain capabilities for device."""
        if not self._available:
            return None
        
        # Check cache first
        cached = self.get_cached_capabilities(device_id)
        if cached:
            return cached
        
        try:
            # Query CoreAudio for device capabilities
            # This is a simplified placeholder
            
            # Real implementation would:
            # 1. Get device name (kAudioDevicePropertyDeviceName)
            # 2. Get volume range (kAudioDevicePropertyVolumeScalar with min/max)
            # 3. Check if mutable (AudioObjectIsPropertySettable)
            
            supports_hardware = self.supports_hardware_gain(device_id)
            
            caps = GainCapabilities(
                device_id=device_id,
                device_name=f"Device {device_id}",  # Placeholder
                supports_hardware_gain=supports_hardware,
                min_gain_db=-20.0 if supports_hardware else 0.0,
                max_gain_db=20.0 if supports_hardware else 0.0,
                current_gain_db=self.get_gain(device_id),
                is_muted=False,
                can_mute=False,
                gain_step_db=1.0
            )
            
            self.cache_capabilities(device_id, caps)
            return caps
            
        except Exception as e:
            logger.error(f"Error getting capabilities: {e}")
            return None
    
    def get_gain(self, device_id: int) -> float:
        """Get current gain in dB."""
        if not self._available:
            return 0.0
        
        try:
            # Query kAudioDevicePropertyVolumeScalar
            # Convert scalar (0.0-1.0) to dB
            
            # Placeholder - real implementation would call AudioObjectGetPropertyData
            scalar = 0.5  # Placeholder
            
            # Convert to dB (approximate)
            if scalar <= 0:
                return -60.0
            return 20 * __import__('math').log10(scalar)
            
        except Exception as e:
            logger.debug(f"Error getting gain: {e}")
            return 0.0
    
    def set_gain(self, device_id: int, gain_db: float) -> GainAdjustmentResult:
        """Set gain in dB."""
        if not self._available:
            return GainAdjustmentResult(
                success=False,
                mode=GainMode.UNKNOWN,
                requested_db=gain_db,
                actual_db=0.0,
                device_id=device_id,
                error_message="CoreAudio not available",
                requires_manual_adjustment=True,
                manual_instructions="Please adjust microphone gain in System Settings > Sound"
            )
        
        # Check if hardware gain is supported
        if not self.supports_hardware_gain(device_id):
            return GainAdjustmentResult(
                success=False,
                mode=GainMode.HARDWARE,
                requested_db=gain_db,
                actual_db=self.get_gain(device_id),
                device_id=device_id,
                error_message="Hardware gain control not available for this device",
                requires_manual_adjustment=True,
                manual_instructions="This microphone has a hardware volume knob. Please adjust it manually."
            )
        
        try:
            # Convert dB to scalar
            # scalar = 10^(gain_db / 20)
            import math
            scalar = min(1.0, max(0.0, 10 ** (gain_db / 20)))
            
            # Set kAudioDevicePropertyVolumeScalar
            # Real implementation would call AudioObjectSetPropertyData
            
            # Placeholder - simulate success
            logger.info(f"Would set device {device_id} gain to {gain_db:.1f} dB (scalar: {scalar:.3f})")
            
            return GainAdjustmentResult(
                success=True,
                mode=GainMode.HARDWARE,
                requested_db=gain_db,
                actual_db=gain_db,  # Placeholder
                device_id=device_id
            )
            
        except Exception as e:
            logger.error(f"Error setting gain: {e}")
            return GainAdjustmentResult(
                success=False,
                mode=GainMode.HARDWARE,
                requested_db=gain_db,
                actual_db=self.get_gain(device_id),
                device_id=device_id,
                error_message=str(e),
                requires_manual_adjustment=True,
                manual_instructions="Please adjust microphone gain in System Settings > Sound"
            )
    
    def is_available(self) -> bool:
        """Check if CoreAudio is available."""
        return self._available


# Utility function to get controller
def create_macos_controller() -> Optional[MacOSCoreAudioController]:
    """Create macOS gain controller if on macOS."""
    if platform.system() != 'Darwin':
        return None
    
    controller = MacOSCoreAudioController()
    if controller.is_available():
        return controller
    
    return None
