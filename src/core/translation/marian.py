"""Marian NMT translator implementation for specific language pairs."""

import time
from typing import List, Optional, Dict, Any

try:
    import torch
    from transformers import MarianTokenizer, MarianMTModel
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    torch = None
    MarianTokenizer = None
    MarianMTModel = None

from .base import BaseTranslator, TranslationResult


class MarianTranslator(BaseTranslator):
    """
    Marian NMT translator for specific language pairs.
    
    Uses separate models for each language pair.
    More efficient when language pairs are known in advance.
    
    Example:
        >>> translator = MarianTranslator(source_lang="en", target_lang="zh")
        >>> result = translator.translate("Hello", "en", "zh")
    """
    
    # HuggingFace model names for language pairs
    MODEL_NAMES = {
        ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
        ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
        ("ja", "en"): "Helsinki-NLP/opus-mt-ja-en",
        ("en", "ja"): "Helsinki-NLP/opus-mt-en-ja",
        ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
        ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
        ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
        ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
        ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
        ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
        ("ru", "en"): "Helsinki-NLP/opus-mt-ru-en",
        ("en", "ru"): "Helsinki-NLP/opus-mt-en-ru",
    }
    
    def __init__(
        self,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        model_name: Optional[str] = None,
        device: str = "auto",
        max_length: int = 512,
        torch_dtype: Optional[Any] = None,
    ):
        if not HAS_TRANSFORMERS:
            raise ImportError(
                "transformers not installed. "
                "Run: pip install transformers torch sacremoses"
            )
        
        # Determine model name from language pair or use provided name
        if model_name is None and source_lang and target_lang:
            model_name = self.MODEL_NAMES.get((source_lang, target_lang))
            if model_name is None:
                raise ValueError(
                    f"No Marian model available for {source_lang} -> {target_lang}. "
                    f"Available pairs: {list(self.MODEL_NAMES.keys())}"
                )
        
        if model_name is None:
            raise ValueError(
                "Either model_name or both source_lang and target_lang must be provided"
            )
        
        super().__init__(model_name, device, max_length)
        
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.torch_dtype = torch_dtype
        self._tokenizer = None
        self._model = None
    
    def initialize(self) -> None:
        """Load the Marian model and tokenizer."""
        if self._model is not None:
            return
        
        # Determine device
        device = self.device
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        
        self.device = device
        
        # Determine dtype
        dtype = self.torch_dtype
        if dtype is None:
            if device == "cuda":
                dtype = torch.float16
            else:
                dtype = torch.float32
        
        # Load tokenizer and model
        self._tokenizer = MarianTokenizer.from_pretrained(self.model_name)
        
        self._model = MarianMTModel.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
        )
        
        self._model = self._model.to(device)
        self._model.eval()
        self._is_initialized = True
    
    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        num_beams: int = 4,
        max_length: Optional[int] = None,
        **kwargs
    ) -> TranslationResult:
        """
        Translate text using Marian NMT.
        
        Args:
            text: Text to translate
            source_lang: Source language code (optional, uses init value)
            target_lang: Target language code (optional, uses init value)
            num_beams: Number of beams for beam search
            max_length: Maximum output length
            **kwargs: Additional generation options
            
        Returns:
            TranslationResult with translated text
        """
        if not self.is_initialized:
            self.initialize()
        
        # Use initialization values if not provided
        src = source_lang or self.source_lang
        tgt = target_lang or self.target_lang
        
        if src is None or tgt is None:
            raise ValueError("source_lang and target_lang must be provided")
        
        start_time = time.time()
        
        # Tokenize input
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        
        # Move to device
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # Generate translation
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                num_beams=num_beams,
                max_length=max_length or self.max_length,
                early_stopping=True,
                **kwargs
            )
        
        # Decode output
        translated = self._tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        processing_time = time.time() - start_time
        
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=src,
            target_language=tgt,
            confidence=0.9,
            processing_time=processing_time
        )
    
    def _translate_batch_internal(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        num_beams: int = 4,
        **kwargs
    ) -> List[TranslationResult]:
        """Internal batch translation implementation."""
        if not self.is_initialized:
            self.initialize()
        
        start_time = time.time()
        
        # Tokenize inputs
        inputs = self._tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        
        # Move to device
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # Generate translations
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                num_beams=num_beams,
                max_length=self.max_length,
                early_stopping=True,
                **kwargs
            )
        
        # Decode outputs
        translations = self._tokenizer.batch_decode(
            outputs,
            skip_special_tokens=True
        )
        
        processing_time = time.time() - start_time
        
        return [
            TranslationResult(
                source_text=text,
                translated_text=trans,
                source_language=source_lang,
                target_language=target_lang,
                confidence=0.9,
                processing_time=processing_time / len(texts)
            )
            for text, trans in zip(texts, translations)
        ]
    
    @property
    def supported_language_pairs(self) -> List[tuple]:
        """Return supported language pairs."""
        return list(self.MODEL_NAMES.keys())
    
    @classmethod
    def get_model_name(cls, source_lang: str, target_lang: str) -> Optional[str]:
        """Get model name for a language pair."""
        return cls.MODEL_NAMES.get((source_lang, target_lang))
    
    def get_info(self) -> Dict[str, Any]:
        """Get translator information."""
        info = super().get_info()
        info.update({
            "provider": "Marian NMT",
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "model_name": self.model_name,
        })
        return info
