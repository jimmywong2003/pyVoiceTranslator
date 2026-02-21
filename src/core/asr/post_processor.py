"""ASR Post-Processor for text normalization and quality filtering."""

import re
import logging
from typing import Optional, List, Iterator, Dict, Any, Callable
from dataclasses import dataclass, field
from collections import deque

from .base import BaseASR, TranscriptionResult, Segment, Word

logger = logging.getLogger(__name__)


@dataclass
class PostProcessConfig:
    """Configuration for ASR post-processing."""
    
    # Hallucination detection
    enable_hallucination_filter: bool = True
    repetition_threshold: int = 6  # Pattern repeats 6+ times = hallucination
    repetition_ratio: float = 0.6  # 60% of text is repetition
    min_diversity_ratio: float = 0.12  # Minimum character diversity
    
    # Confidence filtering
    min_confidence: float = 0.3  # Skip segments below this confidence
    min_segment_confidence: float = 0.5  # Skip individual segments below this
    enable_confidence_smoothing: bool = True  # Smooth confidence across context
    
    # Context-aware filtering
    enable_context_filter: bool = True  # Use context to detect anomalies
    context_window_size: int = 5  # Number of recent segments to track
    max_similarity_drop: float = 0.5  # Max allowed similarity drop from context
    
    # Semantic coherence
    enable_coherence_check: bool = True  # Check if text makes semantic sense
    min_word_length: int = 2  # Minimum avg word length for valid text
    max_gibberish_ratio: float = 0.7  # Max ratio of non-dictionary words
    
    # Text normalization
    enable_normalization: bool = True
    remove_filler_words: bool = True
    normalize_punctuation: bool = True
    
    # Language-specific options
    language: Optional[str] = None
    
    # Performance
    skip_translation_on_empty: bool = True


@dataclass
class PostProcessResult:
    """Result of ASR post-processing with quality metrics."""
    original_text: str
    cleaned_text: str
    is_hallucination: bool = False
    is_empty: bool = False
    confidence_too_low: bool = False
    should_skip_translation: bool = False
    quality_score: float = 1.0  # 0.0-1.0
    filters_applied: List[str] = field(default_factory=list)
    context_score: float = 1.0  # How well it fits context


class ASRPostProcessor:
    """
    Post-processor for ASR transcriptions with context-aware filtering.
    
    Provides:
    1. Hallucination detection (repetitive patterns)
    2. Confidence-based filtering with smoothing
    3. Context-aware anomaly detection
    4. Semantic coherence checking
    5. Text normalization (filler words, punctuation)
    6. Language-specific cleaning
    
    Example:
        >>> config = PostProcessConfig(language="ja")
        >>> processor = ASRPostProcessor(config)
        >>> result = processor.process("あのあのえーとこんにちは")
        >>> print(result.cleaned_text)  # "こんにちは"
    """
    
    # Filler words by language
    FILLER_WORDS = {
        "ja": ["あの", "えーと", "えっと", "なんか", "まあ", "その", "えー", "あのー"],
        "en": ["um", "uh", "like", "you know", "so", "well", "actually", "basically"],
        "zh": ["那个", "就是", "然后", "嗯", "啊", "这个", "呃"],
        "fr": ["euh", "alors", "ben", "quoi", "tu sais", "voilà"],
    }
    
    # Common ASR artifacts
    ARTIFACTS = [
        r'\([\s]*Laughter[\s]*\)',
        r'\([\s]*Applause[\s]*\)',
        r'\([\s]*Music[\s]*\)',
        r'\([\s]*Singing[\s]*\)',
        r'\([\s]*Cheering[\s]*\)',
        r'\([\s]*Booing[\s]*\)',
        r'\([\s]*Cough[\s]*\)',
        r'\([\s]*Sigh[\s]*\)',
        r'\([\s]*Gasp[\s]*\)',
        r'\([\s]*Pause[\s]*\)',
    ]
    
    # Common words for coherence checking (top words in each language)
    COMMON_WORDS = {
        "en": set(["the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at"]),
        "ja": set(["の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ", "ある", "いる", "も", "する", "から", "な", "こと", "として"]),
        "zh": set(["的", "是", "在", "和", "了", "有", "我", "他", "就", "不", "会", "要", "没有", "我们", "这", "那", "吗", "什么", "吧", "呢"]),
    }
    
    def __init__(self, config: Optional[PostProcessConfig] = None):
        self.config = config or PostProcessConfig()
        # Context window for tracking recent transcriptions
        self._context_window: deque = deque(maxlen=self.config.context_window_size)
        self._recent_confidences: deque = deque(maxlen=self.config.context_window_size)
    
    def process(self, text: str, confidence: float = 1.0) -> PostProcessResult:
        """
        Process ASR text and return cleaned result with quality metrics.
        
        Args:
            text: Raw ASR transcription
            confidence: ASR confidence score (0.0-1.0)
            
        Returns:
            PostProcessResult with cleaned text and quality flags
        """
        if not text or not text.strip():
            return PostProcessResult(
                original_text=text or "",
                cleaned_text="",
                is_empty=True,
                should_skip_translation=self.config.skip_translation_on_empty
            )
        
        original = text.strip()
        cleaned = original
        filters_applied = []
        is_hallucination = False
        quality_score = 1.0
        context_score = 1.0
        
        # 1. Hallucination Detection
        if self.config.enable_hallucination_filter:
            hallucination_result = self._detect_hallucination(cleaned)
            if hallucination_result["is_hallucination"]:
                is_hallucination = True
                quality_score = 0.0
                filters_applied.append(f"hallucination:{hallucination_result['pattern']}")
                logger.warning(f"ASR hallucination detected: {hallucination_result['reason']}")
                return PostProcessResult(
                    original_text=original,
                    cleaned_text="",
                    is_hallucination=True,
                    should_skip_translation=True,
                    quality_score=0.0,
                    filters_applied=filters_applied
                )
        
        # 2. Confidence Filtering with Smoothing
        if self.config.enable_confidence_smoothing and self._recent_confidences:
            # Smooth confidence using recent context
            avg_confidence = sum(self._recent_confidences) / len(self._recent_confidences)
            smoothed_confidence = (confidence * 0.7) + (avg_confidence * 0.3)
            effective_confidence = smoothed_confidence
        else:
            effective_confidence = confidence
        
        if effective_confidence < self.config.min_confidence:
            quality_score *= (effective_confidence / self.config.min_confidence)
            filters_applied.append(f"low_confidence:{confidence:.2f}")
        
        # 3. Context-Aware Anomaly Detection
        if self.config.enable_context_filter and len(self._context_window) > 0:
            context_score = self._check_context_coherence(cleaned)
            if context_score < self.config.max_similarity_drop:
                # Significant deviation from context - possible error
                quality_score *= context_score
                filters_applied.append(f"context_anomaly:{context_score:.2f}")
                logger.debug(f"Context anomaly detected: score={context_score:.2f}, text='{cleaned[:30]}...'")
        
        # 4. Semantic Coherence Check
        if self.config.enable_coherence_check:
            coherence_score = self._check_semantic_coherence(cleaned)
            if coherence_score < 0.5:
                quality_score *= coherence_score
                filters_applied.append(f"low_coherence:{coherence_score:.2f}")
        
        # 5. Text Normalization
        if self.config.enable_normalization:
            cleaned = self._normalize_text(cleaned)
            if cleaned != original:
                filters_applied.append("normalization")
        
        # 6. Remove ASR Artifacts
        cleaned = self._remove_artifacts(cleaned)
        if cleaned != original:
            filters_applied.append("artifacts")
        
        # 7. Remove Filler Words
        if self.config.remove_filler_words:
            cleaned = self._remove_filler_words(cleaned)
            if cleaned != original:
                filters_applied.append("filler_words")
        
        # 8. Final Cleanup
        cleaned = self._final_cleanup(cleaned)
        
        # Check if effectively empty after cleaning
        is_effectively_empty = not cleaned or cleaned.strip() == ""
        
        # Calculate final quality score
        if is_effectively_empty:
            quality_score = 0.0
        
        # Update context window
        self._context_window.append(cleaned if not is_effectively_empty else original)
        self._recent_confidences.append(confidence)
        
        return PostProcessResult(
            original_text=original,
            cleaned_text=cleaned,
            is_hallucination=is_hallucination,
            is_empty=is_effectively_empty,
            confidence_too_low=effective_confidence < self.config.min_confidence,
            should_skip_translation=is_effectively_empty or is_hallucination,
            quality_score=quality_score,
            filters_applied=filters_applied,
            context_score=context_score
        )
    
    def process_result(self, result: TranscriptionResult) -> TranscriptionResult:
        """
        Process a complete TranscriptionResult.
        
        Applies post-processing to the full text and individual segments.
        """
        # Process the main text
        process_result = self.process(result.text, result.confidence)
        
        # If hallucination, return empty result
        if process_result.is_hallucination or process_result.should_skip_translation:
            return TranscriptionResult(
                text="",
                language=result.language,
                confidence=0.0,
                segments=[],
                words=result.words,
                duration=result.duration,
                processing_time=result.processing_time
            )
        
        # Process individual segments
        cleaned_segments = []
        for segment in result.segments:
            if segment.confidence >= self.config.min_segment_confidence:
                seg_process = self.process(segment.text, segment.confidence)
                if not seg_process.should_skip_translation:
                    cleaned_segments.append(Segment(
                        id=segment.id,
                        start=segment.start,
                        end=segment.end,
                        text=seg_process.cleaned_text,
                        words=segment.words,
                        confidence=segment.confidence
                    ))
        
        return TranscriptionResult(
            text=process_result.cleaned_text,
            language=result.language,
            confidence=result.confidence * process_result.quality_score,
            segments=cleaned_segments,
            words=result.words,
            duration=result.duration,
            processing_time=result.processing_time
        )
    
    def _detect_hallucination(self, text: str) -> Dict[str, Any]:
        """Detect if text is an ASR hallucination."""
        if len(text) < 5:
            return {"is_hallucination": False}
        
        from collections import Counter
        
        # Check if text is primarily CJK
        def is_cjk(char):
            return '\u4e00' <= char <= '\u9fff' or '\u3040' <= char <= '\u309f' or '\uac00' <= char <= '\ud7af'
        
        cjk_chars = sum(1 for c in text if is_cjk(c))
        total_chars = len([c for c in text if not c.isspace()])
        is_primarily_cjk = cjk_chars / total_chars > 0.5 if total_chars > 0 else False
        
        # Pattern 1: Character repetition (for non-CJK only)
        if not is_primarily_cjk:
            char_counts = Counter(c for c in text if c.isalpha())
            if char_counts:
                most_common_char, count = char_counts.most_common(1)[0]
                if count >= 4 and count / len(text) > 0.35:
                    return {
                        "is_hallucination": True,
                        "pattern": f"char_repeat:{most_common_char}",
                        "reason": f"Character '{most_common_char}' repeats {count} times ({count/len(text):.1%})"
                    }
        
        # Pattern 2: Sequence repetition
        for seq_len in range(2, min(21, len(text)//3 + 1)):
            for i in range(len(text) - seq_len * 3):
                pattern = text[i:i+seq_len]
                if len(pattern.strip()) == 0:
                    continue
                count = 0
                pos = i
                while pos < len(text) and text[pos:pos+seq_len] == pattern:
                    count += 1
                    pos += seq_len
                if count >= self.config.repetition_threshold:
                    return {
                        "is_hallucination": True,
                        "pattern": f"seq_repeat:{pattern}",
                        "reason": f"Sequence '{pattern}' repeats {count} times"
                    }
        
        # Pattern 3: Low word diversity in long text
        if len(text) > 100:
            words = text.lower().split()
            if len(words) > 10:
                unique_words = len(set(words))
                word_diversity = unique_words / len(words)
                if word_diversity < 0.3:
                    return {
                        "is_hallucination": True,
                        "pattern": "low_word_diversity",
                        "reason": f"Low word diversity ({word_diversity:.1%})"
                    }
        
        # Pattern 4: Excessive word repetition
        words = text.split()
        if len(words) >= 5:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            max_count = max(word_counts.values())
            if max_count / len(words) > self.config.repetition_ratio:
                most_common = max(word_counts.keys(), key=lambda w: word_counts[w])
                return {
                    "is_hallucination": True,
                    "pattern": f"word_repeat:{most_common}",
                    "reason": f"Word '{most_common}' appears {max_count}/{len(words)} times"
                }
        
        return {"is_hallucination": False}
    
    def _check_context_coherence(self, text: str) -> float:
        """
        Check how well the text fits with recent context.
        Returns similarity score 0.0-1.0.
        """
        if not self._context_window:
            return 1.0
        
        # Simple n-gram overlap similarity
        text_words = set(text.lower().split())
        if not text_words:
            return 1.0
        
        similarities = []
        for context_text in self._context_window:
            context_words = set(context_text.lower().split())
            if not context_words:
                continue
            
            # Jaccard similarity
            intersection = text_words & context_words
            union = text_words | context_words
            if union:
                similarity = len(intersection) / len(union)
                similarities.append(similarity)
        
        if not similarities:
            return 1.0
        
        # Return average similarity
        return sum(similarities) / len(similarities)
    
    def _check_semantic_coherence(self, text: str) -> float:
        """
        Check if the text is semantically coherent.
        Returns score 0.0-1.0.
        """
        words = text.split()
        if not words:
            return 1.0
        
        # Check 1: Average word length
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < self.config.min_word_length:
            return 0.3  # Too short words = likely gibberish
        
        # Check 2: Ratio of common words (language-specific)
        lang = self.config.language or "en"
        common_words = self.COMMON_WORDS.get(lang, self.COMMON_WORDS["en"])
        
        # Normalize for CJK (characters vs words)
        if lang in ("ja", "zh"):
            # For CJK, check character frequency
            chars = [c for c in text if not c.isspace()]
            if not chars:
                return 1.0
            common_chars = sum(1 for c in chars if c in common_words)
            common_ratio = common_chars / len(chars)
        else:
            common_word_count = sum(1 for w in words if w.lower() in common_words)
            common_ratio = common_word_count / len(words)
        
        # Score based on common word ratio
        if common_ratio < 0.1:
            return 0.4  # Very few common words
        elif common_ratio < 0.2:
            return 0.6
        else:
            return 1.0
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text (punctuation, whitespace)."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize punctuation
        if self.config.normalize_punctuation:
            # Replace multiple punctuation with single
            text = re.sub(r'!{2,}', '!', text)
            text = re.sub(r'\?{2,}', '?', text)
            text = re.sub(r',{2,}', ',', text)
            text = re.sub(r'\.{3,}', '...', text)
            text = re.sub(r'。{2,}', '。', text)
            text = re.sub(r'、{2,}', '、', text)
            text = re.sub(r'，{2,}', '，', text)
        
        return text.strip()
    
    def _remove_artifacts(self, text: str) -> str:
        """Remove ASR artifacts like (Laughter)."""
        result = text
        for pattern in self.ARTIFACTS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        # Remove generic parenthetical sound descriptions
        result = re.sub(r'\([\s]*[A-Z][a-z]+[\s]*\)', '', result)
        return result.strip()
    
    def _remove_filler_words(self, text: str) -> str:
        """Remove filler words based on language."""
        language = self.config.language or "en"
        fillers = self.FILLER_WORDS.get(language, [])
        
        result = text
        for filler in fillers:
            if language in ("ja", "zh"):
                # For CJK languages, match without word boundaries
                pattern = re.escape(filler)
                result = re.sub(pattern, '', result)
            else:
                # Match whole words only for other languages
                pattern = r'\b' + re.escape(filler) + r'\b'
                result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        # Clean up extra spaces (for non-CJK) or repeated punctuation
        if language in ("ja", "zh"):
            # Clean up repeated punctuation for CJK
            result = re.sub(r'。{2,}', '。', result)
            result = re.sub(r'、{2,}', '、', result)
        else:
            result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def _final_cleanup(self, text: str) -> str:
        """Final cleanup of the text."""
        # Strip leading/trailing punctuation
        text = text.strip(' .,!?;:。、，')
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def reset_context(self):
        """Reset the context window. Call when starting a new session."""
        self._context_window.clear()
        self._recent_confidences.clear()


class PostProcessedASR(BaseASR):
    """
    Decorator that adds post-processing to any ASR implementation.
    
    Example:
        >>> base_asr = FasterWhisperASR(model_size="tiny")
        >>> config = PostProcessConfig(language="ja", remove_filler_words=True)
        >>> asr = PostProcessedASR(base_asr, config)
        >>> result = asr.transcribe("audio.wav")  # Automatically post-processed
    """
    
    def __init__(
        self,
        base_asr: BaseASR,
        config: Optional[PostProcessConfig] = None
    ):
        self._base_asr = base_asr
        self._processor = ASRPostProcessor(config)
        self._config = config or PostProcessConfig()
        
        # Copy properties from base ASR
        super().__init__(
            model_name=f"postprocessed-{base_asr.model_name}",
            language=config.language if config else base_asr.language
        )
    
    def initialize(self) -> None:
        """Initialize the base ASR."""
        self._base_asr.initialize()
        self._is_initialized = True
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe and post-process the result.
        
        Returns cleaned TranscriptionResult with quality filtering applied.
        """
        # Get raw result from base ASR
        raw_result = self._base_asr.transcribe(audio_path, language, **kwargs)
        
        # Post-process
        processed_result = self._processor.process_result(raw_result)
        
        # Log filtering if applied
        if processed_result.text != raw_result.text:
            logger.debug(f"ASR post-processed: '{raw_result.text[:50]}...' -> '{processed_result.text[:50]}...'")
        
        if not processed_result.text and raw_result.text:
            logger.info(f"ASR result filtered (quality too low): '{raw_result.text[:50]}...'")
        
        return processed_result
    
    def transcribe_batch(
        self,
        audio_paths: List[str],
        language: Optional[str] = None,
        **kwargs
    ) -> List[TranscriptionResult]:
        """Transcribe batch with post-processing."""
        raw_results = self._base_asr.transcribe_batch(audio_paths, language, **kwargs)
        return [self._processor.process_result(r) for r in raw_results]
    
    def transcribe_stream(
        self,
        audio_stream: Iterator[bytes],
        sample_rate: int = 16000,
        **kwargs
    ) -> Iterator[TranscriptionResult]:
        """Stream transcribe with post-processing."""
        for raw_result in self._base_asr.transcribe_stream(audio_stream, sample_rate, **kwargs):
            yield self._processor.process_result(raw_result)
    
    @property
    def supports_streaming(self) -> bool:
        return self._base_asr.supports_streaming
    
    @property
    def supports_word_timestamps(self) -> bool:
        return self._base_asr.supports_word_timestamps
    
    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info.update({
            "base_asr": self._base_asr.get_info(),
            "post_process_config": {
                "enable_hallucination_filter": self._config.enable_hallucination_filter,
                "enable_context_filter": self._config.enable_context_filter,
                "enable_coherence_check": self._config.enable_coherence_check,
                "min_confidence": self._config.min_confidence,
                "remove_filler_words": self._config.remove_filler_words,
            }
        })
        return info
    
    def reset_context(self):
        """Reset the post-processor context window."""
        self._processor.reset_context()


# Convenience function
def create_post_processed_asr(
    base_asr: BaseASR,
    language: Optional[str] = None,
    remove_filler_words: bool = True,
    enable_hallucination_filter: bool = True,
    enable_context_filter: bool = True,
    enable_coherence_check: bool = True,
    min_confidence: float = 0.3
) -> PostProcessedASR:
    """
    Create a post-processed ASR wrapper with enhanced accuracy features.
    
    Args:
        base_asr: Base ASR implementation to wrap
        language: Language code for language-specific processing
        remove_filler_words: Whether to remove filler words
        enable_hallucination_filter: Whether to detect hallucinations
        enable_context_filter: Whether to use context-aware filtering
        enable_coherence_check: Whether to check semantic coherence
        min_confidence: Minimum confidence threshold
        
    Returns:
        PostProcessedASR wrapper with enhanced accuracy
    """
    config = PostProcessConfig(
        language=language,
        remove_filler_words=remove_filler_words,
        enable_hallucination_filter=enable_hallucination_filter,
        enable_context_filter=enable_context_filter,
        enable_coherence_check=enable_coherence_check,
        min_confidence=min_confidence
    )
    return PostProcessedASR(base_asr, config)
