"""Pivot translation for unsupported language pairs."""

import time
from typing import Optional, List

from .base import BaseTranslator, TranslationResult
from .marian import MarianTranslator


class PivotTranslator(BaseTranslator):
    """
    Pivot translator for language pairs without direct models.
    
    Translates through an intermediate language (typically English).
    For example: ja -> zh becomes ja -> en -> zh
    
    Example:
        >>> translator = PivotTranslator("ja", "zh", pivot_lang="en")
        >>> result = translator.translate("こんにちは")
    """
    
    # Supported language pairs (any pair that can pivot through English)
    SUPPORTED_PAIRS = [
        ("ja", "zh"), ("zh", "ja"),
        ("fr", "zh"), ("zh", "fr"),
        ("de", "zh"), ("zh", "de"),
        ("es", "zh"), ("zh", "es"),
        ("ru", "zh"), ("zh", "ru"),
        ("fr", "ja"), ("ja", "fr"),
        ("de", "ja"), ("ja", "de"),
        ("es", "ja"), ("ja", "es"),
        ("ru", "ja"), ("ja", "ru"),
        ("fr", "de"), ("de", "fr"),
        ("fr", "es"), ("es", "fr"),
        ("fr", "ru"), ("ru", "fr"),
        ("de", "es"), ("es", "de"),
        ("de", "ru"), ("ru", "de"),
        ("es", "ru"), ("ru", "es"),
    ]
    
    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        pivot_lang: str = "en",
        device: str = "auto",
    ):
        """
        Initialize pivot translator.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            pivot_lang: Intermediate language (default: "en")
            device: Device to run on ("auto", "cpu", "cuda", "mps")
        """
        super().__init__(f"{source_lang}-{pivot_lang}-{target_lang}", device)
        
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.pivot_lang = pivot_lang
        
        # Create two translators
        self._first_translator = MarianTranslator(
            source_lang=source_lang,
            target_lang=pivot_lang,
            device=device
        )
        self._second_translator = MarianTranslator(
            source_lang=pivot_lang,
            target_lang=target_lang,
            device=device
        )
    
    def supported_language_pairs(self) -> List[tuple]:
        """Return list of supported language pairs."""
        return self.SUPPORTED_PAIRS
    
    def _translate_batch_internal(
        self,
        texts: List[str],
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        **kwargs
    ) -> List[str]:
        """
        Translate a batch of texts through pivot language.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language
            target_lang: Target language
            **kwargs: Additional options
            
        Returns:
            List of translated texts
        """
        results = []
        for text in texts:
            result = self.translate(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
                **kwargs
            )
            results.append(result.translated_text)
        return results
    
    def initialize(self) -> None:
        """Load both translation models."""
        if self._is_initialized:
            return
        
        self._first_translator.initialize()
        self._second_translator.initialize()
        self._is_initialized = True
    
    def _post_process_translation(self, text: str) -> str:
        """
        Post-process translation to remove common artifacts.
        
        Removes:
        - Hallucinated sound effects: (Laughter), (Applause), etc.
        - Excessive punctuation
        - Common translation errors
        """
        import re
        
        # Remove sound effect annotations
        sound_effects = [
            r'\(Laughter\)',
            r'\(Applause\)',
            r'\(Music\)',
            r'\(Singing\)',
            r'\(Cheering\)',
            r'\(Booing\)',
            r'\(Cough\)',
            r'\(Sigh\)',
            r'\(Gasp\)',
            r'\(Pause\)',
        ]
        
        result = text
        for pattern in sound_effects:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result)
        
        # Clean up excessive punctuation
        result = re.sub(r'\.{3,}', '...', result)  # More than 3 dots -> 3 dots
        result = re.sub(r',{2,}', ',', result)     # Multiple commas -> one
        
        # Strip whitespace
        result = result.strip()
        
        # If result is empty after filtering, return original (with warning)
        if not result or result == '...':
            # Remove just the parentheses but keep the text
            result = re.sub(r'[\(\)]', '', text).strip()
        
        return result
    
    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        **kwargs
    ) -> TranslationResult:
        """
        Translate text through pivot language.
        
        Args:
            text: Text to translate
            source_lang: Source language (optional)
            target_lang: Target language (optional)
            **kwargs: Additional options
            
        Returns:
            TranslationResult with translated text
        """
        if not self.is_initialized:
            self.initialize()
        
        start_time = time.time()
        
        # First translation: source -> pivot
        first_result = self._first_translator.translate(text, **kwargs)
        pivot_text = first_result.translated_text
        
        # Second translation: pivot -> target
        second_result = self._second_translator.translate(pivot_text, **kwargs)
        final_text = second_result.translated_text
        
        # Post-process to remove artifacts
        original_text = final_text
        final_text = self._post_process_translation(final_text)
        
        # Log if we removed something
        if final_text != original_text:
            logger.debug(f"Post-processed: '{original_text}' -> '{final_text}'")
        
        total_time = time.time() - start_time
        
        return TranslationResult(
            source_text=text,
            translated_text=final_text,
            source_language=source_lang or self.source_lang,
            target_language=target_lang or self.target_lang,
            processing_time=total_time,
            model_name=self.model_name,
        )
    
    def get_supported_languages(self) -> List[str]:
        """Return supported languages (from both translators)."""
        first_langs = self._first_translator.get_supported_languages()
        second_langs = self._second_translator.get_supported_languages()
        return list(set(first_langs + second_langs))


def create_translator_with_pivot(
    source_lang: str,
    target_lang: str,
    device: str = "auto"
) -> BaseTranslator:
    """
    Create a translator, using pivot if direct model not available.
    
    Args:
        source_lang: Source language code
        target_lang: Target language code
        device: Device to run on
        
    Returns:
        BaseTranslator (direct or pivot)
    """
    # Check if direct model exists
    direct_pair = (source_lang, target_lang)
    if direct_pair in MarianTranslator.MODEL_NAMES:
        return MarianTranslator(
            source_lang=source_lang,
            target_lang=target_lang,
            device=device
        )
    
    # Try pivot through English
    pivot_lang = "en"
    first_pair = (source_lang, pivot_lang)
    second_pair = (pivot_lang, target_lang)
    
    if first_pair in MarianTranslator.MODEL_NAMES and \
       second_pair in MarianTranslator.MODEL_NAMES:
        return PivotTranslator(
            source_lang=source_lang,
            target_lang=target_lang,
            pivot_lang=pivot_lang,
            device=device
        )
    
    # No translation path available
    available = list(MarianTranslator.MODEL_NAMES.keys())
    raise ValueError(
        f"No translation path available for {source_lang} -> {target_lang}. "
        f"Direct pairs: {available}. "
        f"Pivot through {pivot_lang} also not available."
    )
