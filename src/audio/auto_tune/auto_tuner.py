"""
Audio Auto-Tuner - Main Coordinator

Coordinates level analysis, gain control, and digital gain processing
for automatic microphone gain optimization.
"""

import logging
import threading
import platform
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .level_analyzer import LevelAnalyzer, AudioMetrics, CalibrationResult
from .digital_gain_processor import DigitalGainProcessor
from .gain_controller import GainController, GainMode, GainAdjustmentResult

logger = logging.getLogger(__name__)


@dataclass
class TuneResult:
    """Result of auto-tuning operation."""
    success: bool
    device_id: int
    mode: GainMode
    initial_metrics: Optional[AudioMetrics]
    final_metrics: Optional[AudioMetrics]
    gain_change_db: float
    message: str
    requires_manual_action: bool = False
    manual_instructions: Optional[str] = None


class AudioAutoTuner:
    """
    Main coordinator for automatic audio gain tuning.
    
    Features:
    - Dual-mode gain control (hardware + digital fallback)
    - Iterative calibration with verification
    - Thread-safe gain adjustments
    - Platform-specific optimizations
    
    Usage:
        >>> tuner = AudioAutoTuner()
        >>> result = tuner.quick_tune(device_id=2)
        >>> if result.success:
        ...     print(f"Tuned to {result.final_metrics.rms_db:.1f} dB")
    """
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize audio auto-tuner.
        
        Args:
            sample_rate: Audio sample rate (default 16000 Hz)
        """
        self.sample_rate = sample_rate
        
        # Core components
        self.analyzer = LevelAnalyzer(sample_rate)
        self.digital_processor = DigitalGainProcessor()
        
        # Platform-specific hardware controller
        self.hardware_controller: Optional[GainController] = self._create_platform_controller()
        
        # Threading lock for gain adjustments
        self._gain_lock = threading.Lock()
        
        # Callback for capturing audio (set by user)
        self._capture_callback: Optional[Callable[[], Any]] = None
        
        logger.info(f"AudioAutoTuner initialized ({platform.system()})")
        if self.hardware_controller:
            logger.info(f"Hardware controller: {self.hardware_controller.get_platform_name()}")
        else:
            logger.info("No hardware controller - using digital gain only")
    
    def _create_platform_controller(self) -> Optional[GainController]:
        """Create platform-specific gain controller."""
        system = platform.system()
        
        try:
            if system == 'Darwin':  # macOS
                from .macos_controller import create_macos_controller
                return create_macos_controller()
            
            elif system == 'Windows':
                from .windows_controller import create_windows_controller
                return create_windows_controller()
            
            elif system == 'Linux':
                # Linux support deferred to v2.3.0
                logger.info("Linux gain controller deferred to v2.3.0")
                return None
            
            else:
                logger.warning(f"Unsupported platform: {system}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating platform controller: {e}")
            return None
    
    def set_capture_callback(self, callback: Callable[[], Any]):
        """
        Set callback for capturing audio samples.
        
        The callback should return a numpy array of audio samples.
        
        Args:
            callback: Function that returns audio buffer
        """
        self._capture_callback = callback
    
    def _capture_audio(self, duration: float = 2.0) -> Optional[Any]:
        """Capture audio using callback or default method."""
        if self._capture_callback:
            return self._capture_callback()
        
        # Default: capture using sounddevice
        try:
            import sounddevice as sd
            import numpy as np
            
            samples = int(duration * self.sample_rate)
            audio = sd.rec(samples, samplerate=self.sample_rate, 
                          channels=1, dtype=np.float32)
            sd.wait()
            return audio.flatten()
            
        except Exception as e:
            logger.error(f"Failed to capture audio: {e}")
            return None
    
    def quick_tune(self, device_id: int, 
                   target_peak_db: float = -6.0,
                   target_rms_db: float = -18.0) -> TuneResult:
        """
        Quick 5-second auto-tuning.
        
        Args:
            device_id: Audio device ID
            target_peak_db: Target peak level (-6 dB default)
            target_rms_db: Target RMS level (-18 dB default)
            
        Returns:
            TuneResult with tuning status
        """
        logger.info(f"Starting quick tune for device {device_id}")
        
        # Step 1: Measure initial state
        initial_buffer = self._capture_audio(duration=2.0)
        if initial_buffer is None:
            return TuneResult(
                success=False,
                device_id=device_id,
                mode=GainMode.UNKNOWN,
                initial_metrics=None,
                final_metrics=None,
                gain_change_db=0.0,
                message="Failed to capture initial audio"
            )
        
        initial_metrics = self.analyzer.analyze_buffer(initial_buffer)
        logger.info(f"Initial levels - Peak: {initial_metrics.peak_db:.1f} dB, "
                   f"RMS: {initial_metrics.rms_db:.1f} dB")
        
        # Step 2: Check if already optimal
        if (abs(initial_metrics.peak_db - target_peak_db) < 3 and
            abs(initial_metrics.rms_db - target_rms_db) < 3):
            logger.info("Levels already optimal")
            return TuneResult(
                success=True,
                device_id=device_id,
                mode=GainMode.UNKNOWN,
                initial_metrics=initial_metrics,
                final_metrics=initial_metrics,
                gain_change_db=0.0,
                message="Levels already optimal"
            )
        
        # Step 3: Calculate required gain adjustment
        gain_adjustment = self.analyzer.get_optimal_gain_adjustment(
            initial_metrics, target_peak_db, target_rms_db
        )
        
        logger.info(f"Calculated gain adjustment: {gain_adjustment:.1f} dB")
        
        # Step 4: Apply gain (thread-safe)
        with self._gain_lock:
            result = self._apply_gain(device_id, gain_adjustment, initial_metrics)
        
        if not result.success:
            return TuneResult(
                success=False,
                device_id=device_id,
                mode=result.mode,
                initial_metrics=initial_metrics,
                final_metrics=None,
                gain_change_db=0.0,
                message=result.error_message or "Gain adjustment failed",
                requires_manual_action=result.requires_manual_adjustment,
                manual_instructions=result.manual_instructions
            )
        
        # Step 5: Verify with second measurement
        final_buffer = self._capture_audio(duration=2.0)
        if final_buffer is not None:
            final_metrics = self.analyzer.analyze_buffer(final_buffer)
            logger.info(f"Final levels - Peak: {final_metrics.peak_db:.1f} dB, "
                       f"RMS: {final_metrics.rms_db:.1f} dB")
        else:
            final_metrics = None
        
        return TuneResult(
            success=True,
            device_id=device_id,
            mode=result.mode,
            initial_metrics=initial_metrics,
            final_metrics=final_metrics,
            gain_change_db=gain_adjustment,
            message=f"Tuning successful ({result.mode.value})"
        )
    
    def _apply_gain(self, device_id: int, gain_db: float,
                    metrics: AudioMetrics) -> GainAdjustmentResult:
        """
        Apply gain adjustment using best available method.
        
        Strategy:
        1. Try hardware gain if available
        2. Fall back to digital gain
        3. Return result with mode indication
        """
        # Try hardware gain first
        if self.hardware_controller and self.hardware_controller.supports_hardware_gain(device_id):
            logger.info("Attempting hardware gain adjustment")
            result = self.hardware_controller.set_gain(device_id, gain_db)
            
            if result.success:
                logger.info("Hardware gain adjustment successful")
                return result
            
            logger.warning(f"Hardware gain failed: {result.error_message}")
            # Fall through to digital gain
        
        # Use digital gain fallback
        logger.info("Using digital gain fallback")
        
        # Check noise floor before applying high gain
        noise_floor = metrics.noise_floor_db if metrics else None
        actual_gain = self.digital_processor.set_gain(
            device_id, gain_db, noise_floor_db=noise_floor
        )
        
        # Get warnings
        warnings = self.digital_processor.get_warnings(device_id)
        message = "Digital gain applied"
        if warnings:
            message += f" (warnings: {'; '.join(warnings)})"
        
        return GainAdjustmentResult(
            success=True,
            mode=GainMode.DIGITAL,
            requested_db=gain_db,
            actual_db=actual_gain,
            device_id=device_id,
            error_message=message if warnings else None
        )
    
    def get_device_status(self, device_id: int) -> Dict[str, Any]:
        """Get current status of a device."""
        status = {
            'device_id': device_id,
            'hardware_controller': self.hardware_controller is not None,
            'digital_gain_db': self.digital_processor.get_gain(device_id),
        }
        
        if self.hardware_controller:
            status['hardware_gain_db'] = self.hardware_controller.get_gain(device_id)
            status['supports_hardware'] = self.hardware_controller.supports_hardware_gain(device_id)
            caps = self.hardware_controller.get_capabilities(device_id)
            if caps:
                status['capabilities'] = {
                    'min_db': caps.min_gain_db,
                    'max_db': caps.max_gain_db,
                    'can_mute': caps.can_mute
                }
        
        return status
    
    def reset_device(self, device_id: int):
        """Reset gain to default for a device."""
        with self._gain_lock:
            # Reset hardware gain if available
            if self.hardware_controller:
                try:
                    self.hardware_controller.set_gain(device_id, 0.0)
                except Exception as e:
                    logger.debug(f"Could not reset hardware gain: {e}")
            
            # Reset digital gain
            self.digital_processor.reset_gain(device_id)
        
        logger.info(f"Reset gain for device {device_id}")
    
    def process_audio_buffer(self, device_id: int, audio_buffer) -> Any:
        """
        Process audio buffer through digital gain.
        
        This should be called in the audio pipeline before VAD/ASR.
        
        Args:
            device_id: Audio device ID
            audio_buffer: Input audio samples
            
        Returns:
            Processed audio buffer with gain applied
        """
        return self.digital_processor.process_buffer(device_id, audio_buffer)
