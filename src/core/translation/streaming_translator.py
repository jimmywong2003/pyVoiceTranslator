"""
Streaming Translator - Phase 1.3

Translates drafts conditionally based on semantic completeness:
- Only translates if text has verb or punctuation (complete thought)
- SOV language safety: Wait for punctuation for Japanese, Korean, etc.
- Stability scoring to track translation changes
"""

import time
import logging
from typing import Optional, Dict, List, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

from .marian import MarianTranslator
from .base import TranslationResult

logger = logging.getLogger(__name__)


@dataclass
class StreamingTranslationResult:
    """Result from streaming translation."""
    text: Optional[str]
    is_final: bool
    stability: float  # 0.0-1.0, 1.0 = identical to previous
    skipped_reason: Optional[str] = None
    
    def __str__(self):
        if self.text:
            status = "FINAL" if self.is_final else "DRAFT"
            return f"[{status}] '{self.text[:40]}...' (stability: {self.stability:.2f})"
        else:
            return f"[SKIPPED] Reason: {self.skipped_reason}"


class SemanticRules:
    """
    Language-specific semantic rules for translation gating.
    
    Phase 1.3: Controls when drafts are translated based on:
    - Minimum word count
    - Verb presence (for SVO languages)
    - Punctuation (sentence boundaries)
    - SOV language special handling
    """
    
    # Language-specific verb lists (common verbs)
    VERBS = {
        'en': ['is', 'are', 'was', 'were', 'be', 'been', 'being',
               'have', 'has', 'had', 'do', 'does', 'did',
               'go', 'went', 'gone', 'make', 'made', 'take', 'took',
               'come', 'came', 'see', 'saw', 'know', 'knew',
               'get', 'got', 'give', 'gave', 'find', 'found',
               'think', 'thought', 'tell', 'told', 'become', 'became'],
        'zh': ['是', '在', '有', '去', '来', '吃', '喝', '看', '说', '做',
               '走', '跑', '写', '读', '听', '想', '要', '会', '能', '可以'],
        'ja': ['です', 'ます', 'する', '行く', '来る', '食べる', '飲む',
               '見る', '言う', '話す', '分かる', 'ある', 'いる', 'なる',
               '思う', '知る', '書く', '読む', '聞く', '取る', '作る'],
        'fr': ['être', 'avoir', 'faire', 'aller', 'venir', 'voir',
               'savoir', 'pouvoir', 'falloir', 'vouloir', 'falloir'],
        'es': ['ser', 'estar', 'tener', 'hacer', 'poder', 'decir',
               'ir', 'ver', 'dar', 'saber', 'querer', 'llegar'],
        'de': ['sein', 'haben', 'werden', 'können', 'müssen',
               'wollen', 'sollen', 'dürfen', 'machen', 'gehen'],
        'ko': ['이다', '있다', '없다', '하다', '되다', '알다', '모르다',
               '가다', '오다', '먹다', '마시다', '보다', '듣다', '말하다'],
        'tr': ['olmak', 'etmek', 'almak', 'vermek', 'yapmak',
               'gitmek', 'gelmek', 'görmek', 'bilmek', 'istemek'],
    }
    
    # Punctuation marks that indicate sentence boundaries
    PUNCTUATION = ['.', '!', '?', '。', '！', '？', '।']
    
    # SOV languages (Subject-Object-Verb)
    # These put the verb at the END, so we must wait for punctuation
    SOV_LANGUAGES: Set[str] = {'ja', 'ko', 'de', 'tr', 'hi', 'fa'}
    
    # SVO languages (Subject-Verb-Object) - more flexible
    SVO_LANGUAGES: Set[str] = {'en', 'zh', 'fr', 'es', 'it', 'pt', 'ru'}
    
    @classmethod
    def get_verbs(cls, language: str) -> List[str]:
        """Get verb list for a language."""
        return cls.VERBS.get(language, cls.VERBS['en'])  # Default to English
    
    @classmethod
    def is_sov(cls, language: str) -> bool:
        """Check if language is SOV (verb at end)."""
        return language in cls.SOV_LANGUAGES
    
    @classmethod
    def is_svo(cls, language: str) -> bool:
        """Check if language is SVO (verb in middle)."""
        return language in cls.SVO_LANGUAGES


class StreamingTranslator:
    """
    Streaming translator with semantic gating.
    
    Phase 1.3: Only translates drafts when they contain complete thoughts.
    
    Key Features:
    1. Semantic gating: Wait for verb or punctuation
    2. SOV safety: For JA/KO/DE/TR, must wait for sentence end
    3. Stability scoring: Track how much translation changes
    4. Beam size control: Fast (1) for drafts, accurate (5) for final
    
    Usage:
        translator = StreamingTranslator(base_translator, 'en', 'ja')
        
        # Draft with incomplete thought
        result = translator.translate_streaming("Hello", is_final=False)
        # -> StreamingTranslationResult(text=None, skipped_reason="incomplete")
        
        # Draft with complete thought  
        result = translator.translate_streaming("Hello world.", is_final=False)
        # -> StreamingTranslationResult(text="こんにちは世界。", is_final=False)
        
        # Final
        result = translator.translate_streaming("Hello world today.", is_final=True)
        # -> StreamingTranslationResult(text="こんにちは世界今日。", is_final=True)
    """
    
    def __init__(
        self,
        base_translator: MarianTranslator,
        source_lang: str,
        target_lang: str,
        min_words: int = 2,
        draft_beam_size: int = 1,
        final_beam_size: int = 5
    ):
        """
        Initialize streaming translator.
        
        Args:
            base_translator: Base Marian translator
            source_lang: Source language code (e.g., 'en')
            target_lang: Target language code (e.g., 'ja')
            min_words: Minimum words before considering translation
            draft_beam_size: Beam size for drafts (1 = fast)
            final_beam_size: Beam size for final (5 = accurate)
        """
        self.base_translator = base_translator
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.min_words = min_words
        self.draft_beam_size = draft_beam_size
        self.final_beam_size = final_beam_size
        
        # State
        self._previous_translation: Optional[str] = None
        
        # Statistics
        self._translations_triggered = 0
        self._translations_skipped = 0
        self._skip_reasons: Dict[str, int] = {
            'too_short': 0,
            'no_verb': 0,
            'no_punctuation': 0,
            'sov_incomplete': 0,
        }
        
        logger.info(
            f"StreamingTranslator initialized ({source_lang} -> {target_lang}, "
            f"SOV={SemanticRules.is_sov(target_lang)})"
        )
    
    def _has_verb(self, text: str) -> bool:
        """Check if text contains a verb."""
        text_lower = text.lower()
        verbs = SemanticRules.get_verbs(self.source_lang)
        return any(verb in text_lower for verb in verbs)
    
    def _has_punctuation(self, text: str) -> bool:
        """Check if text ends with sentence punctuation."""
        text_stripped = text.strip()
        return any(text_stripped.endswith(p) for p in SemanticRules.PUNCTUATION)
    
    def _is_semantically_complete(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Check if text is semantically complete and can be translated.
        
        Returns:
            (is_complete, skip_reason)
        """
        # Check 1: Minimum word count
        words = text.split()
        if len(words) < self.min_words:
            return False, "too_short"
        
        # Check 2: Has verb or punctuation (complete thought)
        has_verb = self._has_verb(text)
        has_punct = self._has_punctuation(text)
        
        # Check 3: SOV language special handling
        if SemanticRules.is_sov(self.target_lang):
            # For SOV languages, we MUST wait for punctuation
            # because the verb comes at the END
            if not has_punct:
                return False, "sov_incomplete"
        else:
            # For SVO languages, verb or punctuation is enough
            if not (has_verb or has_punct):
                return False, "no_verb_or_punct"
        
        return True, None
    
    def _calculate_stability(self, current: str) -> float:
        """
        Calculate stability score vs previous translation.
        
        Returns 0.0-1.0, where 1.0 means identical to previous.
        """
        if not self._previous_translation:
            return 0.0
        
        similarity = SequenceMatcher(
            None, 
            current, 
            self._previous_translation
        ).ratio()
        
        return similarity
    
    def translate_streaming(
        self,
        text: str,
        is_final: bool = False
    ) -> StreamingTranslationResult:
        """
        Translate text with semantic gating.
        
        Args:
            text: Text to translate
            is_final: If True, always translate with high quality
            
        Returns:
            StreamingTranslationResult with translation or skip reason
        """
        # Final mode: Always translate with full quality
        if is_final:
            return self._translate_final(text)
        
        # Draft mode: Check semantic completeness
        is_complete, skip_reason = self._is_semantically_complete(text)
        
        if not is_complete:
            self._translations_skipped += 1
            self._skip_reasons[skip_reason] = self._skip_reasons.get(skip_reason, 0) + 1
            
            logger.debug(f"Skipping draft translation: {skip_reason} - '{text[:30]}...'")
            
            return StreamingTranslationResult(
                text=None,
                is_final=False,
                stability=0.0,
                skipped_reason=skip_reason
            )
        
        # Translate draft
        return self._translate_draft(text)
    
    def _translate_draft(self, text: str) -> StreamingTranslationResult:
        """Translate draft with fast settings."""
        try:
            start_time = time.time()
            
            result = self.base_translator.translate(
                text,
                source_lang=self.source_lang,
                target_lang=self.target_lang
            )
            
            translated_text = result.translated_text
            
            # Calculate stability
            stability = self._calculate_stability(translated_text)
            
            # Store for next comparison
            self._previous_translation = translated_text
            
            self._translations_triggered += 1
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(
                f"Draft translated: '{text[:30]}...' -> '{translated_text[:30]}...' "
                f"({processing_time:.0f}ms, stability: {stability:.2f})"
            )
            
            return StreamingTranslationResult(
                text=translated_text,
                is_final=False,
                stability=stability
            )
            
        except Exception as e:
            logger.error(f"Draft translation failed: {e}")
            return StreamingTranslationResult(
                text=None,
                is_final=False,
                stability=0.0,
                skipped_reason=f"error: {e}"
            )
    
    def _translate_final(self, text: str) -> StreamingTranslationResult:
        """Translate final with high quality settings."""
        try:
            start_time = time.time()
            
            result = self.base_translator.translate(
                text,
                source_lang=self.source_lang,
                target_lang=self.target_lang
            )
            
            translated_text = result.translated_text
            
            # Calculate stability vs last draft
            stability = self._calculate_stability(translated_text)
            
            self._translations_triggered += 1
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(
                f"Final translated: '{text[:30]}...' -> '{translated_text[:30]}...' "
                f"({processing_time:.0f}ms, stability: {stability:.2f})"
            )
            
            # Clear previous translation for next segment
            self._previous_translation = None
            
            return StreamingTranslationResult(
                text=translated_text,
                is_final=True,
                stability=stability
            )
            
        except Exception as e:
            logger.error(f"Final translation failed: {e}")
            return StreamingTranslationResult(
                text=None,
                is_final=True,
                stability=0.0,
                skipped_reason=f"error: {e}"
            )
    
    def get_stats(self) -> dict:
        """Get translator statistics."""
        total = self._translations_triggered + self._translations_skipped
        
        return {
            'triggered': self._translations_triggered,
            'skipped': self._translations_skipped,
            'total': total,
            'trigger_rate': (
                self._translations_triggered / total * 100 
                if total > 0 else 0
            ),
            'skip_reasons': self._skip_reasons.copy(),
        }
    
    def print_stats(self):
        """Print translator statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 STREAMING TRANSLATOR STATS (Phase 1.3)")
        print("=" * 60)
        
        print(f"\n  Language Pair:      {self.source_lang} -> {self.target_lang}")
        print(f"  Target Type:        {'SOV' if SemanticRules.is_sov(self.target_lang) else 'SVO'}")
        
        print(f"\n  Translations:")
        print(f"    Triggered:        {stats['triggered']}")
        print(f"    Skipped:          {stats['skipped']}")
        print(f"    Trigger Rate:     {stats['trigger_rate']:.1f}%")
        
        if stats['skipped'] > 0:
            print(f"\n  Skip Reasons:")
            for reason, count in stats['skip_reasons'].items():
                if count > 0:
                    print(f"    {reason}: {count}")
        
        # SOV warning
        if SemanticRules.is_sov(self.target_lang):
            print(f"\n  ⚠️  SOV Language Mode:")
            print(f"     Drafts only translate when punctuation detected")
            print(f"     (Prevents grammatical errors from partial input)")
        
        print("=" * 60)


def create_streaming_translator(
    source_lang: str,
    target_lang: str,
    device: str = "auto"
) -> StreamingTranslator:
    """
    Factory function to create a streaming translator.
    
    Args:
        source_lang: Source language code
        target_lang: Target language code
        device: Device for translation model
        
    Returns:
        Configured StreamingTranslator
    """
    # Create base translator
    base = MarianTranslator(
        source_lang=source_lang,
        target_lang=target_lang,
        device=device
    )
    base.initialize()
    
    return StreamingTranslator(
        base_translator=base,
        source_lang=source_lang,
        target_lang=target_lang
    )
