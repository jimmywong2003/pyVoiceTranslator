"""
Gain Controller Abstract Base Class

Defines the interface for platform-specific gain control implementations.
Supports both hardware gain control and software digital gain fallback.
"""

import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GainMode(Enum):
    """Gain control mode."""
    HARDWARE = "hardware"  # OS/hardware gain control
    DIGITAL = "digital"    # Software PCM multiplication
    UNKNOWN = "unknown"    # Not yet determined


@dataclass
class GainCapabilities:
    """Capabilities of a device's gain control."""
    device_id: int
    device_name: str
    supports_hardware_gain: bool
    min_gain_db: float
    max_gain_db: float
    current_gain_db: float
    is_muted: bool
    can_mute: bool
    gain_step_db: float  # Smallest adjustable step


@dataclass
class GainAdjustmentResult:
    """Result of a gain adjustment attempt."""
    success: bool
    mode: GainMode
    requested_db: float
    actual_db: float
    device_id: int
    error_message: Optional[str] = None
    requires_manual_adjustment: bool = False
    manual_instructions: Optional[str] = None


class GainController(ABC):
    """
    Abstract base class for platform-specific gain control.
    
    Implementations must handle:
    1. Hardware capability detection
    2. Hardware gain get/set (if available)
    3. Graceful fallback when hardware control unavailable
    """
    
    def __init__(self):
        self._capabilities_cache: Dict[int, GainCapabilities] = {}
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return platform name (e.g., 'macos', 'windows', 'linux')."""
        pass
    
    @abstractmethod
    def supports_hardware_gain(self, device_id: int) -> bool:
        """
        Check if the OS allows changing mic gain for this device.
        
        Many USB mics (Blue Yeti, Rode NT-USB) have hardware knobs
        and ignore OS gain commands. This method detects that.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            True if hardware gain control is available and working
        """
        pass
    
    @abstractmethod
    def get_capabilities(self, device_id: int) -> Optional[GainCapabilities]:
        """
        Get gain capabilities for a device.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            GainCapabilities or None if device not found
        """
        pass
    
    @abstractmethod
    def get_gain(self, device_id: int) -> float:
        """
        Get current microphone gain in dB.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            Current gain in dB (0.0 if not available)
        """
        pass
    
    @abstractmethod
    def set_gain(self, device_id: int, gain_db: float) -> GainAdjustmentResult:
        """
        Set microphone gain in dB.
        
        Args:
            device_id: Audio device ID
            gain_db: Target gain in dB
            
        Returns:
            GainAdjustmentResult with success status and actual gain applied
        """
        pass
    
    def validate_gain_range(self, device_id: int, target_db: float) -> Tuple[bool, str]:
        """
        Validate target gain is within device capabilities.
        
        Args:
            device_id: Audio device ID
            target_db: Target gain in dB
            
        Returns:
            Tuple of (is_valid, message)
        """
        caps = self.get_capabilities(device_id)
        if not caps:
            return False, "Device capabilities not available"
        
        if target_db < caps.min_gain_db or target_db > caps.max_gain_db:
            return False, (f"Target {target_db:.1f}dB outside range "
                          f"[{caps.min_gain_db:.1f}, {caps.max_gain_db:.1f}]")
        
        return True, "OK"
    
    def is_gain_available(self, device_id: int) -> bool:
        """
        Check if any form of gain control is available.
        
        Returns True if either hardware or digital gain can be applied.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            True if gain control is available
        """
        # Hardware gain available?
        if self.supports_hardware_gain(device_id):
            return True
        
        # Device exists?
        caps = self.get_capabilities(device_id)
        return caps is not None
    
    def get_gain_range(self, device_id: int) -> Tuple[float, float]:
        """
        Get min/max gain range for device.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            Tuple of (min_db, max_db)
        """
        caps = self.get_capabilities(device_id)
        if caps:
            return (caps.min_gain_db, caps.max_gain_db)
        return (-20.0, 20.0)  # Default range
    
    def cache_capabilities(self, device_id: int, caps: GainCapabilities):
        """Cache capabilities for a device."""
        self._capabilities_cache[device_id] = caps
    
    def get_cached_capabilities(self, device_id: int) -> Optional[GainCapabilities]:
        """Get cached capabilities for a device."""
        return self._capabilities_cache.get(device_id)
    
    def clear_cache(self):
        """Clear capabilities cache."""
        self._capabilities_cache.clear()


# Platform-specific controller implementations will be in separate files:
# - macos_controller.py
# - windows_controller.py  
# - linux_controller.py
