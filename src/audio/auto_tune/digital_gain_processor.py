"""
Digital Gain Processor for Audio Auto-Tune

Software-based gain adjustment that works on ALL devices.
This is the mandatory fallback when hardware gain control is unavailable.
"""

import time
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class DigitalGainSettings:
    """Settings for digital gain on a specific device."""
    device_id: int
    gain_db: float
    multiplier: float
    noise_floor_db: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0


class DigitalGainProcessor:
    """
    Software gain processor for PCM audio buffers.
    
    This is the FALLBACK when hardware gain control is unavailable.
    It multiplies audio samples before they reach the VAD/ASR pipeline.
    
    Limitations:
    - Cannot fix hardware clipping (distortion inside the mic)
    - Amplifies noise along with signal
    - Best for fixing low signal issues
    
    Benefits:
    - Works on 100% of devices
    - No OS dependencies
    - Low latency (<5ms)
    """
    
    def __init__(self, max_gain_db: float = 20.0, min_gain_db: float = -20.0):
        """
        Initialize digital gain processor.
        
        Args:
            max_gain_db: Maximum gain to apply (+20 dB default)
            min_gain_db: Minimum gain to apply (-20 dB default)
        """
        self._max_gain_db = max_gain_db
        self._min_gain_db = min_gain_db
        
        # Device settings storage
        self._settings: Dict[int, DigitalGainSettings] = {}
        
        # Warnings for devices with high noise floors
        self._warnings: Dict[int, List[str]] = {}
        
        logger.info(f"DigitalGainProcessor initialized "
                   f"(range: {min_gain_db} to +{max_gain_db} dB)")
    
    def set_gain(self, device_id: int, target_db: float,
                 noise_floor_db: Optional[float] = None) -> float:
        """
        Set digital gain for a device.
        
        NEW: Warns and limits gain if noise floor is too high.
        
        Args:
            device_id: Audio device ID
            target_db: Target gain in dB
            noise_floor_db: Measured noise floor (for warnings)
            
        Returns:
            Actual gain applied (may be limited)
        """
        # Limit to safe range
        original_target = target_db
        target_db = max(self._min_gain_db, min(target_db, self._max_gain_db))
        
        if original_target != target_db:
            logger.warning(f"Gain {original_target:.1f}dB limited to {target_db:.1f}dB")
        
        # NEW: Noise floor check before applying high gain
        warnings = []
        if noise_floor_db is not None:
            if noise_floor_db > -40:
                # High noise floor - limit digital gain
                limited_gain = min(target_db, 10.0)  # Cap at +10dB
                if limited_gain < target_db:
                    warnings.append(
                        f"High noise floor ({noise_floor_db:.1f}dB) - "
                        f"limiting digital gain from {target_db:.1f}dB to {limited_gain:.1f}dB"
                    )
                    logger.warning(warnings[-1])
                    target_db = limited_gain
            
            # Warn about noise amplification
            if target_db > 0 and noise_floor_db > -50:
                warnings.append(
                    f"Digital gain of +{target_db:.1f}dB will amplify noise floor "
                    f"from {noise_floor_db:.1f}dB to approximately "
                    f"{noise_floor_db + target_db:.1f}dB"
                )
                logger.warning(warnings[-1])
        
        # Convert dB to linear multiplier
        # gain_db = 20 * log10(multiplier)
        # multiplier = 10^(gain_db / 20)
        multiplier = 10 ** (target_db / 20)
        
        # Store settings
        now = datetime.now()
        if device_id in self._settings:
            # Update existing
            self._settings[device_id].gain_db = target_db
            self._settings[device_id].multiplier = multiplier
            self._settings[device_id].noise_floor_db = noise_floor_db
            self._settings[device_id].last_accessed = now
        else:
            # Create new
            self._settings[device_id] = DigitalGainSettings(
                device_id=device_id,
                gain_db=target_db,
                multiplier=multiplier,
                noise_floor_db=noise_floor_db,
                created_at=now,
                last_accessed=now
            )
        
        # Store warnings
        if warnings:
            self._warnings[device_id] = warnings
        
        logger.info(f"Digital gain set for device {device_id}: "
                   f"{target_db:.1f} dB (multiplier: {multiplier:.3f})")
        
        return target_db
    
    def get_gain(self, device_id: int) -> float:
        """
        Get current digital gain for a device.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            Current gain in dB (0.0 if not set)
        """
        if device_id in self._settings:
            self._settings[device_id].last_accessed = datetime.now()
            self._settings[device_id].access_count += 1
            return self._settings[device_id].gain_db
        return 0.0
    
    def get_multiplier(self, device_id: int) -> float:
        """
        Get current gain multiplier for a device.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            Current multiplier (1.0 if not set)
        """
        if device_id in self._settings:
            self._settings[device_id].last_accessed = datetime.now()
            self._settings[device_id].access_count += 1
            return self._settings[device_id].multiplier
        return 1.0
    
    def process_buffer(self, device_id: int, 
                       audio_buffer: np.ndarray) -> np.ndarray:
        """
        Apply digital gain to audio buffer.
        
        Called by the audio pipeline before VAD/ASR processing.
        Includes latency monitoring and soft clipping.
        
        Args:
            device_id: Audio device ID
            audio_buffer: Input audio samples
            
        Returns:
            Amplified audio buffer
        """
        start_time = time.perf_counter()
        
        # Get multiplier
        multiplier = self.get_multiplier(device_id)
        
        # No gain needed
        if multiplier == 1.0:
            return audio_buffer
        
        # Apply gain
        amplified = audio_buffer * multiplier
        
        # Soft clipping to prevent digital distortion
        # Use tanh for smooth limiting when approaching clipping
        max_val = np.max(np.abs(amplified))
        if max_val > 0.95:
            # Apply soft clipping
            amplified = np.tanh(amplified)
            logger.debug(f"Soft clipping applied (max was {max_val:.2f})")
        
        # Latency monitoring
        elapsed = time.perf_counter() - start_time
        if elapsed > 0.005:  # 5ms budget
            logger.warning(f"Digital gain processing exceeded latency budget: "
                          f"{elapsed*1000:.1f}ms (target: <5ms)")
        
        return amplified
    
    def reset_gain(self, device_id: int):
        """Reset gain to 0 dB for a device."""
        if device_id in self._settings:
            self._settings[device_id].gain_db = 0.0
            self._settings[device_id].multiplier = 1.0
            logger.info(f"Digital gain reset for device {device_id}")
    
    def get_warnings(self, device_id: int) -> List[str]:
        """Get warnings for a device."""
        return self._warnings.get(device_id, [])
    
    def clear_warnings(self, device_id: int):
        """Clear warnings for a device."""
        if device_id in self._warnings:
            del self._warnings[device_id]
    
    def cleanup_inactive_devices(self, max_age_hours: int = 24):
        """
        Remove gain settings for devices not used recently.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []
        
        for device_id, settings in self._settings.items():
            if settings.last_accessed < cutoff:
                to_remove.append(device_id)
        
        for device_id in to_remove:
            del self._settings[device_id]
            if device_id in self._warnings:
                del self._warnings[device_id]
            logger.debug(f"Cleaned up inactive device {device_id}")
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive device(s)")
    
    def get_active_devices(self) -> List[int]:
        """Get list of devices with active gain settings."""
        return list(self._settings.keys())
    
    def get_device_info(self, device_id: int) -> Optional[Dict]:
        """Get information about a device's gain settings."""
        if device_id not in self._settings:
            return None
        
        settings = self._settings[device_id]
        return {
            'device_id': device_id,
            'gain_db': settings.gain_db,
            'multiplier': settings.multiplier,
            'noise_floor_db': settings.noise_floor_db,
            'created_at': settings.created_at.isoformat(),
            'last_accessed': settings.last_accessed.isoformat(),
            'access_count': settings.access_count,
            'warnings': self._warnings.get(device_id, [])
        }
