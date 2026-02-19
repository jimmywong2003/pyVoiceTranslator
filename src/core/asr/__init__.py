"""ASR (Automatic Speech Recognition) module."""

from .base import BaseASR, TranscriptionResult, Segment, Word
from .whisper_cpp import WhisperCppASR
from .faster_whisper import FasterWhisperASR
from .post_processor import (
    ASRPostProcessor,
    PostProcessedASR,
    PostProcessConfig,
    PostProcessResult,
    create_post_processed_asr,
)

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
    "ASRPostProcessor",
    "PostProcessedASR",
    "PostProcessConfig",
    "PostProcessResult",
    "create_post_processed_asr",
]

if HAS_MLX:
    __all__.append("MLXWhisperASR")
