"""Translation module for NMT (Neural Machine Translation)."""

from .base import BaseTranslator, TranslationResult
from .nllb import NLLBTranslator
from .marian import MarianTranslator

__all__ = [
    "BaseTranslator",
    "TranslationResult",
    "NLLBTranslator",
    "MarianTranslator",
]
