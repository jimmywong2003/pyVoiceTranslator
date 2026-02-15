"""
Voice Translation System - ML Module

A hybrid edge-cloud speech recognition and translation system supporting
Chinese (zh), English (en), Japanese (ja), and French (fr).
"""

__version__ = "1.0.0"
__author__ = "ML Engineering Team"

from .asr import BaseASR, WhisperCppASR, FasterWhisperASR
from .translation import BaseTranslator, NLLBTranslator, MarianTranslator
from .pipeline import RealtimeTranslator, BatchVideoTranslator

__all__ = [
    "BaseASR",
    "WhisperCppASR", 
    "FasterWhisperASR",
    "BaseTranslator",
    "NLLBTranslator",
    "MarianTranslator",
    "RealtimeTranslator",
    "BatchVideoTranslator",
]
