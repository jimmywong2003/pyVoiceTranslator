"""faster-whisper ASR implementation with CTranslate2 backend."""

import os
import tempfile
from typing import Iterator, Optional, List
from pathlib import Path

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    WhisperModel = None

from .base import BaseASR, TranscriptionResult, Segment, Word


class FasterWhisperASR(BaseASR):
    """
    ASR implementation using faster-whisper (CTranslate2 backend).
    
    Cross-platform with excellent CPU/GPU support and quantization.
    
    Example:
        >>> asr = FasterWhisperASR(
        ...     model_size="medium",
        ...     device="cpu",
        ...     compute_type="int8"
        ... )
        >>> result = asr.transcribe("audio.wav", language="zh")
    """
    
    # Model size to approximate VRAM requirements (GB)
    VRAM_REQUIREMENTS = {
        "tiny": 1,
        "base": 1,
        "small": 2,
        "medium": 5,
        "large-v1": 10,
        "large-v2": 10,
        "large-v3": 10,
        "large-v3-turbo": 6,
        "distil-large-v3": 5,
    }
    
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[str] = None,
        language: Optional[str] = None,
        cpu_threads: int = 4,
        num_workers: int = 1,
    ):
        if not HAS_FASTER_WHISPER:
            raise ImportError(
                "faster-whisper not installed. "
                "Run: pip install faster-whisper"
            )
        
        super().__init__(f"faster-whisper-{model_size}", language)
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self._model = None
    
    def initialize(self) -> None:
        """Load the faster-whisper model."""
        if self._model is not None:
            return
        
        device = self.device
        
        # Auto-detect CUDA if available
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self._model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=self.compute_type,
            download_root=self.download_root,
            cpu_threads=self.cpu_threads,
            num_workers=self.num_workers,
        )
        self._is_initialized = True
    
    def _to_result(
        self,
        segments,
        info,
        processing_time: Optional[float] = None
    ) -> TranscriptionResult:
        """Convert faster-whisper output to TranscriptionResult."""
        segments_list = list(segments)
        
        # Convert to our Segment format
        our_segments = []
        all_words = []
        
        for seg in segments_list:
            words = None
            if seg.words:
                words = [
                    Word(
                        word=w.word,
                        start=w.start,
                        end=w.end,
                        probability=w.probability
                    )
                    for w in seg.words
                ]
                all_words.extend(words)
            
            our_segments.append(Segment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                words=words,
                confidence=getattr(seg, 'avg_logprob', 0.0),
            ))
        
        full_text = " ".join([s.text for s in our_segments])
        
        return TranscriptionResult(
            text=full_text,
            language=info.language,
            confidence=info.language_probability,
            segments=our_segments,
            words=all_words if all_words else None,
            duration=info.duration,
            processing_time=processing_time
        )
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0,
        length_penalty: float = 1.0,
        temperature: float = 0.0,
        compression_ratio_threshold: float = 2.4,
        log_prob_threshold: float = -1.0,
        no_speech_threshold: float = 0.6,
        condition_on_previous_text: bool = True,
        initial_prompt: Optional[str] = None,
        word_timestamps: bool = True,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio file using faster-whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'zh', 'en', 'ja', 'fr')
            beam_size: Beam size for beam search
            best_of: Number of candidates when sampling
            patience: Beam search patience factor
            length_penalty: Length penalty factor
            temperature: Sampling temperature
            compression_ratio_threshold: Threshold for compression ratio
            log_prob_threshold: Threshold for log probability
            no_speech_threshold: Threshold for no speech
            condition_on_previous_text: Condition on previous text
            initial_prompt: Initial prompt for transcription
            word_timestamps: Include word-level timestamps
            **kwargs: Additional options
            
        Returns:
            TranscriptionResult with segments and timestamps
        """
        if not self.is_initialized:
            self.initialize()
        
        import time
        start_time = time.time()
        
        segments, info = self._model.transcribe(
            audio_path,
            language=language or self.language,
            beam_size=beam_size,
            best_of=best_of,
            patience=patience,
            length_penalty=length_penalty,
            temperature=temperature,
            compression_ratio_threshold=compression_ratio_threshold,
            log_prob_threshold=log_prob_threshold,
            no_speech_threshold=no_speech_threshold,
            condition_on_previous_text=condition_on_previous_text,
            initial_prompt=initial_prompt,
            word_timestamps=word_timestamps,
            **kwargs
        )
        
        processing_time = time.time() - start_time
        
        return self._to_result(segments, info, processing_time)
    
    def transcribe_batch(
        self,
        audio_paths: List[str],
        language: Optional[str] = None,
        batch_size: int = 8,
        **kwargs
    ) -> List[TranscriptionResult]:
        """
        Transcribe multiple audio files with batching.
        
        Args:
            audio_paths: List of audio file paths
            language: Language code
            batch_size: Number of files to process in parallel
            **kwargs: Additional options passed to transcribe()
            
        Returns:
            List of TranscriptionResult objects
        """
        if not self.is_initialized:
            self.initialize()
        
        results = []
        for i in range(0, len(audio_paths), batch_size):
            batch = audio_paths[i:i + batch_size]
            
            # Process batch
            for path in batch:
                result = self.transcribe(path, language=language, **kwargs)
                results.append(result)
        
        return results
    
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
                
                # Keep overlap
                overlap_samples = int(sample_rate * 1.0)
                buffer = [audio_data[-overlap_samples:]]
    
    @property
    def supports_streaming(self) -> bool:
        """faster-whisper uses buffer-based pseudo-streaming."""
        return True
    
    @property
    def supports_word_timestamps(self) -> bool:
        """faster-whisper supports word timestamps."""
        return True
    
    def get_vram_requirement(self) -> int:
        """Get approximate VRAM requirement in GB."""
        return self.VRAM_REQUIREMENTS.get(self.model_size, 5)
    
    def get_info(self) -> dict:
        """Get ASR information."""
        info = super().get_info()
        info.update({
            "provider": "faster-whisper",
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "vram_required_gb": self.get_vram_requirement(),
        })
        return info
