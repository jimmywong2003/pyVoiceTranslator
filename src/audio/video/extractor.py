"""
Video audio extractor

Extract audio from video files for testing and processing.
Uses FFmpeg for maximum format compatibility.
"""

import subprocess
import tempfile
import os
import io
import wave
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class VideoAudioExtractor:
    """
    Extract audio from video files
    
    Supports all formats supported by FFmpeg including:
    - MP4, AVI, MKV, MOV, WMV
    - WebM, FLV, MPEG
    
    Usage:
        extractor = VideoAudioExtractor(sample_rate=16000)
        
        # Extract to file
        audio_path = extractor.extract_audio("video.mp4", "output.wav")
        
        # Extract to numpy array
        audio_data = extractor.extract_to_numpy("video.mp4")
        
        # Stream processing
        for chunk in extractor.extract_streaming("video.mp4", chunk_size=480):
            process_chunk(chunk)
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize video audio extractor
        
        Args:
            sample_rate: Target sample rate for extracted audio
            channels: Number of audio channels (1=mono, 2=stereo)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        
        # Verify FFmpeg is available
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self):
        """Verify FFmpeg is installed"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                logger.info(f"FFmpeg found: {version_line}")
            else:
                raise RuntimeError("FFmpeg not working properly")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg:\n"
                "  Windows: choco install ffmpeg\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: apt install ffmpeg"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg verification timed out")
    
    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        format: str = "wav"
    ) -> str:
        """
        Extract audio from video file to file
        
        Args:
            video_path: Path to video file
            output_path: Output audio file path (auto-generated if None)
            format: Output format (wav, mp3, etc.)
            
        Returns:
            Path to extracted audio file
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=f".{format}")
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", video_path,
            "-vn",  # No video
            "-ar", str(self.sample_rate),  # Sample rate
            "-ac", str(self.channels),  # Channels
        ]
        
        # Format-specific options
        if format == "wav":
            cmd.extend(["-acodec", "pcm_s16le"])  # PCM 16-bit
        elif format == "mp3":
            cmd.extend(["-acodec", "libmp3lame", "-q:a", "2"])
        
        cmd.append(output_path)
        
        logger.info(f"Extracting audio from {video_path} to {output_path}")
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        logger.info(f"Audio extracted successfully: {output_path}")
        return output_path
    
    def extract_to_numpy(self, video_path: str) -> np.ndarray:
        """
        Extract audio directly to numpy array
        
        Args:
            video_path: Path to video file
            
        Returns:
            Audio as numpy array (int16)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-f", "wav",
            "-"
        ]
        
        logger.info(f"Extracting audio from {video_path} to memory")
        
        result = subprocess.run(
            cmd,
            capture_output=True
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"FFmpeg failed: {stderr}")
        
        # Parse WAV data
        audio_data = self._parse_wav(result.stdout)
        
        logger.info(f"Audio extracted: {len(audio_data)} samples")
        return audio_data
    
    def extract_streaming(
        self,
        video_path: str,
        chunk_size: int = 480,
        offset: float = 0.0,
        duration: Optional[float] = None
    ):
        """
        Stream audio from video file in chunks
        
        Args:
            video_path: Path to video file
            chunk_size: Number of samples per chunk
            offset: Start offset in seconds
            duration: Maximum duration to extract (None for all)
            
        Yields:
            Audio chunks as numpy arrays
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(offset),  # Start offset
        ]
        
        if duration is not None:
            cmd.extend(["-t", str(duration)])
        
        cmd.extend([
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-f", "wav",
            "-"
        ])
        
        logger.info(f"Streaming audio from {video_path}")
        
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Skip WAV header (44 bytes)
        header = process.stdout.read(44)
        if len(header) < 44:
            raise RuntimeError("Failed to read WAV header")
        
        bytes_per_sample = 2  # 16-bit
        bytes_per_chunk = chunk_size * bytes_per_sample * self.channels
        
        try:
            while True:
                chunk_bytes = process.stdout.read(bytes_per_chunk)
                if not chunk_bytes:
                    break
                
                # Convert to numpy
                chunk = np.frombuffer(chunk_bytes, dtype=np.int16)
                
                # Convert to mono if stereo
                if self.channels == 2:
                    chunk = chunk.reshape(-1, 2).mean(axis=1).astype(np.int16)
                
                yield chunk
        
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    def _parse_wav(self, wav_data: bytes) -> np.ndarray:
        """Parse WAV data to numpy array"""
        wav_file = wave.open(io.BytesIO(wav_data), 'rb')
        
        try:
            n_channels = wav_file.getnchannels()
            n_frames = wav_file.getnframes()
            
            # Read all frames
            raw_data = wav_file.readframes(n_frames)
            audio_data = np.frombuffer(raw_data, dtype=np.int16)
            
            # Convert to mono if stereo
            if n_channels == 2:
                audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
            
            return audio_data
        
        finally:
            wav_file.close()
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video file information
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=codec_name,sample_rate,channels",
            "-of", "json",
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        
        import json
        info = json.loads(result.stdout)
        
        return {
            "duration": float(info.get("format", {}).get("duration", 0)),
            "audio_streams": [
                {
                    "codec": stream.get("codec_name"),
                    "sample_rate": int(stream.get("sample_rate", 0)),
                    "channels": int(stream.get("channels", 0))
                }
                for stream in info.get("streams", [])
                if stream.get("codec_type") == "audio"
            ]
        }
