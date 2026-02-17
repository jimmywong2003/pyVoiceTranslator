"""
Voice Activity Detection module

Provides VAD implementations:
- Silero VAD (recommended)
- WebRTC VAD (fallback)
"""

from .silero_vad import SileroVADProcessor
from .webrtc_vad import WebRTCVADProcessor

__all__ = ["SileroVADProcessor", "WebRTCVADProcessor"]
