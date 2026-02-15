"""Base translator interface and data structures."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class TranslationProvider(Enum):
    """Translation provider types."""
    NLLB = "nllb"
    MARIAN = "marian"
    DEEPL_API = "deepl_api"
    GOOGLE_API = "google_api"


@dataclass
class TranslationResult:
    """Translation result with metadata."""
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float = 0.0
    processing_time: Optional[float] = None
    alternatives: Optional[List[str]] = None
    
    @property
    def is_reliable(self) -> bool:
        """Check if translation confidence is above threshold."""
        return self.confidence >= 0.7


class BaseTranslator(ABC):
    """Abstract base class for NMT implementations."""
    
    # Language code mappings
    LANGUAGE_CODES = {
        "zh": "zh",  # Chinese
        "en": "en",  # English
        "ja": "ja",  # Japanese
        "fr": "fr",  # French
    }
    
    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        max_length: int = 256
    ):
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self._is_initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the translation model."""
        pass
    
    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        **kwargs
    ) -> TranslationResult:
        """
        Translate text from source to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'zh', 'en')
            target_lang: Target language code (e.g., 'en', 'fr')
            **kwargs: Additional implementation-specific options
            
        Returns:
            TranslationResult with translated text and metadata
        """
        pass
    
    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        batch_size: int = 8,
        **kwargs
    ) -> List[TranslationResult]:
        """
        Translate multiple texts in batches.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            batch_size: Number of texts to process in parallel
            **kwargs: Additional options
            
        Returns:
            List of TranslationResult objects
        """
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = self._translate_batch_internal(
                batch, source_lang, target_lang, **kwargs
            )
            results.extend(batch_results)
        return results
    
    @abstractmethod
    def _translate_batch_internal(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        **kwargs
    ) -> List[TranslationResult]:
        """Internal batch translation implementation."""
        pass
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text.
        
        Default implementation returns 'auto'.
        Override for language detection capability.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language code
        """
        return "auto"
    
    @property
    def is_initialized(self) -> bool:
        """Check if model is initialized."""
        return self._is_initialized
    
    @property
    @abstractmethod
    def supported_language_pairs(self) -> List[tuple]:
        """Return list of supported (source, target) language pairs."""
        pass
    
    def is_language_pair_supported(
        self,
        source_lang: str,
        target_lang: str
    ) -> bool:
        """Check if a language pair is supported."""
        return (source_lang, target_lang) in self.supported_language_pairs
    
    def get_info(self) -> Dict[str, Any]:
        """Get translator information."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "max_length": self.max_length,
            "initialized": self.is_initialized,
            "supported_pairs": self.supported_language_pairs,
        }
