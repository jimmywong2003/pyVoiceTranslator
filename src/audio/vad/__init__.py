"""
Voice Activity Detection module

Provides VAD implementations:
- Silero VAD (recommended)
- WebRTC VAD (fallback)
- Improved Silero VAD (with enhancements)
- Adaptive Silero VAD (with noise estimation)
- Environment-Aware VAD (handles dynamic environments)
- Calibration-Based VAD (3s calibration for optimal threshold)
"""

from .silero_vad import SileroVADProcessor, VADState, AudioSegment
from .webrtc_vad import WebRTCVADProcessor
from .silero_vad_improved import ImprovedSileroVADProcessor
from .silero_vad_adaptive import AdaptiveSileroVADProcessor, AdaptiveVADConfig
from .environment_aware_vad import (
    EnvironmentAwareVADProcessor, 
    EnvironmentAwareConfig,
    EnvironmentState
)
from .adaptive_vad_with_calibration import (
    AdaptiveVADWithCalibration,
    CalibrationConfig,
    CalibrationResult,
    CalibrationState,
)

__all__ = [
    "SileroVADProcessor",
    "WebRTCVADProcessor", 
    "ImprovedSileroVADProcessor",
    "AdaptiveSileroVADProcessor",
    "AdaptiveVADConfig",
    "EnvironmentAwareVADProcessor",
    "EnvironmentAwareConfig",
    "EnvironmentState",
    "AdaptiveVADWithCalibration",
    "CalibrationConfig",
    "CalibrationResult",
    "CalibrationState",
    "VADState",
    "AudioSegment",
]
