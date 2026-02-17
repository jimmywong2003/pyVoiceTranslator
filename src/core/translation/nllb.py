"""NLLB (No Language Left Behind) translator implementation."""

import time
from typing import List, Optional, Dict, Any

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    torch = None
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None

from .base import BaseTranslator, TranslationResult


class NLLBTranslator(BaseTranslator):
    """
    NLLB-200 translator supporting 200 languages.
    
    Uses a single model for all language pairs.
    
    Example:
        >>> translator = NLLBTranslator(model_name="facebook/nllb-200-distilled-600M")
        >>> result = translator.translate("Hello", "en", "zh")
    """
    
    # NLLB language codes
    NLLB_CODES = {
        "zh": "zho_Hans",      # Chinese (Simplified)
        "zh-Hant": "zho_Hant", # Chinese (Traditional)
        "en": "eng_Latn",      # English
        "ja": "jpn_Jpan",      # Japanese
        "fr": "fra_Latn",      # French
        "de": "deu_Latn",      # German
        "es": "spa_Latn",      # Spanish
        "ko": "kor_Hang",      # Korean
        "ru": "rus_Cyrl",      # Russian
        "it": "ita_Latn",      # Italian
        "pt": "por_Latn",      # Portuguese
    }
    
    # Available model sizes
    MODELS = {
        "350M": "facebook/nllb-200-distilled-350M",
        "600M": "facebook/nllb-200-distilled-600M",
        "1.3B": "facebook/nllb-200-1.3B",
        "3.3B": "facebook/nllb-200-3.3B",
    }
    
    def __init__(
        self,
        model_name: str = "facebook/nllb-200-distilled-600M",
        device: str = "auto",
        max_length: int = 256,
        torch_dtype: Optional[Any] = None,
    ):
        if not HAS_TRANSFORMERS:
            raise ImportError(
                "transformers not installed. "
                "Run: pip install transformers torch"
            )
        
        super().__init__(model_name, device, max_length)
        
        # Resolve model name
        if model_name in self.MODELS:
            model_name = self.MODELS[model_name]
        
        self.model_name = model_name
        self.torch_dtype = torch_dtype
        self._tokenizer = None
        self._model = None
    
    def initialize(self) -> None:
        """Load the NLLB model and tokenizer."""
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
        
        # Determine dtype
        dtype = self.torch_dtype
        if dtype is None:
            if device == "cuda":
                dtype = torch.float16
            else:
                dtype = torch.float32
        
        # Load tokenizer and model
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # Load model - avoid device_map to prevent accelerate requirement
        self._model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype
        )
        
        # Move to device
        self._model = self._model.to(device)
        
        self._model.eval()
        self._is_initialized = True
    
    def _get_nllb_code(self, lang_code: str) -> str:
        """Convert standard language code to NLLB format."""
        return self.NLLB_CODES.get(lang_code, lang_code)
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        num_beams: int = 4,
        max_length: Optional[int] = None,
        **kwargs
    ) -> TranslationResult:
        """
        Translate text using NLLB.
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'zh', 'en')
            target_lang: Target language code (e.g., 'en', 'fr')
            num_beams: Number of beams for beam search
            max_length: Maximum output length
            **kwargs: Additional generation options
            
        Returns:
            TranslationResult with translated text
        """
        if not self.is_initialized:
            self.initialize()
        
        start_time = time.time()
        
        # Get NLLB language codes
        src_code = self._get_nllb_code(source_lang)
        tgt_code = self._get_nllb_code(target_lang)
        
        # Set source language
        self._tokenizer.src_lang = src_code
        
        # Tokenize input
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        
        # Move to device
        if self.device != "auto":
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # Get forced BOS token for target language
        forced_bos_token_id = self._tokenizer.lang_code_to_id[tgt_code]
        
        # Generate translation
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
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
            source_language=source_lang,
            target_language=target_lang,
            confidence=0.9,  # NLLB doesn't expose confidence directly
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
        
        # Get NLLB language codes
        src_code = self._get_nllb_code(source_lang)
        tgt_code = self._get_nllb_code(target_lang)
        
        # Set source language
        self._tokenizer.src_lang = src_code
        
        # Tokenize inputs
        inputs = self._tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        
        # Move to device
        if self.device != "auto":
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # Get forced BOS token
        forced_bos_token_id = self._tokenizer.lang_code_to_id[tgt_code]
        
        # Generate translations
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
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
        """NLLB supports all pairs of its 200 languages."""
        # Return key pairs for the required languages
        codes = ["zh", "en", "ja", "fr"]
        pairs = []
        for src in codes:
            for tgt in codes:
                if src != tgt:
                    pairs.append((src, tgt))
        return pairs
    
    def get_info(self) -> Dict[str, Any]:
        """Get translator information."""
        info = super().get_info()
        info.update({
            "provider": "NLLB",
            "model_size": self.model_name.split("-")[-1],
            "num_languages": 200,
        })
        return info
