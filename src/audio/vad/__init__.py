"""
Voice Activity Detection module

Provides VAD implementations:
- Silero VAD (recommended)
- WebRTC VAD (fallback)
- Improved Silero VAD (with enhancements)
- Adaptive Silero VAD (with noise estimation)
- Environment-Aware VAD (handles dynamic environments)
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

__all__ = [
    "SileroVADProcessor",
    "WebRTCVADProcessor", 
    "ImprovedSileroVADProcessor",
    "AdaptiveSileroVADProcessor",
    "AdaptiveVADConfig",
    "EnvironmentAwareVADProcessor",
    "EnvironmentAwareConfig",
    "EnvironmentState",
    "VADState",
    "AudioSegment",
]
