"""
Voice Activity Detection module

Provides VAD implementations:
- Silero VAD (recommended)
- WebRTC VAD (fallback)
- Improved Silero VAD (with enhancements)
- Adaptive Silero VAD (with noise estimation)
"""

from .silero_vad import SileroVADProcessor, VADState, AudioSegment
from .webrtc_vad import WebRTCVADProcessor
from .silero_vad_improved import ImprovedSileroVADProcessor
from .silero_vad_adaptive import AdaptiveSileroVADProcessor, AdaptiveVADConfig

__all__ = [
    "SileroVADProcessor",
    "WebRTCVADProcessor", 
    "ImprovedSileroVADProcessor",
    "AdaptiveSileroVADProcessor",
    "AdaptiveVADConfig",
    "VADState",
    "AudioSegment",
]
