"""
Audio capture module

Provides cross-platform audio capture for:
- Microphone input
- System audio (loopback)
"""

from .manager import AudioManager
from .base import BaseAudioCapture

__all__ = ["AudioManager", "BaseAudioCapture"]
