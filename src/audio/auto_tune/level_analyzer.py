"""
Level Analyzer for Audio Auto-Tune

Analyzes audio levels and characteristics for gain optimization.
"""

import time
import logging
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class AudioMetrics:
    """Audio level metrics from analysis."""
    peak_db: float
    rms_db: float
    noise_floor_db: float
    snr_db: float
    clipping_count: int
    clipping_ratio: float
    duration: float
    timestamp: float


@dataclass
class CalibrationResult:
    """Result of calibration attempt."""
    success: bool
    final_db: float
    target_db: float
    error_db: float
    iterations: int
    mode: str  # 'hardware' or 'digital'
    message: str


class LevelAnalyzer:
    """
    Analyze audio levels for gain optimization.
    
    Features:
    - RMS and peak level calculation
    - Noise floor detection
    - Clipping detection
    - Iterative calibration with verification
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._measurement_buffer: deque = deque(maxlen=10)
        
    def calculate_rms(self, audio_buffer: np.ndarray) -> float:
        """
        Calculate RMS level in dB for float audio (-1.0 to 1.0).
        
        Args:
            audio_buffer: Audio samples as float32 array (-1.0 to 1.0)
            
        Returns:
            RMS level in dB. Returns -100.0 for silence.
        """
        if len(audio_buffer) == 0:
            return -100.0
            
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_buffer ** 2))
        
        # Explicit handling for silence
        if rms < 1e-10:
            return -100.0  # Effectively silent
        
        db = 20 * np.log10(rms)
        return db
    
    def calculate_peak(self, audio_buffer: np.ndarray) -> float:
        """
        Calculate peak level in dB.
        
        Args:
            audio_buffer: Audio samples as float32 array
            
        Returns:
            Peak level in dB
        """
        if len(audio_buffer) == 0:
            return -100.0
            
        peak = np.max(np.abs(audio_buffer))
        
        if peak < 1e-10:
            return -100.0
            
        return 20 * np.log10(peak)
    
    def detect_clipping(self, audio_buffer: np.ndarray, 
                       threshold: float = 0.99) -> Tuple[int, float]:
        """
        Detect clipping in audio buffer.
        
        Args:
            audio_buffer: Audio samples
            threshold: Clipping threshold (0.0-1.0)
            
        Returns:
            Tuple of (clipping_count, clipping_ratio)
        """
        if len(audio_buffer) == 0:
            return 0, 0.0
            
        # Count samples at/near clipping level
        clipped = np.sum(np.abs(audio_buffer) >= threshold)
        ratio = clipped / len(audio_buffer)
        
        return int(clipped), ratio
    
    def measure_noise_floor(self, audio_buffer: np.ndarray,
                           percentile: float = 10.0) -> float:
        """
        Estimate noise floor using percentile method.
        
        Uses lower percentile of energy to estimate noise floor
        without requiring pure silence.
        
        Args:
            audio_buffer: Audio samples
            percentile: Percentile to use (default 10% - lowest energy)
            
        Returns:
            Estimated noise floor in dB
        """
        if len(audio_buffer) == 0:
            return -100.0
            
        # Calculate frame-wise energy
        frame_size = int(self.sample_rate * 0.01)  # 10ms frames
        frames = []
        
        for i in range(0, len(audio_buffer) - frame_size, frame_size):
            frame = audio_buffer[i:i+frame_size]
            energy = np.mean(frame ** 2)
            frames.append(energy)
        
        if not frames:
            return -100.0
            
        # Use percentile to estimate noise floor
        noise_energy = np.percentile(frames, percentile)
        
        if noise_energy < 1e-10:
            return -100.0
            
        return 10 * np.log10(noise_energy)
    
    def analyze_buffer(self, audio_buffer: np.ndarray,
                      duration: Optional[float] = None) -> AudioMetrics:
        """
        Comprehensive analysis of audio buffer.
        
        Args:
            audio_buffer: Audio samples
            duration: Duration in seconds (for reference)
            
        Returns:
            AudioMetrics with all measurements
        """
        # Calculate metrics
        peak_db = self.calculate_peak(audio_buffer)
        rms_db = self.calculate_rms(audio_buffer)
        noise_floor_db = self.measure_noise_floor(audio_buffer)
        
        # Calculate SNR
        if rms_db > -90 and noise_floor_db > -90:
            snr_db = rms_db - noise_floor_db
        else:
            snr_db = 0.0
            
        # Detect clipping
        clipping_count, clipping_ratio = self.detect_clipping(audio_buffer)
        
        actual_duration = len(audio_buffer) / self.sample_rate if duration is None else duration
        
        return AudioMetrics(
            peak_db=peak_db,
            rms_db=rms_db,
            noise_floor_db=noise_floor_db,
            snr_db=snr_db,
            clipping_count=clipping_count,
            clipping_ratio=clipping_ratio,
            duration=actual_duration,
            timestamp=time.time()
        )
    
    def iterative_calibration(self, 
                             measure_func,
                             apply_gain_func,
                             device_id: int,
                             target_rms_db: float = -18.0,
                             max_iterations: int = 3,
                             tolerance_db: float = 2.0,
                             settle_time: float = 0.5) -> CalibrationResult:
        """
        Iterative calibration with verification.
        
        Process:
        1. Measure current level
        2. Calculate delta to target
        3. Apply gain adjustment
        4. Wait for hardware latency
        5. Re-measure
        6. If error > tolerance, repeat (max iterations)
        
        Args:
            measure_func: Function that returns audio buffer for measurement
            apply_gain_func: Function(device_id, gain_db) -> bool
            device_id: Audio device ID
            target_rms_db: Target RMS level
            max_iterations: Maximum calibration attempts
            tolerance_db: Acceptable error range
            settle_time: Seconds to wait after gain change
            
        Returns:
            CalibrationResult with final status
        """
        logger.info(f"Starting iterative calibration for device {device_id}")
        logger.info(f"Target: {target_rms_db} dB, Tolerance: ±{tolerance_db} dB")
        
        for iteration in range(1, max_iterations + 1):
            logger.info(f"Calibration iteration {iteration}/{max_iterations}")
            
            # Step 1: Measure
            try:
                audio_buffer = measure_func()
                if audio_buffer is None or len(audio_buffer) == 0:
                    return CalibrationResult(
                        success=False,
                        final_db=-100.0,
                        target_db=target_rms_db,
                        error_db=0.0,
                        iterations=iteration,
                        mode='unknown',
                        message="Failed to capture audio for measurement"
                    )
                
                metrics = self.analyze_buffer(audio_buffer)
                current_db = metrics.rms_db
                
            except Exception as e:
                logger.error(f"Measurement failed: {e}")
                return CalibrationResult(
                    success=False,
                    final_db=-100.0,
                    target_db=target_rms_db,
                    error_db=0.0,
                    iterations=iteration,
                    mode='unknown',
                    message=f"Measurement error: {e}"
                )
            
            # Step 2: Calculate delta
            error_db = target_rms_db - current_db
            
            logger.info(f"Current: {current_db:.1f} dB, Target: {target_rms_db:.1f} dB, "
                       f"Error: {error_db:.1f} dB")
            
            # Step 3: Check if within tolerance
            if abs(error_db) <= tolerance_db:
                logger.info(f"Calibration successful within tolerance")
                return CalibrationResult(
                    success=True,
                    final_db=current_db,
                    target_db=target_rms_db,
                    error_db=error_db,
                    iterations=iteration,
                    mode='calibrated',
                    message=f"Calibration successful after {iteration} iteration(s)"
                )
            
            # Step 4: Apply gain adjustment
            target_gain_db = target_rms_db - current_db  # Simplified - assumes linear
            
            try:
                success = apply_gain_func(device_id, target_gain_db)
                if not success:
                    return CalibrationResult(
                        success=False,
                        final_db=current_db,
                        target_db=target_rms_db,
                        error_db=error_db,
                        iterations=iteration,
                        mode='failed',
                        message="Failed to apply gain adjustment"
                    )
            except Exception as e:
                logger.error(f"Gain adjustment failed: {e}")
                return CalibrationResult(
                    success=False,
                    final_db=current_db,
                    target_db=target_rms_db,
                    error_db=error_db,
                    iterations=iteration,
                    mode='failed',
                    message=f"Gain adjustment error: {e}"
                )
            
            # Step 5: Wait for hardware latency
            if iteration < max_iterations:
                logger.debug(f"Waiting {settle_time}s for hardware to settle...")
                time.sleep(settle_time)
        
        # Max iterations reached
        logger.warning(f"Calibration failed to converge after {max_iterations} attempts")
        return CalibrationResult(
            success=False,
            final_db=current_db,
            target_db=target_rms_db,
            error_db=error_db,
            iterations=max_iterations,
            mode='failed',
            message=f"Failed to converge after {max_iterations} attempts"
        )
    
    def get_optimal_gain_adjustment(self, metrics: AudioMetrics,
                                   target_peak_db: float = -6.0,
                                   target_rms_db: float = -18.0) -> float:
        """
        Calculate optimal gain adjustment based on current metrics.
        
        Args:
            metrics: Current audio metrics
            target_peak_db: Target peak level
            target_rms_db: Target RMS level
            
        Returns:
            Suggested gain adjustment in dB
        """
        # Prioritize preventing clipping
        if metrics.peak_db > -3.0:
            # Too loud - reduce gain
            return target_peak_db - metrics.peak_db
        
        # Target RMS level
        if metrics.rms_db < target_rms_db - 5:
            # Too quiet - increase gain
            return target_rms_db - metrics.rms_db
        
        # Within acceptable range
        return 0.0
