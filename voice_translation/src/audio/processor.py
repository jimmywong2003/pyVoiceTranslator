"""Audio preprocessing utilities."""

import numpy as np
from pathlib import Path
from typing import Union, Optional, Tuple

try:
    import librosa
    import soundfile as sf
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False
    librosa = None
    sf = None


class AudioProcessor:
    """
    Audio preprocessing for ASR input.
    
    Handles resampling, normalization, and format conversion.
    """
    
    # Target sample rate for Whisper models
    TARGET_SAMPLE_RATE = 16000
    
    def __init__(self, target_sample_rate: int = 16000):
        if not HAS_AUDIO:
            raise ImportError(
                "Audio processing requires librosa and soundfile. "
                "Run: pip install librosa soundfile"
            )
        
        self.target_sample_rate = target_sample_rate
    
    def load_audio(
        self,
        audio_path: Union[str, Path],
        offset: float = 0.0,
        duration: Optional[float] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio file.
        
        Args:
            audio_path: Path to audio file
            offset: Start time in seconds
            duration: Duration to load in seconds
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        audio, sr = librosa.load(
            audio_path,
            sr=None,
            offset=offset,
            duration=duration,
            mono=True
        )
        return audio, sr
    
    def resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: Optional[int] = None
    ) -> np.ndarray:
        """
        Resample audio to target sample rate.
        
        Args:
            audio: Audio array
            orig_sr: Original sample rate
            target_sr: Target sample rate (default: 16000)
            
        Returns:
            Resampled audio array
        """
        target_sr = target_sr or self.target_sample_rate
        
        if orig_sr == target_sr:
            return audio
        
        return librosa.resample(
            audio,
            orig_sr=orig_sr,
            target_sr=target_sr
        )
    
    def normalize(
        self,
        audio: np.ndarray,
        target_db: float = -20.0
    ) -> np.ndarray:
        """
        Normalize audio to target dB level.
        
        Args:
            audio: Audio array
            target_db: Target dB level (default: -20 dB)
            
        Returns:
            Normalized audio array
        """
        # Calculate current RMS
        rms = np.sqrt(np.mean(audio ** 2))
        
        if rms == 0:
            return audio
        
        # Calculate target RMS
        target_rms = 10 ** (target_db / 20)
        
        # Apply gain
        gain = target_rms / rms
        return audio * gain
    
    def remove_silence(
        self,
        audio: np.ndarray,
        sample_rate: int,
        threshold_db: float = -40.0,
        min_silence_duration: float = 0.3,
        keep_margin: float = 0.1
    ) -> np.ndarray:
        """
        Remove silence from audio.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate
            threshold_db: Silence threshold in dB
            min_silence_duration: Minimum silence to remove (seconds)
            keep_margin: Margin to keep around non-silent parts (seconds)
            
        Returns:
            Audio with silence removed
        """
        # Convert threshold to amplitude
        threshold = 10 ** (threshold_db / 20)
        
        # Find non-silent intervals
        intervals = librosa.effects.split(
            audio,
            top_db=-threshold_db,
            frame_length=int(sample_rate * 0.025),
            hop_length=int(sample_rate * 0.01)
        )
        
        if len(intervals) == 0:
            return audio
        
        # Add margin
        margin_samples = int(keep_margin * sample_rate)
        intervals[:, 0] = np.maximum(0, intervals[:, 0] - margin_samples)
        intervals[:, 1] = np.minimum(len(audio), intervals[:, 1] + margin_samples)
        
        # Concatenate non-silent parts
        return np.concatenate([audio[start:end] for start, end in intervals])
    
    def preprocess(
        self,
        audio_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        normalize: bool = True,
        remove_silence: bool = False,
        trim: bool = True
    ) -> str:
        """
        Full preprocessing pipeline for ASR input.
        
        Args:
            audio_path: Input audio file path
            output_path: Output file path (optional)
            normalize: Apply normalization
            remove_silence: Remove silent parts
            trim: Trim leading/trailing silence
            
        Returns:
            Path to preprocessed audio file
        """
        # Load audio
        audio, sr = self.load_audio(audio_path)
        
        # Resample to target
        if sr != self.target_sample_rate:
            audio = self.resample(audio, sr, self.target_sample_rate)
            sr = self.target_sample_rate
        
        # Trim silence
        if trim:
            audio, _ = librosa.effects.trim(audio, top_db=20)
        
        # Remove silence
        if remove_silence:
            audio = self.remove_silence(audio, sr)
        
        # Normalize
        if normalize:
            audio = self.normalize(audio)
        
        # Ensure no clipping
        audio = np.clip(audio, -1.0, 1.0)
        
        # Save output
        if output_path is None:
            output_path = Path(audio_path).with_suffix('.processed.wav')
        
        sf.write(output_path, audio, sr)
        
        return str(output_path)
    
    def get_duration(self, audio_path: Union[str, Path]) -> float:
        """Get audio duration in seconds."""
        return librosa.get_duration(path=audio_path)
    
    def chunk_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        chunk_duration: float,
        overlap: float = 0.0
    ) -> list:
        """
        Split audio into chunks.
        
        Args:
            audio: Audio array
            sample_rate: Sample rate
            chunk_duration: Chunk duration in seconds
            overlap: Overlap between chunks in seconds
            
        Returns:
            List of audio chunks
        """
        chunk_samples = int(chunk_duration * sample_rate)
        overlap_samples = int(overlap * sample_rate)
        
        chunks = []
        start = 0
        
        while start < len(audio):
            end = min(start + chunk_samples, len(audio))
            chunks.append(audio[start:end])
            start += chunk_samples - overlap_samples
        
        return chunks
