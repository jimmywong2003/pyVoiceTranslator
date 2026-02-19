"""ASR Post-Processor for text normalization and quality filtering."""

import re
import logging
from typing import Optional, List, Iterator, Dict, Any, Callable
from dataclasses import dataclass, field

from .base import BaseASR, TranscriptionResult, Segment, Word

logger = logging.getLogger(__name__)


@dataclass
class PostProcessConfig:
    """Configuration for ASR post-processing."""
    
    # Hallucination detection
    enable_hallucination_filter: bool = True
    repetition_threshold: int = 4  # Pattern repeats 4+ times = hallucination
    repetition_ratio: float = 0.5  # 50% of text is repetition
    min_diversity_ratio: float = 0.3  # Less than 30% unique = hallucination
    
    # Confidence filtering
    min_confidence: float = 0.3  # Skip segments below this confidence
    min_segment_confidence: float = 0.5  # Skip individual segments below this
    
    # Text normalization
    enable_normalization: bool = True
    remove_filler_words: bool = True
    normalize_punctuation: bool = True
    
    # Language-specific options
    language: Optional[str] = None
    
    # Performance
    skip_translation_on_empty: bool = True  # Don't translate empty/invalid results


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


class ASRPostProcessor:
    """
    Post-processor for ASR transcriptions.
    
    Provides:
    1. Hallucination detection (repetitive patterns)
    2. Confidence-based filtering
    3. Text normalization (filler words, punctuation)
    4. Language-specific cleaning
    
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
    
    def __init__(self, config: Optional[PostProcessConfig] = None):
        self.config = config or PostProcessConfig()
    
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
        
        # 2. Confidence Filtering
        if confidence < self.config.min_confidence:
            quality_score *= (confidence / self.config.min_confidence)
            filters_applied.append(f"low_confidence:{confidence:.2f}")
        
        # 3. Text Normalization
        if self.config.enable_normalization:
            cleaned = self._normalize_text(cleaned)
            if cleaned != original:
                filters_applied.append("normalization")
        
        # 4. Remove ASR Artifacts
        cleaned = self._remove_artifacts(cleaned)
        if cleaned != original:
            filters_applied.append("artifacts")
        
        # 5. Remove Filler Words
        if self.config.remove_filler_words:
            cleaned = self._remove_filler_words(cleaned)
            if cleaned != original:
                filters_applied.append("filler_words")
        
        # 6. Final Cleanup
        cleaned = self._final_cleanup(cleaned)
        
        # Check if effectively empty after cleaning
        is_effectively_empty = not cleaned or cleaned.strip() == ""
        
        # Calculate final quality score
        if is_effectively_empty:
            quality_score = 0.0
        
        return PostProcessResult(
            original_text=original,
            cleaned_text=cleaned,
            is_hallucination=is_hallucination,
            is_empty=is_effectively_empty,
            confidence_too_low=confidence < self.config.min_confidence,
            should_skip_translation=is_effectively_empty or is_hallucination,
            quality_score=quality_score,
            filters_applied=filters_applied
        )
    
    def process_result(self, result: TranscriptionResult) -> TranscriptionResult:
        """
        Process a complete TranscriptionResult.
        
        Applies post-processing to the full text and individual segments.
        
        Args:
            result: Raw ASR transcription result
            
        Returns:
            Processed TranscriptionResult with cleaned text
        """
        # Process the main text
        process_result = self.process(result.text, result.confidence)
        
        # If hallucination, return empty result
        if process_result.is_hallucination or process_result.should_skip_translation:
            return TranscriptionResult(
                text="",
                language=result.language,
                confidence=0.0,
                segments=[],  # Clear segments
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
        
        # Pattern 1: Character repetition (4+ same chars)
        from collections import Counter
        char_counts = Counter(text)
        most_common_char, count = char_counts.most_common(1)[0]
        if count >= 4 and count / len(text) > 0.3:
            return {
                "is_hallucination": True,
                "pattern": f"char_repeat:{most_common_char}",
                "reason": f"Character '{most_common_char}' repeats {count} times ({count/len(text):.1%})"
            }
        
        # Pattern 2: Sequence repetition (3+ same sequence)
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
        
        # Pattern 3: Low diversity in long text
        if len(text) > 50:
            unique_chars = len(set(text))
            diversity = unique_chars / len(text)
            if diversity < self.config.min_diversity_ratio:
                return {
                    "is_hallucination": True,
                    "pattern": "low_diversity",
                    "reason": f"Low character diversity ({diversity:.1%})"
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
                "min_confidence": self._config.min_confidence,
                "remove_filler_words": self._config.remove_filler_words,
            }
        })
        return info


# Convenience function
def create_post_processed_asr(
    base_asr: BaseASR,
    language: Optional[str] = None,
    remove_filler_words: bool = True,
    enable_hallucination_filter: bool = True,
    min_confidence: float = 0.3
) -> PostProcessedASR:
    """
    Create a post-processed ASR wrapper.
    
    Args:
        base_asr: Base ASR implementation to wrap
        language: Language code for language-specific processing
        remove_filler_words: Whether to remove filler words
        enable_hallucination_filter: Whether to detect hallucinations
        min_confidence: Minimum confidence threshold
        
    Returns:
        PostProcessedASR wrapper
    """
    config = PostProcessConfig(
        language=language,
        remove_filler_words=remove_filler_words,
        enable_hallucination_filter=enable_hallucination_filter,
        min_confidence=min_confidence
    )
    return PostProcessedASR(base_asr, config)
