"""Translation module for NMT (Neural Machine Translation)."""

from .base import BaseTranslator, TranslationResult
from .nllb import NLLBTranslator
from .marian import MarianTranslator
from .cache import TranslationCache, CachedTranslator

__all__ = [
    "BaseTranslator",
    "TranslationResult",
    "NLLBTranslator",
    "MarianTranslator",
    "TranslationCache",
    "CachedTranslator",
]
