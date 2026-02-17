"""
Adaptive VAD with Calibration Phase

Measures background noise for a few seconds before starting detection,
then uses this measurement to set optimal thresholds.

Usage:
    from src.audio.vad.adaptive_vad_with_calibration import AdaptiveVADWithCalibration
    
    vad = AdaptiveVADWithCalibration(
        calibration_duration=3.0,  # 3 seconds calibration
        sample_rate=16000
    )
    
    # Calibration happens automatically on first chunks
    for chunk in audio_stream:
        segments = vad.process_chunk(chunk)
        # After calibration, uses measured noise floor
"""

import numpy as np
import torch
from collections import deque
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

from .silero_vad_improved import (
    ImprovedSileroVADProcessor, 
    AudioSegment, 
    VADState
)

logger = logging.getLogger(__name__)


class CalibrationState(Enum):
    """VAD calibration states."""
    NOT_STARTED = "not_started"
    CALIBRATING = "calibrating"
    CALIBRATED = "calibrated"
    DETECTING = "detecting"


@dataclass
class CalibrationConfig:
    """Configuration for calibration-based VAD."""
    # Calibration settings
    calibration_duration: float = 3.0  # Seconds to measure background
    min_calibration_chunks: int = 30   # Minimum chunks for calibration
    max_calibration_chunks: int = 150  # Maximum chunks (safety)
    
    # Core settings
    sample_rate: int = 16000
    base_threshold: float = 0.5
    
    # Threshold bounds (will be adjusted based on calibration)
    min_threshold: float = 0.25
    max_threshold: float = 0.75
    
    # Noise measurement
    noise_percentile: float = 10.0  # Use 10th percentile (conservative)
    noise_safety_margin_db: float = 6.0  # Add 6dB margin above measured noise
    
    # Speech detection thresholds (relative to noise floor)
    speech_threshold_db_above_noise: float = 6.0  # Speech must be 6dB above noise
    
    # Timing
    min_speech_duration_ms: int = 200
    min_silence_duration_ms: int = 250
    speech_pad_ms: int = 400
    max_segment_duration_ms: int = 5000  # 5 seconds max (reduced from 8s for lower latency)
    
    # Callbacks
    on_calibration_complete: Optional[Callable[[Dict], None]] = None
    on_calibration_progress: Optional[Callable[[float], None]] = None


@dataclass
class CalibrationResult:
    """Results from calibration phase."""
    noise_floor: float
    noise_floor_db: float
    noise_std: float
    measured_samples: int
    calibration_duration: float
    recommended_threshold: float
    recommended_min_speech_rms: float
    
    def to_dict(self) -> Dict:
        return {
            'noise_floor': f"{self.noise_floor:.6f}",
            'noise_floor_db': f"{self.noise_floor_db:.1f} dB",
            'noise_std': f"{self.noise_std:.6f}",
            'measured_samples': self.measured_samples,
            'calibration_duration': f"{self.calibration_duration:.2f}s",
            'recommended_threshold': f"{self.recommended_threshold:.2f}",
            'recommended_min_speech_rms': f"{self.recommended_min_speech_rms:.6f}",
        }


class AdaptiveVADWithCalibration(ImprovedSileroVADProcessor):
    """
    VAD with calibration phase for optimal noise floor estimation.
    
    How it works:
    1. CALIBRATION PHASE (first 3 seconds):
       - Measures background noise without detecting speech
       - Collects RMS values from all audio chunks
       - Calculates noise floor using percentile method
       
    2. DETECTION PHASE (after calibration):
       - Uses measured noise floor as baseline
       - Sets threshold based on actual noise characteristics
       - Adapts slowly to environment changes
       
    This is much more robust than starting with default values.
    
    Example:
        >>> vad = AdaptiveVADWithCalibration(calibration_duration=3.0)
        >>> 
        >>> # First 3 seconds: calibration (no speech detection)
        >>> for chunk in first_3_seconds:
        ...     segments = vad.process_chunk(chunk)  # Always returns []
        >>> 
        >>> # After 3 seconds: normal detection
        >>> for chunk in rest_of_audio:
        ...     segments = vad.process_chunk(chunk)  # Actual detection
    """
    
    def __init__(self, config: Optional[CalibrationConfig] = None):
        if config is None:
            config = CalibrationConfig()
        self.calibration_config = config
        
        # Initialize base VAD
        super().__init__(
            sample_rate=config.sample_rate,
            threshold=config.base_threshold,
            min_speech_duration_ms=config.min_speech_duration_ms,
            min_silence_duration_ms=config.min_silence_duration_ms,
            speech_pad_ms=config.speech_pad_ms,
            max_segment_duration_ms=config.max_segment_duration_ms,
        )
        
        # Calibration state
        self._calibration_state = CalibrationState.NOT_STARTED
        self._calibration_samples: List[float] = []
        self._calibration_start_time: Optional[float] = None
        self._calibration_result: Optional[CalibrationResult] = None
        
        # Post-calibration tracking
        self._noise_floor: float = 0.001  # Will be set after calibration
        self._adaptive_threshold: float = config.base_threshold
        self._chunks_since_calibration: int = 0
        
        # Statistics
        self._total_chunks: int = 0
        self._speech_chunks: int = 0
        
        logger.info(f"AdaptiveVADWithCalibration initialized ({config.calibration_duration}s calibration)")
    
    def process_chunk(self, audio_chunk: np.ndarray) -> List[AudioSegment]:
        """
        Process audio chunk with calibration.
        
        During calibration: measures noise, returns empty list
        After calibration: normal speech detection
        
        Args:
            audio_chunk: Audio samples
            
        Returns:
            List of speech segments (empty during calibration)
        """
        self._total_chunks += 1
        
        # Convert to float32 and normalize
        if audio_chunk.dtype != np.float32:
            audio_float = audio_chunk.astype(np.float32)
        else:
            audio_float = audio_chunk
        
        if np.abs(audio_float).max() > 1.0:
            audio_float = audio_float / 32768.0
        
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # State machine
        if self._calibration_state == CalibrationState.NOT_STARTED:
            self._start_calibration()
            self._calibration_samples.append(rms)
            return []
            
        elif self._calibration_state == CalibrationState.CALIBRATING:
            return self._handle_calibrating(rms, audio_float)
            
        elif self._calibration_state == CalibrationState.CALIBRATED:
            self._enter_detection_mode()
            return []
            
        else:  # DETECTING
            return self._handle_detection(rms, audio_float, audio_chunk)
    
    def _start_calibration(self):
        """Start calibration phase."""
        self._calibration_state = CalibrationState.CALIBRATING
        self._calibration_start_time = time.time()
        self._calibration_samples = []
        logger.info(f"🔧 CALIBRATION STARTED: Measuring background noise for {self.calibration_config.calibration_duration}s...")
        
        if self.calibration_config.on_calibration_progress:
            self.calibration_config.on_calibration_progress(0.0)
    
    def _handle_calibrating(self, rms: float, audio_float: np.ndarray) -> List[AudioSegment]:
        """Handle calibration phase - collect samples, no detection."""
        # Collect sample
        self._calibration_samples.append(rms)
        
        # Check if calibration is complete
        elapsed = time.time() - self._calibration_start_time
        min_chunks_met = len(self._calibration_samples) >= self.calibration_config.min_calibration_chunks
        time_met = elapsed >= self.calibration_config.calibration_duration
        max_chunks_met = len(self._calibration_samples) >= self.calibration_config.max_calibration_chunks
        
        # Progress callback
        if self.calibration_config.on_calibration_progress:
            progress = min(1.0, elapsed / self.calibration_config.calibration_duration)
            self.calibration_config.on_calibration_progress(progress)
        
        # Complete calibration if conditions met
        if (min_chunks_met and time_met) or max_chunks_met:
            self._complete_calibration()
        
        return []
    
    def _complete_calibration(self):
        """Complete calibration and calculate noise statistics."""
        if len(self._calibration_samples) < 10:
            logger.warning("⚠️ Calibration: Too few samples, using defaults")
            noise_floor = 0.001
        else:
            # Use percentile for robust noise floor estimation
            samples = np.array(self._calibration_samples)
            noise_floor = np.percentile(samples, self.calibration_config.noise_percentile)
            noise_std = np.std(samples)
        
        # Calculate noise floor in dB
        noise_floor_db = 20 * np.log10(noise_floor + 1e-10)
        
        # Calculate recommended threshold
        # Speech should be X dB above noise floor
        speech_threshold_db = noise_floor_db + self.calibration_config.speech_threshold_db_above_noise
        
        # Convert back to linear for threshold calculation
        # This is approximate - the Silero VAD uses probability, not direct level
        if noise_floor_db < -60:  # Very quiet
            recommended_threshold = 0.35
        elif noise_floor_db < -50:  # Quiet
            recommended_threshold = 0.40
        elif noise_floor_db < -40:  # Moderate
            recommended_threshold = 0.45
        elif noise_floor_db < -30:  # Noisy
            recommended_threshold = 0.50
        else:  # Very noisy
            recommended_threshold = 0.55
        
        # Calculate minimum speech RMS (6dB above noise)
        min_speech_rms = noise_floor * (10 ** (self.calibration_config.speech_threshold_db_above_noise / 20))
        
        # Create result
        elapsed = time.time() - self._calibration_start_time
        self._calibration_result = CalibrationResult(
            noise_floor=noise_floor,
            noise_floor_db=noise_floor_db,
            noise_std=np.std(self._calibration_samples) if len(self._calibration_samples) > 1 else 0,
            measured_samples=len(self._calibration_samples),
            calibration_duration=elapsed,
            recommended_threshold=recommended_threshold,
            recommended_min_speech_rms=min_speech_rms
        )
        
        # Set internal state
        self._noise_floor = noise_floor
        self._adaptive_threshold = recommended_threshold
        self._calibration_state = CalibrationState.CALIBRATED
        
        # Apply threshold to base VAD
        self.set_threshold(recommended_threshold)
        
        # Log results
        logger.info(f"✅ CALIBRATION COMPLETE: {self._calibration_result.to_dict()}")
        
        # Callback
        if self.calibration_config.on_calibration_complete:
            self.calibration_config.on_calibration_complete(self._calibration_result.to_dict())
    
    def _enter_detection_mode(self):
        """Enter normal detection mode after calibration."""
        self._calibration_state = CalibrationState.DETECTING
        self._chunks_since_calibration = 0
        logger.info(f"🎤 DETECTION MODE ACTIVE: threshold={self._adaptive_threshold:.2f}, "
                   f"noise_floor={self._noise_floor:.6f}")
    
    def _handle_detection(self, rms: float, audio_float: np.ndarray, 
                         audio_chunk: np.ndarray) -> List[AudioSegment]:
        """Handle normal speech detection after calibration."""
        self._chunks_since_calibration += 1
        
        # Optional: Skip very low energy (well below noise floor)
        # This is less aggressive than before - only skip obvious silence
        snr_db = 20 * np.log10((rms + 1e-10) / (self._noise_floor + 1e-10))
        if snr_db < -12:  # More than 12dB below noise floor = definite silence
            return []
        
        # Run base VAD
        segments = super().process_chunk(audio_chunk)
        
        if segments:
            self._speech_chunks += 1
        
        # Slow adaptation of noise floor (in case environment gradually changes)
        if self._chunks_since_calibration % 100 == 0:  # Every ~3 seconds
            self._adapt_noise_floor(rms, len(segments) > 0)
        
        return segments
    
    def _adapt_noise_floor(self, rms: float, is_speech: bool):
        """Slowly adapt noise floor based on recent audio."""
        if is_speech:
            return  # Don't update during speech
        
        # Very slow adaptation (0.1% per update)
        alpha = 0.001
        self._noise_floor = (1 - alpha) * self._noise_floor + alpha * rms
        
        # Log adaptation occasionally
        if self._chunks_since_calibration % 500 == 0:
            noise_db = 20 * np.log10(self._noise_floor + 1e-10)
            logger.debug(f"Noise floor adapted: {noise_db:.1f} dB")
    
    def get_calibration_result(self) -> Optional[CalibrationResult]:
        """Get calibration results (available after calibration)."""
        return self._calibration_result
    
    def is_calibrated(self) -> bool:
        """Check if calibration is complete."""
        return self._calibration_state == CalibrationState.DETECTING
    
    def is_calibrating(self) -> bool:
        """Check if currently calibrating."""
        return self._calibration_state == CalibrationState.CALIBRATING
    
    def get_calibration_progress(self) -> float:
        """Get calibration progress (0.0 to 1.0)."""
        if self._calibration_state == CalibrationState.NOT_STARTED:
            return 0.0
        elif self._calibration_state in (CalibrationState.CALIBRATED, CalibrationState.DETECTING):
            return 1.0
        else:  # CALIBRATING
            elapsed = time.time() - self._calibration_start_time
            return min(1.0, elapsed / self.calibration_config.calibration_duration)
    
    def get_stats(self) -> Dict:
        """Get VAD statistics."""
        return {
            'calibration_state': self._calibration_state.value,
            'calibration_progress': f"{self.get_calibration_progress():.1%}",
            'total_chunks': self._total_chunks,
            'speech_chunks': self._speech_chunks,
            'speech_ratio': f"{100*self._speech_chunks/max(1,self._total_chunks):.1f}%",
            'noise_floor_db': f"{20*np.log10(self._noise_floor + 1e-10):.1f}" if self._calibration_state == CalibrationState.DETECTING else "N/A",
            'current_threshold': f"{self._adaptive_threshold:.2f}" if self._calibration_state == CalibrationState.DETECTING else "N/A",
        }
    
    def reset_calibration(self):
        """Reset and restart calibration."""
        self._calibration_state = CalibrationState.NOT_STARTED
        self._calibration_samples = []
        self._calibration_result = None
        self._noise_floor = 0.001
        self._adaptive_threshold = self.calibration_config.base_threshold
        self._total_chunks = 0
        self._speech_chunks = 0
        self.set_threshold(self.calibration_config.base_threshold)
        logger.info("Calibration reset - will recalibrate on next chunk")
