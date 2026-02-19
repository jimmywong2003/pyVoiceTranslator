"""
Environment-Aware Adaptive VAD

Handles dynamic environment changes (e.g., moving from quiet office to noisy street).
Features:
- Rapid environment change detection
- Fast adaptation when environment shifts
- Environment state tracking with hysteresis
- Smooth operation within stable environments

Usage:
    from src.audio.vad.environment_aware_vad import EnvironmentAwareVADProcessor
    
    vad = EnvironmentAwareVADProcessor()
    
    for chunk in audio_stream:
        segments = vad.process_chunk(chunk)
        # VAD automatically adapts to environment changes
"""

import numpy as np
import torch
from collections import deque
from typing import Optional, List, Dict
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


class EnvironmentState(Enum):
    """Current acoustic environment state."""
    QUIET = "quiet"           # Low background noise
    MODERATE = "moderate"     # Medium background noise  
    NOISY = "noisy"           # High background noise
    VERY_NOISY = "very_noisy" # Very high background noise
    TRANSITIONING = "transitioning"  # Environment is changing


@dataclass
class EnvironmentAwareConfig:
    """Configuration for environment-aware VAD."""
    # Core settings
    sample_rate: int = 16000
    base_threshold: float = 0.5
    
    # Environment detection
    env_detection_window: int = 50  # chunks (~1.5s at 30ms/chunk)
    env_change_threshold_db: float = 10.0  # 10dB change = new environment
    env_hysteresis_db: float = 3.0  # Hysteresis to prevent oscillation
    
    # Adaptation speeds
    fast_adaptation_rate: float = 0.5  # When environment changes
    normal_adaptation_rate: float = 0.1  # Stable environment
    
    # Noise floor limits
    noise_floor_min: float = 1e-6
    noise_floor_max: float = 0.5
    
    # Threshold bounds
    min_threshold: float = 0.25
    max_threshold: float = 0.85
    
    # Energy pre-filter - DISABLED by default for better speech detection
    # Enable only if you're getting too many false positives in quiet environments
    enable_energy_prefilter: bool = False
    min_snr_db: float = 0.0  # Not used when prefilter is disabled
    
    # Timing (from improved VAD)
    min_speech_duration_ms: int = 200  # Slightly shorter for responsiveness
    min_silence_duration_ms: int = 250
    speech_pad_ms: int = 400
    max_segment_duration_ms: int = 8000  # 8 seconds max


@dataclass  
class EnvironmentMetrics:
    """Real-time environment and VAD metrics."""
    timestamp: float = field(default_factory=time.time)
    
    # Environment state
    environment: str = "unknown"
    noise_floor: float = 0.001
    noise_floor_db: float = -60.0
    
    # Signal
    current_rms: float = 0.0
    current_db: float = -60.0
    snr_db: float = 0.0
    
    # Threshold
    current_threshold: float = 0.5
    
    # Change detection
    recent_change_detected: bool = False
    adaptation_rate: float = 0.1
    
    # Efficiency
    total_chunks: int = 0
    filtered_chunks: int = 0
    
    # Speech detection
    speech_detected_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'environment': self.environment,
            'noise_floor_db': f"{self.noise_floor_db:.1f}",
            'signal_db': f"{self.current_db:.1f}",
            'snr_db': f"{self.snr_db:.1f}",
            'threshold': f"{self.current_threshold:.2f}",
            'recent_change': self.recent_change_detected,
            'filter_rate': f"{100*self.filtered_chunks/max(1,self.total_chunks):.1f}%",
            'speech_events': self.speech_detected_count,
        }


class RapidNoiseEstimator:
    """
    Rapidly adapting noise floor estimator.
    
    Detects environment changes quickly and adapts accordingly.
    """
    
    def __init__(self, config: EnvironmentAwareConfig):
        self.config = config
        
        # History for change detection
        self.recent_noise = deque(maxlen=config.env_detection_window)
        self.silence_buffer = deque(maxlen=20)  # Short-term silence RMS
        
        # Current state
        self.noise_floor = 0.001
        self.adaptation_rate = config.normal_adaptation_rate
        
        # Environment tracking
        self.environment_state = EnvironmentState.MODERATE
        self.last_env_change = 0
        
        logger.debug("RapidNoiseEstimator initialized")
    
    def update(self, audio_chunk: np.ndarray, is_speech: bool) -> float:
        """
        Update noise floor estimate with rapid change detection.
        
        Args:
            audio_chunk: Audio samples
            is_speech: Whether speech was detected in this chunk
            
        Returns:
            Current noise floor estimate
        """
        # Calculate RMS
        audio_float = audio_chunk.astype(np.float32)
        rms = np.sqrt(np.mean(audio_float ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)
        
        # Track recent noise levels
        self.recent_noise.append(rms_db)
        
        # Update silence buffer (for noise floor during silence)
        if not is_speech:
            self.silence_buffer.append(rms)
        
        # Detect environment change
        if len(self.recent_noise) >= 10:
            recent_mean = np.mean(list(self.recent_noise)[-10:])
            older_mean = np.mean(list(self.recent_noise)[:10]) if len(self.recent_noise) > 20 else recent_mean
            
            db_change = abs(recent_mean - older_mean)
            
            # Environment change detected
            if db_change > self.config.env_change_threshold_db:
                self.adaptation_rate = self.config.fast_adaptation_rate
                logger.info(f"Environment change detected: {db_change:.1f}dB shift, fast adaptation")
            else:
                # Gradually return to normal adaptation
                self.adaptation_rate = (
                    0.9 * self.adaptation_rate + 
                    0.1 * self.config.normal_adaptation_rate
                )
        
        # Update noise floor
        if self.silence_buffer:
            # Use silence periods to estimate noise
            current_noise_estimate = np.percentile(list(self.silence_buffer), 20)
        else:
            # No silence yet, use conservative estimate
            current_noise_estimate = rms * 0.5
        
        # Apply adaptation
        self.noise_floor = (
            (1 - self.adaptation_rate) * self.noise_floor + 
            self.adaptation_rate * current_noise_estimate
        )
        
        # Clamp to valid range
        self.noise_floor = max(
            self.config.noise_floor_min,
            min(self.config.noise_floor_max, self.noise_floor)
        )
        
        return self.noise_floor
    
    def get_environment_state(self) -> EnvironmentState:
        """Determine current environment state based on noise floor."""
        noise_db = 20 * np.log10(self.noise_floor + 1e-10)
        
        # Thresholds with hysteresis
        if noise_db < -50:
            return EnvironmentState.QUIET
        elif noise_db < -40:
            return EnvironmentState.MODERATE
        elif noise_db < -30:
            return EnvironmentState.NOISY
        else:
            return EnvironmentState.VERY_NOISY
    
    def reset(self):
        """Reset estimator (e.g., when manually triggered)."""
        self.recent_noise.clear()
        self.silence_buffer.clear()
        self.noise_floor = 0.001
        self.adaptation_rate = self.config.fast_adaptation_rate
        logger.info("Noise estimator reset")


class DynamicThreshold:
    """
    Dynamic threshold that responds to environment state.
    
    Key insight: In system audio capture with background noise,
    we need to keep threshold LOW enough to catch speech that may
    only be slightly above noise floor.
    """
    
    def __init__(self, config: EnvironmentAwareConfig):
        self.config = config
        self.current_threshold = config.base_threshold
        self._stable_environment = False
        self._stable_counter = 0
        
    def update(self, noise_floor: float, environment: EnvironmentState) -> float:
        """
        Calculate optimal threshold for current environment.
        
        Strategy:
        - Use environment-specific base threshold
        - CAP maximum threshold to ensure speech detection
        - Only raise threshold slightly in very noisy conditions
        - Lower threshold after environment stabilizes
        
        Args:
            noise_floor: Current noise floor estimate
            environment: Current environment state
            
        Returns:
            Updated threshold
        """
        # Environment-specific thresholds (CAPPED for speech detection)
        # These are MAXIMUM thresholds - we won't go higher
        env_max_thresholds = {
            EnvironmentState.QUIET: 0.45,      # Can afford higher threshold
            EnvironmentState.MODERATE: 0.50,   # Balanced
            EnvironmentState.NOISY: 0.55,      # Keep lower to catch speech
            EnvironmentState.VERY_NOISY: 0.60, # Even in noise, don't go too high
            EnvironmentState.TRANSITIONING: 0.50,  # Conservative during change
        }
        
        max_threshold = env_max_thresholds.get(environment, self.config.base_threshold)
        
        # Track environment stability
        if environment == EnvironmentState.TRANSITIONING:
            self._stable_counter = 0
            self._stable_environment = False
        else:
            self._stable_counter += 1
            if self._stable_counter > 100:  # ~3 seconds stable
                self._stable_environment = True
        
        # Calculate target threshold
        # Start from base and only adjust slightly
        target = self.config.base_threshold
        
        noise_db = 20 * np.log10(noise_floor + 1e-10)
        
        # Fine adjustments (very conservative)
        if noise_db < -55:  # Very quiet
            target = 0.40  # Slightly higher for quiet
        elif noise_db < -45:  # Quiet
            target = 0.45
        elif noise_db < -35:  # Moderate
            target = 0.50
        elif noise_db < -30:  # Noisy
            target = 0.52  # Keep low!
        else:  # Very noisy
            target = 0.55  # Still keep relatively low
        
        # Apply cap
        target = min(target, max_threshold)
        target = max(target, self.config.min_threshold)
        
        # Smooth transition (slower = more stable)
        alpha = 0.1 if self._stable_environment else 0.3
        self.current_threshold = (1 - alpha) * self.current_threshold + alpha * target
        
        # Final clamp
        self.current_threshold = max(
            self.config.min_threshold,
            min(max_threshold, self.current_threshold)
        )
        
        return self.current_threshold


class EnvironmentAwareVADProcessor(ImprovedSileroVADProcessor):
    """
    VAD processor that adapts to changing acoustic environments.
    
    Key features:
    - Rapid detection of environment changes
    - Fast adaptation when moving between environments
    - Stable operation within consistent environments
    - Comprehensive metrics for monitoring
    
    Example:
        >>> vad = EnvironmentAwareVADProcessor()
        >>> 
        >>> # In quiet office
        >>> segments = vad.process_chunk(quiet_chunk)
        >>> 
        >>> # Move to noisy street (automatically adapts)
        >>> segments = vad.process_chunk(noisy_chunk)
    """
    
    def __init__(self, config: Optional[EnvironmentAwareConfig] = None):
        if config is None:
            config = EnvironmentAwareConfig()
        self.adaptive_config = config
        
        # Initialize base VAD
        super().__init__(
            sample_rate=config.sample_rate,
            threshold=config.base_threshold,
            min_speech_duration_ms=config.min_speech_duration_ms,
            min_silence_duration_ms=config.min_silence_duration_ms,
            speech_pad_ms=config.speech_pad_ms,
            max_segment_duration_ms=config.max_segment_duration_ms,
        )
        
        # Environment-aware components
        self._noise_estimator = RapidNoiseEstimator(config)
        self._threshold_controller = DynamicThreshold(config)
        
        # Metrics
        self._metrics = EnvironmentMetrics()
        self._last_log_time = 0
        
        logger.info("EnvironmentAwareVADProcessor initialized")
    
    def process_chunk(self, audio_chunk: np.ndarray) -> List[AudioSegment]:
        """
        Process audio chunk with environment-aware adaptation.
        
        Args:
            audio_chunk: Audio samples (any format)
            
        Returns:
            List of detected speech segments
        """
        # Convert to float32
        if audio_chunk.dtype != np.float32:
            audio_float = audio_chunk.astype(np.float32)
        else:
            audio_float = audio_chunk
        
        # Normalize if needed
        if np.abs(audio_float).max() > 1.0:
            audio_float = audio_float / 32768.0
        
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # Environment-aware energy pre-filter
        noise_floor = self._noise_estimator.noise_floor
        if self._should_skip_by_energy(rms, noise_floor):
            # Skip expensive VAD - likely just noise
            self._update_metrics(rms, noise_floor, 0.0, is_filtered=True)
            return []
        
        # Run base VAD
        segments = super().process_chunk(audio_chunk)
        
        # Determine if speech was present
        is_speech = len(segments) > 0
        
        # Get VAD probability from internal state (if available)
        speech_prob = 1.0 if is_speech else 0.0
        
        # Update noise estimator
        noise_floor = self._noise_estimator.update(audio_float, is_speech)
        
        # Get environment state
        env_state = self._noise_estimator.get_environment_state()
        
        # Update threshold
        new_threshold = self._threshold_controller.update(noise_floor, env_state)
        self.set_threshold(new_threshold)
        
        # Update metrics
        self._update_metrics(rms, noise_floor, speech_prob, is_filtered=False)
        self._metrics.environment = env_state.value
        self._metrics.current_threshold = new_threshold
        self._metrics.adaptation_rate = self._noise_estimator.adaptation_rate
        
        # Track speech detection for better logging
        if is_speech:
            self._metrics.speech_detected_count = getattr(self._metrics, 'speech_detected_count', 0) + 1
        
        # Log periodically or when speech detected
        current_time = time.time()
        if current_time - self._last_log_time > 5.0:  # Every 5 seconds
            self._log_status()
            self._last_log_time = current_time
        elif is_speech and getattr(self, '_last_speech_log', 0) < current_time - 1.0:
            # Log when speech detected (but not too frequently)
            logger.info(f"🎤 Speech detected! Segments: {len(segments)}, "
                       f"Duration: {sum(s.duration for s in segments):.2f}s")
            self._last_speech_log = current_time
        
        return segments
    
    def _should_skip_by_energy(self, rms: float, noise_floor: float) -> bool:
        """
        Environment-aware energy pre-filter.
        
        In very noisy environments (like system audio with background noise),
        we need to be more permissive to catch speech that might only be
        slightly above the noise floor.
        
        Returns:
            True if chunk should be skipped (likely just noise)
        """
        if not self.adaptive_config.enable_energy_prefilter:
            return False
        
        # Calculate SNR
        snr_db = 20 * np.log10((rms + 1e-10) / (noise_floor + 1e-10))
        
        # Get current environment
        env = self._noise_estimator.get_environment_state()
        
        # Environment-specific SNR thresholds
        # More permissive in noisy environments
        snr_thresholds = {
            EnvironmentState.QUIET: 3.0,      # Need clear signal in quiet
            EnvironmentState.MODERATE: 1.5,   # Moderate tolerance
            EnvironmentState.NOISY: 0.5,      # Very permissive (speech close to noise)
            EnvironmentState.VERY_NOISY: 0.0, # Accept anything (speech buried in noise)
            EnvironmentState.TRANSITIONING: 1.0,
        }
        
        threshold = snr_thresholds.get(env, self.adaptive_config.min_snr_db)
        
        # Skip if SNR is below environment-specific threshold
        return snr_db < threshold
    
    def _update_metrics(self, rms: float, noise_floor: float, 
                       speech_prob: float, is_filtered: bool):
        """Update internal metrics."""
        self._metrics.total_chunks += 1
        if is_filtered:
            self._metrics.filtered_chunks += 1
        
        self._metrics.current_rms = rms
        self._metrics.noise_floor = noise_floor
        self._metrics.speech_probability = speech_prob
        
        # Convert to dB
        self._metrics.current_db = 20 * np.log10(rms + 1e-10)
        self._metrics.noise_floor_db = 20 * np.log10(noise_floor + 1e-10)
        self._metrics.snr_db = self._metrics.current_db - self._metrics.noise_floor_db
    
    def _log_status(self):
        """Log current status."""
        m = self._metrics
        speech_info = f"🎤 {m.speech_detected_count} speech events | " if m.speech_detected_count > 0 else ""
        logger.info(
            f"Environment: {m.environment.upper()} | "
            f"Noise: {m.noise_floor_db:.1f}dB | "
            f"Signal: {m.current_db:.1f}dB | "
            f"SNR: {m.snr_db:.1f}dB | "
            f"Threshold: {m.current_threshold:.2f} | "
            f"{speech_info}"
            f"Chunks: {m.total_chunks}"
        )
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        return self._metrics.to_dict()
    
    def reset_environment(self):
        """
        Manually reset environment detection.
        
        Call this when you know the environment has changed
        (e.g., user moved to a different room).
        """
        self._noise_estimator.reset()
        logger.info("Environment manually reset")
    
    def force_environment(self, env: str):
        """
        Force a specific environment state.
        
        Args:
            env: One of "quiet", "moderate", "noisy", "very_noisy"
        """
        env_map = {
            "quiet": EnvironmentState.QUIET,
            "moderate": EnvironmentState.MODERATE,
            "noisy": EnvironmentState.NOISY,
            "very_noisy": EnvironmentState.VERY_NOISY,
        }
        
        if env in env_map:
            # Set noise floor to match environment
            noise_targets = {
                "quiet": 0.0005,      # -66 dB
                "moderate": 0.005,    # -46 dB
                "noisy": 0.02,        # -34 dB
                "very_noisy": 0.1,    # -20 dB
            }
            
            self._noise_estimator.noise_floor = noise_targets[env]
            self._noise_estimator.adaptation_rate = self.adaptive_config.fast_adaptation_rate
            logger.info(f"Environment forced to: {env}")
