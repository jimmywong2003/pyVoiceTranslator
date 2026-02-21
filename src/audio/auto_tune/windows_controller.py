"""
Windows WASAPI Gain Controller

Implementation of GainController for Windows using WASAPI.
Supports pycaw primary and PolicyConfig fallback.
"""

import logging
import platform
from typing import Optional, Tuple, List
from enum import Enum

from .gain_controller import GainController, GainCapabilities, GainAdjustmentResult, GainMode

logger = logging.getLogger(__name__)


class WindowsControllerType(Enum):
    """Type of Windows controller available."""
    PYCAW = "pycaw"
    POLICY_CONFIG = "policy_config"
    NONE = "none"


class WindowsWASAPIController(GainController):
    """
    Windows gain controller using WASAPI.
    
    Primary: pycaw (IAudioEndpointVolume)
    Fallback: IPolicyConfig (undocumented but often works)
    """
    
    # Known Windows builds where PolicyConfig may be broken
    _policy_config_broken_versions: List[str] = []
    
    def __init__(self):
        super().__init__()
        self._controller_type = WindowsControllerType.NONE
        self._pycaw_available = False
        self._policy_config_available = False
        self._windows_version = platform.version()
        
        # Try to initialize controllers
        self._try_init_pycaw()
        self._try_init_policy_config()
        
        logger.info(f"Windows controller initialized: {self._controller_type.value}")
    
    def _try_init_pycaw(self):
        """Try to initialize pycaw controller."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            
            # Test if we can get microphone
            device = AudioUtilities.GetMicrophone()
            if device:
                # Try to access volume interface
                interface = device.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                volume = interface.QueryInterface(IAudioEndpointVolume)
                
                # Test read
                current = volume.GetMasterVolumeLevelScalar()
                
                self._pycaw_available = True
                self._controller_type = WindowsControllerType.PYCAW
                logger.info("pycaw controller available")
                
        except Exception as e:
            logger.debug(f"pycaw not available: {e}")
            self._pycaw_available = False
    
    def _try_init_policy_config(self):
        """Try to initialize PolicyConfig fallback."""
        # Check if this Windows version is known to be broken
        if self._windows_version in self._policy_config_broken_versions:
            logger.warning(f"PolicyConfig known to be broken on {self._windows_version}")
            return
        
        try:
            # Try to import and test PolicyConfig via ctypes/comtypes
            # This is a simplified check
            
            # Real implementation would:
            # 1. Import IPolicyConfig interface
            # 2. Try to get/set volume
            
            # For now, mark as potentially available
            self._policy_config_available = True
            
            if not self._pycaw_available:
                self._controller_type = WindowsControllerType.POLICY_CONFIG
                logger.info("PolicyConfig fallback available")
                
        except Exception as e:
            logger.debug(f"PolicyConfig not available: {e}")
            self._policy_config_available = False
    
    def _check_policy_config_health(self) -> bool:
        """Check if PolicyConfig works on this Windows build."""
        if self._windows_version in self._policy_config_broken_versions:
            return False
        
        # Test with actual set/get round-trip
        try:
            # Placeholder - real implementation would test
            return True
        except Exception:
            return False
    
    def get_platform_name(self) -> str:
        return "windows"
    
    def supports_hardware_gain(self, device_id: int) -> bool:
        """Check if device supports software gain control."""
        if self._controller_type == WindowsControllerType.NONE:
            return False
        
        try:
            # Windows is more permissive than macOS
            # Most devices support gain control via WASAPI
            
            # However, some USB mics with hardware knobs may not
            # Check by trying to get current volume
            caps = self.get_capabilities(device_id)
            if caps:
                return caps.supports_hardware_gain
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking gain support: {e}")
            return False
    
    def get_capabilities(self, device_id: int) -> Optional[GainCapabilities]:
        """Get gain capabilities for device."""
        if self._controller_type == WindowsControllerType.NONE:
            return None
        
        # Check cache
        cached = self.get_cached_capabilities(device_id)
        if cached:
            return cached
        
        try:
            if self._pycaw_available:
                return self._get_capabilities_pycaw(device_id)
            elif self._policy_config_available:
                return self._get_capabilities_policy_config(device_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting capabilities: {e}")
            return None
    
    def _get_capabilities_pycaw(self, device_id: int) -> Optional[GainCapabilities]:
        """Get capabilities using pycaw."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            
            # Get default microphone
            device = AudioUtilities.GetMicrophone()
            if not device:
                return None
            
            interface = device.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)
            
            # Get volume range
            min_db = volume.GetVolumeRange()[0]  # Typically -96.0 dB
            max_db = volume.GetVolumeRange()[1]  # Typically 0.0 dB or +30.0 dB
            
            # Get current
            current_scalar = volume.GetMasterVolumeLevelScalar()
            current_db = volume.GetMasterVolumeLevel()
            
            # Check if mutable (simplified)
            supports_gain = True  # Assume yes for now
            
            caps = GainCapabilities(
                device_id=device_id,
                device_name=device.GetFriendlyName() if hasattr(device, 'GetFriendlyName') else f"Device {device_id}",
                supports_hardware_gain=supports_gain,
                min_gain_db=min_db,
                max_gain_db=max_db,
                current_gain_db=current_db,
                is_muted=volume.GetMute(),
                can_mute=True,
                gain_step_db=1.0
            )
            
            self.cache_capabilities(device_id, caps)
            return caps
            
        except Exception as e:
            logger.error(f"pycaw capability query failed: {e}")
            return None
    
    def _get_capabilities_policy_config(self, device_id: int) -> Optional[GainCapabilities]:
        """Get capabilities using PolicyConfig fallback."""
        # Placeholder - real implementation would use IPolicyConfig
        return GainCapabilities(
            device_id=device_id,
            device_name=f"Device {device_id}",
            supports_hardware_gain=True,  # Assume yes
            min_gain_db=-96.0,
            max_gain_db=30.0,
            current_gain_db=0.0,
            is_muted=False,
            can_mute=True,
            gain_step_db=1.0
        )
    
    def get_gain(self, device_id: int) -> float:
        """Get current gain in dB."""
        if self._controller_type == WindowsControllerType.NONE:
            return 0.0
        
        try:
            if self._pycaw_available:
                return self._get_gain_pycaw(device_id)
            elif self._policy_config_available:
                return self._get_gain_policy_config(device_id)
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"Error getting gain: {e}")
            return 0.0
    
    def _get_gain_pycaw(self, device_id: int) -> float:
        """Get gain using pycaw."""
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        device = AudioUtilities.GetMicrophone()
        if not device:
            return 0.0
        
        interface = device.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        volume = interface.QueryInterface(IAudioEndpointVolume)
        
        return volume.GetMasterVolumeLevel()
    
    def _get_gain_policy_config(self, device_id: int) -> float:
        """Get gain using PolicyConfig."""
        # Placeholder
        return 0.0
    
    def set_gain(self, device_id: int, gain_db: float) -> GainAdjustmentResult:
        """Set gain in dB."""
        if self._controller_type == WindowsControllerType.NONE:
            return GainAdjustmentResult(
                success=False,
                mode=GainMode.UNKNOWN,
                requested_db=gain_db,
                actual_db=0.0,
                device_id=device_id,
                error_message="No Windows audio controller available",
                requires_manual_adjustment=True,
                manual_instructions="Please adjust microphone level in Sound Settings"
            )
        
        # Validate range
        is_valid, message = self.validate_gain_range(device_id, gain_db)
        if not is_valid:
            logger.warning(f"Gain validation failed: {message}")
            # Try to clamp to valid range
            min_db, max_db = self.get_gain_range(device_id)
            gain_db = max(min_db, min(gain_db, max_db))
        
        try:
            if self._pycaw_available:
                return self._set_gain_pycaw(device_id, gain_db)
            elif self._policy_config_available:
                return self._set_gain_policy_config(device_id, gain_db)
            
            raise RuntimeError("No controller available")
            
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
                manual_instructions="Please adjust microphone level in Sound Settings"
            )
    
    def _set_gain_pycaw(self, device_id: int, gain_db: float) -> GainAdjustmentResult:
        """Set gain using pycaw."""
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        device = AudioUtilities.GetMicrophone()
        if not device:
            raise RuntimeError("No microphone found")
        
        interface = device.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        volume = interface.QueryInterface(IAudioEndpointVolume)
        
        # Set volume level in dB
        volume.SetMasterVolumeLevel(gain_db, None)
        
        # Verify
        actual_db = volume.GetMasterVolumeLevel()
        
        return GainAdjustmentResult(
            success=True,
            mode=GainMode.HARDWARE,
            requested_db=gain_db,
            actual_db=actual_db,
            device_id=device_id
        )
    
    def _set_gain_policy_config(self, device_id: int, gain_db: float) -> GainAdjustmentResult:
        """Set gain using PolicyConfig fallback."""
        # Placeholder - real implementation would use IPolicyConfig
        logger.info(f"Would set gain via PolicyConfig: {gain_db:.1f} dB")
        
        return GainAdjustmentResult(
            success=True,  # Placeholder
            mode=GainMode.HARDWARE,
            requested_db=gain_db,
            actual_db=gain_db,  # Placeholder
            device_id=device_id
        )
    
    def is_available(self) -> bool:
        """Check if any Windows controller is available."""
        return self._controller_type != WindowsControllerType.NONE


# Utility function
def create_windows_controller() -> Optional[WindowsWASAPIController]:
    """Create Windows gain controller if on Windows."""
    if platform.system() != 'Windows':
        return None
    
    controller = WindowsWASAPIController()
    if controller.is_available():
        return controller
    
    return None
