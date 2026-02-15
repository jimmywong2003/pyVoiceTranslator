"""MLX Whisper ASR implementation for Apple Silicon."""

import os
import tempfile
from typing import Iterator, Optional
from pathlib import Path

try:
    import mlx_whisper
    HAS_MLX = True
except ImportError:
    HAS_MLX = False
    mlx_whisper = None

from .base import BaseASR, TranscriptionResult, Segment, Word


class MLXWhisperASR(BaseASR):
    """
    ASR implementation using mlx-whisper for Apple Silicon.
    
    Uses Apple's MLX framework for optimized inference on M1/M2/M3/M4.
    
    Example:
        >>> asr = MLXWhisperASR(model_name="medium")
        >>> result = asr.transcribe("audio.wav", language="zh")
    """
    
    # Model mapping from size to HuggingFace path
    MODELS = {
        "tiny": "mlx-community/whisper-tiny",
        "base": "mlx-community/whisper-base",
        "small": "mlx-community/whisper-small",
        "medium": "mlx-community/whisper-medium",
        "large-v3": "mlx-community/whisper-large-v3",
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
        "distil-large-v3": "mlx-community/distil-whisper-large-v3",
    }
    
    def __init__(
        self,
        model_name: str = "medium",
        language: Optional[str] = None,
        quantize: bool = False,
    ):
        if not HAS_MLX:
            raise ImportError(
                "mlx-whisper not installed. "
                "Run: pip install mlx-whisper"
            )
        
        # Check if running on Apple Silicon
        import platform
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError(
                "MLX Whisper requires Apple Silicon (M1/M2/M3/M4)"
            )
        
        super().__init__(f"mlx-whisper-{model_name}", language)
        self.model_name = model_name
        self.quantize = quantize
        self._model_path = None
    
    def initialize(self) -> None:
        """Load the MLX Whisper model."""
        if self._model_path is not None:
            return
        
        model_path = self.MODELS.get(self.model_name)
        if model_path is None:
            raise ValueError(f"Unknown model: {self.model_name}")
        
        self._model_path = model_path
        self._is_initialized = True
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        temperature: float = 0.0,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio file using mlx-whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'zh', 'en', 'ja', 'fr')
            word_timestamps: Include word-level timestamps
            temperature: Sampling temperature
            **kwargs: Additional options
            
        Returns:
            TranscriptionResult with segments and timestamps
        """
        if not self.is_initialized:
            self.initialize()
        
        import time
        start_time = time.time()
        
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=self._model_path,
            language=language or self.language,
            word_timestamps=word_timestamps,
            temperature=temperature,
            **kwargs
        )
        
        processing_time = time.time() - start_time
        
        # Parse result
        segments = []
        words_list = []
        
        for seg_data in result.get("segments", []):
            words = None
            if "words" in seg_data:
                words = [
                    Word(
                        word=w["word"],
                        start=w["start"],
                        end=w["end"],
                        probability=w.get("probability")
                    )
                    for w in seg_data["words"]
                ]
                words_list.extend(words)
            
            segments.append(Segment(
                id=seg_data.get("id", 0),
                start=seg_data.get("start", 0.0),
                end=seg_data.get("end", 0.0),
                text=seg_data.get("text", "").strip(),
                words=words,
                confidence=seg_data.get("avg_logprob", 0.0),
            ))
        
        full_text = result.get("text", "").strip()
        
        return TranscriptionResult(
            text=full_text,
            language=result.get("language", "auto"),
            confidence=1.0,  # MLX doesn't expose confidence directly
            segments=segments,
            words=words_list if words_list else None,
            processing_time=processing_time
        )
    
    def transcribe_stream(
        self,
        audio_stream: Iterator[bytes],
        sample_rate: int = 16000,
        chunk_duration: float = 5.0,
        **kwargs
    ) -> Iterator[TranscriptionResult]:
        """
        Transcribe audio stream using buffer-based approach.
        
        Args:
            audio_stream: Iterator yielding audio chunks
            sample_rate: Audio sample rate
            chunk_duration: Process chunks of this duration
            **kwargs: Additional options
            
        Yields:
            TranscriptionResult for each processed chunk
        """
        import numpy as np
        import soundfile as sf
        
        buffer = []
        chunk_samples = int(sample_rate * chunk_duration)
        
        for audio_chunk in audio_stream:
            buffer.append(np.frombuffer(audio_chunk, dtype=np.int16))
            
            if sum(len(b) for b in buffer) >= chunk_samples:
                audio_data = np.concatenate(buffer)
                
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp:
                    sf.write(tmp.name, audio_data, sample_rate)
                    tmp_path = tmp.name
                
                try:
                    result = self.transcribe(tmp_path, **kwargs)
                    yield result
                finally:
                    os.unlink(tmp_path)
                
                overlap_samples = int(sample_rate * 1.0)
                buffer = [audio_data[-overlap_samples:]]
    
    @property
    def supports_streaming(self) -> bool:
        """MLX Whisper uses buffer-based pseudo-streaming."""
        return True
    
    @property
    def supports_word_timestamps(self) -> bool:
        """MLX Whisper supports word timestamps."""
        return True
    
    def get_info(self) -> dict:
        """Get ASR information."""
        info = super().get_info()
        info.update({
            "provider": "mlx-whisper",
            "model_name": self.model_name,
            "model_path": self._model_path,
            "quantize": self.quantize,
            "platform": "Apple Silicon",
        })
        return info
