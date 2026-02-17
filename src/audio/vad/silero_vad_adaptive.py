"""
Adaptive Silero VAD with Noise Estimation and Dynamic Thresholding

Phase 1 Implementation:
- Real-time noise floor estimation
- Adaptive threshold (0.3 - 0.8 range)
- Energy-based pre-filtering for CPU optimization
- Comprehensive metrics and debugging

Usage:
    from src.audio.vad.silero_vad_adaptive import AdaptiveSileroVADProcessor
    
    vad = AdaptiveSileroVADProcessor(
        sample_rate=16000,
        enable_adaptive_threshold=True,
        enable_noise_estimation=True
    )
    
    for audio_chunk in stream:
        segments = vad.process_chunk(audio_chunk)
        for segment in segments:
            process_segment(segment)
"""

import numpy as np
import torch
from collections import deque
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

# Import the improved VAD as base
from .silero_vad_improved import (
    ImprovedSileroVADProcessor, 
    AudioSegment, 
    VADState
)

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveVADConfig:
    """Configuration for adaptive VAD."""
    # Core settings
    sample_rate: int = 16000
    base_threshold: float = 0.5
    
    # Feature toggles
    enable_noise_estimation: bool = True
    enable_adaptive_threshold: bool = True
    enable_energy_prefilter: bool = True
    enable_metrics: bool = True
    
    # Noise estimation
    noise_history_size: int = 100
    noise_percentile: float = 10.0  # Use 10th percentile (conservative)
    noise_update_rate: float = 0.1   # EMA smoothing factor
    
    # Threshold adaptation
    min_threshold: float = 0.3
    max_threshold: float = 0.8
    threshold_smooth_factor: float = 0.2  # Smooth transitions
    
    # Noise level zones (RMS values)
    quiet_zone_max: float = 0.001    # Very quiet environment
    noisy_zone_min: float = 0.01     # Noisy environment
    
    # Energy pre-filter
    energy_prefilter_db: float = 6.0  # dB above noise floor (2x = ~6dB)
    min_speech_rms_ratio: float = 2.0  # Minimum RMS ratio for speech
    
    # Timing (inherited from improved VAD)
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 300
    speech_pad_ms: int = 500
    max_segment_duration_ms: int = 5000  # 5 seconds max (reduced from 8s for lower latency)
    pause_threshold_ms: int = 800


@dataclass
class VADMetrics:
    """Real-time VAD performance metrics."""
    timestamp: float = field(default_factory=time.time)
    
    # Noise statistics
    noise_floor: float = 0.0
    current_rms: float = 0.0
    snr_db: float = 0.0
    
    # Threshold
    current_threshold: float = 0.5
    base_threshold: float = 0.5
    
    # Processing
    energy_filtered_count: int = 0
    total_chunks: int = 0
    vadinference_count: int = 0
    
    # Detection
    speech_detected: bool = False
    speech_probability: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'noise_floor': self.noise_floor,
            'current_rms': self.current_rms,
            'snr_db': self.snr_db,
            'current_threshold': self.current_threshold,
            'energy_filter_efficiency': (
                self.energy_filtered_count / max(1, self.total_chunks)
            ),
            'speech_probability': self.speech_probability,
        }


class NoiseFloorEstimator:
    """
    Estimates background noise floor in real-time.
    
    Uses exponential moving average of silence periods to track
    changing noise conditions.
    """
    
    def __init__(self, config: AdaptiveVADConfig):
        self.config = config
        self.noise_history = deque(maxlen=config.noise_history_size)
        self.noise_floor = 0.001  # Initial conservative estimate
        self.last_update_time = time.time()
        
        logger.debug("NoiseFloorEstimator initialized")
    
    def update(self, audio_chunk: np.ndarray, speech_prob: float):
        """
        Update noise floor estimate.
        
        Only updates when we're confident there's no speech
        (speech_prob < 0.1), to avoid including speech in noise estimate.
        """
        # Calculate RMS
        audio_float = audio_chunk.astype(np.float32)
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # Update noise floor only during silence
        if speech_prob < 0.1:
            self.noise_history.append(rms)
            
            # Use percentile for robustness (ignore outliers)
            if len(self.noise_history) >= 10:
                # Use 10th percentile (conservative, excludes spikes)
                new_noise = np.percentile(
                    list(self.noise_history), 
                    self.config.noise_percentile
                )
                
                # Smooth with EMA
                alpha = self.config.noise_update_rate
                self.noise_floor = (1 - alpha) * self.noise_floor + alpha * new_noise
                
                # Ensure minimum (avoid zero)
                self.noise_floor = max(self.noise_floor, 1e-6)
    
    def get_noise_floor(self) -> float:
        """Get current noise floor estimate."""
        return self.noise_floor
    
    def get_noise_level_category(self) -> str:
        """Categorize current noise level."""
        if self.noise_floor < self.config.quiet_zone_max:
            return "quiet"
        elif self.noise_floor > self.config.noisy_zone_min:
            return "noisy"
        return "moderate"
    
    def reset(self):
        """Reset noise estimation."""
        self.noise_history.clear()
        self.noise_floor = 0.001
        logger.debug("Noise floor estimator reset")


class AdaptiveThreshold:
    """
    Dynamically adjusts VAD threshold based on noise floor.
    
    Strategy:
    - Quiet environment → Lower threshold (catch soft speech)
    - Noisy environment → Higher threshold (avoid false triggers)
    - Smooth transitions to avoid oscillation
    """
    
    def __init__(self, config: AdaptiveVADConfig):
        self.config = config
        self.current_threshold = config.base_threshold
        self.target_threshold = config.base_threshold
        
        logger.debug(f"AdaptiveThreshold initialized: base={config.base_threshold}")
    
    def update(self, noise_floor: float) -> float:
        """
        Calculate adaptive threshold based on noise floor.
        
        Returns:
            Updated threshold value
        """
        # Calculate target threshold based on noise zone
        if noise_floor < self.config.quiet_zone_max:
            # Very quiet - can use lower threshold
            # Linear interpolation: 0.0 noise → 0.35 threshold
            ratio = noise_floor / self.config.quiet_zone_max
            self.target_threshold = (
                self.config.min_threshold + 
                (self.config.base_threshold - self.config.min_threshold) * ratio
            )
            
        elif noise_floor > self.config.noisy_zone_min:
            # Noisy - need higher threshold
            # Linear interpolation: noisy_zone → 0.8 threshold
            excess = (noise_floor - self.config.noisy_zone_min) / self.config.noisy_zone_min
            excess = min(excess, 1.0)  # Cap at 1
            self.target_threshold = (
                self.config.base_threshold + 
                (self.config.max_threshold - self.config.base_threshold) * excess
            )
            
        else:
            # Moderate noise - use base threshold
            self.target_threshold = self.config.base_threshold
        
        # Smooth transition (avoid sudden changes)
        alpha = self.config.threshold_smooth_factor
        self.current_threshold = (
            (1 - alpha) * self.current_threshold + 
            alpha * self.target_threshold
        )
        
        # Clamp to valid range
        self.current_threshold = max(
            self.config.min_threshold,
            min(self.config.max_threshold, self.current_threshold)
        )
        
        return self.current_threshold
    
    def get_threshold(self) -> float:
        """Get current threshold."""
        return self.current_threshold
    
    def reset(self):
        """Reset to base threshold."""
        self.current_threshold = self.config.base_threshold
        self.target_threshold = self.config.base_threshold


class EnergyPreFilter:
    """
    Fast energy-based pre-filtering before VAD model.
    
    Rejects clear silence without expensive VAD model inference,
    saving CPU cycles.
    """
    
    def __init__(self, config: AdaptiveVADConfig):
        self.config = config
        self.filtered_count = 0
        self.total_count = 0
        
    def should_process_vad(self, audio_chunk: np.ndarray, 
                          noise_floor: float) -> Tuple[bool, float]:
        """
        Quick check if chunk needs full VAD processing.
        
        Returns:
            (should_process, rms_value)
        """
        self.total_count += 1
        
        # Calculate RMS quickly
        audio_float = audio_chunk.astype(np.float32)
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # Calculate minimum RMS for speech
        min_speech_rms = noise_floor * self.config.min_speech_rms_ratio
        
        # Quick reject if clearly below speech level
        if rms < min_speech_rms:
            self.filtered_count += 1
            return False, rms
        
        return True, rms
    
    def get_efficiency(self) -> float:
        """Get filtering efficiency ratio (0-1)."""
        if self.total_count == 0:
            return 0.0
        return self.filtered_count / self.total_count
    
    def reset(self):
        """Reset counters."""
        self.filtered_count = 0
        self.total_count = 0


class AdaptiveSileroVADProcessor(ImprovedSileroVADProcessor):
    """
    Adaptive VAD with noise estimation and dynamic thresholding.
    
    Extends ImprovedSileroVADProcessor with:
    - Real-time noise floor estimation
    - Adaptive threshold (0.3 - 0.8)
    - Energy pre-filtering for CPU savings
    - Comprehensive metrics and debugging
    """
    
    def __init__(self, config: Optional[AdaptiveVADConfig] = None, **kwargs):
        """
        Initialize adaptive VAD processor.
        
        Args:
            config: AdaptiveVADConfig instance (or created from kwargs)
            **kwargs: Override config parameters
        """
        # Create or update config
        if config is None:
            config = AdaptiveVADConfig()
        
        # Override with any kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.adaptive_config = config
        
        # Initialize base class with config values
        super().__init__(
            sample_rate=config.sample_rate,
            threshold=config.base_threshold,
            min_speech_duration_ms=config.min_speech_duration_ms,
            min_silence_duration_ms=config.min_silence_duration_ms,
            speech_pad_ms=config.speech_pad_ms,
            max_segment_duration_ms=config.max_segment_duration_ms,
            pause_threshold_ms=config.pause_threshold_ms,
        )
        
        # Initialize adaptive components
        self.noise_estimator = NoiseFloorEstimator(config)
        self.threshold_adapter = AdaptiveThreshold(config)
        self.energy_filter = EnergyPreFilter(config)
        
        # Metrics
        self.metrics = VADMetrics()
        self.metrics_history: deque = deque(maxlen=1000)
        
        # State tracking
        self._speech_start_time: Optional[float] = None
        self._last_log_time = time.time()
        
        logger.info(
            f"Adaptive VAD initialized: "
            f"noise_est={config.enable_noise_estimation}, "
            f"adaptive_thresh={config.enable_adaptive_threshold}, "
            f"energy_filter={config.enable_energy_prefilter}"
        )
    
    def process_chunk(self, audio_chunk: np.ndarray) -> List[AudioSegment]:
        """
        Process audio chunk with adaptive VAD.
        
        Args:
            audio_chunk: Audio data as numpy array
            
        Returns:
            List of detected speech segments (0, 1, or more)
        """
        segments = []
        self.metrics.total_chunks += 1
        
        # Step 1: Energy pre-filtering (optional, for CPU savings)
        if self.adaptive_config.enable_energy_prefilter:
            noise_floor = self.noise_estimator.get_noise_floor()
            should_process, rms = self.energy_filter.should_process_vad(
                audio_chunk, noise_floor
            )
            self.metrics.current_rms = rms
            
            if not should_process:
                # Fast path: clear silence, skip VAD model
                self.metrics.energy_filtered_count += 1
                speech_prob = 0.0
            else:
                # Run VAD model
                speech_prob = self._get_speech_probability(audio_chunk)
                self.metrics.vadinference_count += 1
        else:
            # Always run VAD model
            rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
            self.metrics.current_rms = rms
            speech_prob = self._get_speech_probability(audio_chunk)
            self.metrics.vadinference_count += 1
        
        self.metrics.speech_probability = speech_prob
        
        # Step 2: Update noise estimation
        if self.adaptive_config.enable_noise_estimation:
            self.noise_estimator.update(audio_chunk, speech_prob)
            self.metrics.noise_floor = self.noise_estimator.get_noise_floor()
            
            # Calculate SNR
            if self.metrics.noise_floor > 0:
                snr_linear = self.metrics.current_rms / self.metrics.noise_floor
                self.metrics.snr_db = 20 * np.log10(snr_linear) if snr_linear > 0 else -100
        
        # Step 3: Update adaptive threshold
        if self.adaptive_config.enable_adaptive_threshold:
            effective_threshold = self.threshold_adapter.update(
                self.metrics.noise_floor
            )
            self.metrics.current_threshold = effective_threshold
            self.metrics.base_threshold = self.adaptive_config.base_threshold
        else:
            effective_threshold = self.adaptive_config.base_threshold
            self.metrics.current_threshold = effective_threshold
        
        # Step 4: Use adaptive threshold for detection
        # Temporarily override base class threshold
        original_threshold = self.threshold
        self.threshold = effective_threshold
        
        try:
            # Call parent processing with adaptive threshold
            segments = super().process_chunk(audio_chunk)
            
            # Track speech detection
            if segments:
                self.metrics.speech_detected = True
            else:
                self.metrics.speech_detected = (speech_prob >= effective_threshold)
            
        finally:
            # Restore original threshold
            self.threshold = original_threshold
        
        # Step 5: Store metrics
        if self.adaptive_config.enable_metrics:
            self.metrics_history.append(self.metrics.to_dict())
            self._maybe_log_status()
        
        return segments
    
    def _get_speech_probability(self, audio_chunk: np.ndarray) -> float:
        """Get speech probability from Silero VAD model."""
        # Prepare audio
        min_samples = max(512, int(self.sample_rate * 0.03))
        if len(audio_chunk) < min_samples:
            audio_chunk = np.pad(
                audio_chunk,
                (0, min_samples - len(audio_chunk)),
                mode='constant'
            )
        
        # Convert to float32 tensor
        if audio_chunk.dtype == np.int16:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk.astype(np.float32)
        
        audio_tensor = torch.from_numpy(audio_float)
        
        # Run inference
        try:
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
        except Exception as e:
            logger.warning(f"VAD inference error: {e}")
            speech_prob = 0.0
        
        return speech_prob
    
    def _maybe_log_status(self):
        """Log status periodically (every 5 seconds)."""
        now = time.time()
        if now - self._last_log_time > 5.0:
            self._log_status()
            self._last_log_time = now
    
    def _log_status(self):
        """Log current VAD status."""
        noise_category = self.noise_estimator.get_noise_level_category()
        filter_efficiency = self.energy_filter.get_efficiency()
        
        logger.info(
            f"Adaptive VAD Status: "
            f"noise={self.metrics.noise_floor:.6f} ({noise_category}), "
            f"threshold={self.metrics.current_threshold:.3f}, "
            f"SNR={self.metrics.snr_db:.1f}dB, "
            f"filter_efficiency={filter_efficiency:.1%}"
        )
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        return {
            'current': self.metrics.to_dict(),
            'noise_category': self.noise_estimator.get_noise_level_category(),
            'filter_efficiency': self.energy_filter.get_efficiency(),
            'history': list(self.metrics_history),
        }
    
    def print_summary(self):
        """Print performance summary."""
        noise_cat = self.noise_estimator.get_noise_level_category()
        filter_eff = self.energy_filter.get_efficiency()
        
        print("\n" + "=" * 60)
        print("📊 Adaptive VAD Summary")
        print("=" * 60)
        print(f"Noise Level:      {self.metrics.noise_floor:.6f} ({noise_cat})")
        print(f"Current Threshold: {self.metrics.current_threshold:.3f}")
        print(f"Base Threshold:    {self.adaptive_config.base_threshold:.3f}")
        print(f"Filter Efficiency: {filter_eff:.1%} (CPU savings)")
        print(f"Total Chunks:      {self.metrics.total_chunks}")
        print(f"VAD Inferences:    {self.metrics.vadinference_count}")
        print("=" * 60)
    
    def reset(self):
        """Reset all adaptive state."""
        super().reset()
        self.noise_estimator.reset()
        self.threshold_adapter.reset()
        self.energy_filter.reset()
        self.metrics = VADMetrics()
        self.metrics_history.clear()
        logger.info("Adaptive VAD reset")


def create_adaptive_vad_for_environment(
    environment: str = "auto",
    sample_rate: int = 16000
) -> AdaptiveSileroVADProcessor:
    """
    Create pre-configured adaptive VAD for specific environment.
    
    Args:
        environment: "quiet", "office", "noisy", "auto"
        sample_rate: Audio sample rate
        
    Returns:
        Configured AdaptiveSileroVADProcessor
    """
    config = AdaptiveVADConfig(sample_rate=sample_rate)
    
    if environment == "quiet":
        # Home, studio - sensitive detection
        config.base_threshold = 0.4
        config.min_threshold = 0.25
        config.quiet_zone_max = 0.002
        
    elif environment == "office":
        # Office, classroom - balanced
        config.base_threshold = 0.5
        config.quiet_zone_max = 0.001
        config.noisy_zone_min = 0.008
        
    elif environment == "noisy":
        # Coffee shop, street - conservative
        config.base_threshold = 0.6
        config.min_threshold = 0.4
        config.noisy_zone_min = 0.005
        config.energy_prefilter_db = 9.0  # Higher threshold
        
    # "auto" uses defaults
    
    return AdaptiveSileroVADProcessor(config)


# Convenience exports
__all__ = [
    'AdaptiveSileroVADProcessor',
    'AdaptiveVADConfig',
    'NoiseFloorEstimator',
    'AdaptiveThreshold',
    'EnergyPreFilter',
    'VADMetrics',
    'create_adaptive_vad_for_environment',
]
