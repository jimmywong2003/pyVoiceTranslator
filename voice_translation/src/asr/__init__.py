"""ASR (Automatic Speech Recognition) module."""

from .base import BaseASR, TranscriptionResult, Segment, Word
from .whisper_cpp import WhisperCppASR
from .faster_whisper import FasterWhisperASR

try:
    from .mlx_whisper import MLXWhisperASR
    HAS_MLX = True
except ImportError:
    HAS_MLX = False
    MLXWhisperASR = None

__all__ = [
    "BaseASR",
    "TranscriptionResult",
    "Segment",
    "Word",
    "WhisperCppASR",
    "FasterWhisperASR",
]

if HAS_MLX:
    __all__.append("MLXWhisperASR")
