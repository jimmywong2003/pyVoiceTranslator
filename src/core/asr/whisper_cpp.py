"""whisper.cpp ASR implementation for Apple Silicon optimization."""

import subprocess
import json
import os
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Iterator, Optional, List

from .base import BaseASR, TranscriptionResult, Segment, Word


class WhisperCppASR(BaseASR):
    """
    ASR implementation using whisper.cpp.
    
    Optimized for Apple Silicon with Metal GPU acceleration.
    Requires whisper.cpp binary to be compiled and available.
    
    Example:
        >>> asr = WhisperCppASR(
        ...     model_path="models/ggml-medium.bin",
        ...     executable_path="./whisper.cpp/main",
        ...     use_metal=True
        ... )
        >>> result = asr.transcribe("audio.wav", language="zh")
    """
    
    def __init__(
        self,
        model_path: str,
        executable_path: str = "./whisper.cpp/main",
        threads: int = 4,
        use_metal: bool = True,
        language: Optional[str] = None,
        translate: bool = False,
    ):
        super().__init__("whisper.cpp", language)
        self.model_path = Path(model_path)
        self.executable = Path(executable_path)
        self.threads = threads
        self.use_metal = use_metal
        self.translate = translate
        
        # Validate paths
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not self.executable.exists():
            raise FileNotFoundError(f"Executable not found: {self.executable}")
    
    def initialize(self) -> None:
        """Verify model can be loaded (whisper.cpp loads on first use)."""
        # whisper.cpp loads model on first transcription
        self._is_initialized = True
    
    def _build_command(
        self,
        audio_path: str,
        language: Optional[str] = None,
        output_json: bool = True,
        word_timestamps: bool = True,
    ) -> List[str]:
        """Build whisper.cpp command with options."""
        cmd = [
            str(self.executable),
            "-m", str(self.model_path),
            "-f", audio_path,
            "-t", str(self.threads),
        ]
        
        # Language
        lang = language or self.language
        if lang:
            cmd.extend(["-l", lang])
        
        # Output format
        if output_json:
            cmd.append("--output-json")
        else:
            cmd.append("--output-txt")
        
        # Word timestamps
        if word_timestamps:
            cmd.append("--word-timestamps")
        
        # Metal acceleration (macOS only)
        if self.use_metal and os.uname().sysname == "Darwin":
            cmd.append("--use-metal")
        
        # Translation mode (en only)
        if self.translate:
            cmd.append("--translate")
        
        return cmd
    
    def _parse_output(self, output_json: dict) -> TranscriptionResult:
        """Parse whisper.cpp JSON output to TranscriptionResult."""
        # Extract segments
        segments = []
        words_list = []
        
        for seg_data in output_json.get("transcription", []):
            # Parse words if available
            words = None
            if "words" in seg_data:
                words = [
                    Word(
                        word=w["word"],
                        start=w.get("start", 0.0),
                        end=w.get("end", 0.0),
                        probability=w.get("probability")
                    )
                    for w in seg_data["words"]
                ]
                words_list.extend(words)
            
            segment = Segment(
                id=seg_data.get("id", 0),
                start=seg_data.get("offsets", {}).get("from", 0.0) / 1000.0,
                end=seg_data.get("offsets", {}).get("to", 0.0) / 1000.0,
                text=seg_data.get("text", "").strip(),
                words=words,
                confidence=seg_data.get("confidence", 0.0)
            )
            segments.append(segment)
        
        # Full text
        full_text = " ".join([s.text for s in segments])
        
        # Detected language
        language = output_json.get("result", {}).get("language", "auto")
        
        return TranscriptionResult(
            text=full_text,
            language=language,
            confidence=output_json.get("result", {}).get("confidence", 0.0),
            segments=segments,
            words=words_list if words_list else None
        )
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio file using whisper.cpp.
        
        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            language: Language code (e.g., 'zh', 'en', 'ja', 'fr')
            word_timestamps: Include word-level timestamps
            **kwargs: Ignored (for compatibility)
            
        Returns:
            TranscriptionResult with segments and timestamps
        """
        cmd = self._build_command(
            audio_path,
            language=language,
            output_json=True,
            word_timestamps=word_timestamps
        )
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"whisper.cpp failed: {result.stderr}")
        
        # Parse JSON output
        output = json.loads(result.stdout)
        return self._parse_output(output)
    
    def transcribe_stream(
        self,
        audio_stream: Iterator[bytes],
        sample_rate: int = 16000,
        chunk_duration: float = 5.0,
        **kwargs
    ) -> Iterator[TranscriptionResult]:
        """
        Transcribe audio stream (buffer-based approach).
        
        whisper.cpp doesn't support true streaming, so we buffer
        chunks and process when speech is detected.
        
        Args:
            audio_stream: Iterator yielding audio chunks (PCM16)
            sample_rate: Audio sample rate
            chunk_duration: Process chunks of this duration (seconds)
            **kwargs: Additional options
            
        Yields:
            TranscriptionResult for each processed chunk
        """
        buffer = []
        chunk_samples = int(sample_rate * chunk_duration)
        
        for audio_chunk in audio_stream:
            buffer.append(np.frombuffer(audio_chunk, dtype=np.int16))
            
            # Process when buffer is full
            if sum(len(b) for b in buffer) >= chunk_samples:
                # Concatenate and save to temp file
                audio_data = np.concatenate(buffer)
                
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp:
                    sf.write(tmp.name, audio_data, sample_rate)
                    tmp_path = tmp.name
                
                try:
                    result = self.transcribe(tmp_path)
                    yield result
                finally:
                    os.unlink(tmp_path)
                
                # Keep overlap for context
                overlap_samples = int(sample_rate * 1.0)  # 1 second overlap
                buffer = [audio_data[-overlap_samples:]]
    
    @property
    def supports_streaming(self) -> bool:
        """whisper.cpp uses buffer-based pseudo-streaming."""
        return True
    
    @property
    def supports_word_timestamps(self) -> bool:
        """whisper.cpp supports word timestamps with --word-timestamps."""
        return True
    
    def get_info(self) -> dict:
        """Get ASR information."""
        info = super().get_info()
        info.update({
            "provider": "whisper.cpp",
            "model_path": str(self.model_path),
            "threads": self.threads,
            "use_metal": self.use_metal,
        })
        return info
