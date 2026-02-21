"""
Audio Auto-Tune Module

Automatic microphone gain optimization for VoiceTranslate Pro.

Features:
- Hardware gain control (when available)
- Digital gain fallback (100% device coverage)
- Iterative calibration with verification
- Platform-specific implementations

Usage:
    >>> from audio.auto_tune import AudioAutoTuner, TuneResult
    >>> tuner = AudioAutoTuner()
    >>> result = tuner.quick_tune(device_id=2)
    >>> if result.success:
    ...     print(f"Tuned to {result.final_metrics.rms_db:.1f} dB")
"""

from .level_analyzer import LevelAnalyzer, AudioMetrics, CalibrationResult
from .digital_gain_processor import DigitalGainProcessor, DigitalGainSettings
from .gain_controller import (
    GainController, GainCapabilities, GainAdjustmentResult, GainMode
)
from .auto_tuner import AudioAutoTuner, TuneResult

__all__ = [
    # Main coordinator
    'AudioAutoTuner',
    'TuneResult',
    
    # Level analysis
    'LevelAnalyzer',
    'AudioMetrics',
    'CalibrationResult',
    
    # Digital gain
    'DigitalGainProcessor',
    'DigitalGainSettings',
    
    # Hardware control
    'GainController',
    'GainCapabilities',
    'GainAdjustmentResult',
    'GainMode',
]

__version__ = '1.0.0'
