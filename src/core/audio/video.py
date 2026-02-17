"""Video file audio extraction."""

import subprocess
import tempfile
from pathlib import Path
from typing import Union, Optional, List


class VideoExtractor:
    """
    Extract and process audio from video files.
    
    Supports various video formats and extracts audio for ASR processing.
    
    Example:
        >>> extractor = VideoExtractor()
        >>> audio_path = extractor.extract("video.mp4")
        >>> segments = extractor.extract_with_timestamps("video.mp4")
    """
    
    SUPPORTED_FORMATS = [
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv'
    ]
    
    def __init__(
        self,
        target_sample_rate: int = 16000,
        ffmpeg_path: str = "ffmpeg"
    ):
        self.target_sample_rate = target_sample_rate
        self.ffmpeg_path = ffmpeg_path
        
        # Check ffmpeg availability
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Verify ffmpeg is installed."""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "ffmpeg not found. Please install ffmpeg: "
                "https://ffmpeg.org/download.html"
            )
    
    def extract(
        self,
        video_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        audio_track: int = 0
    ) -> str:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to video file
            output_path: Output audio file path (optional)
            audio_track: Audio track index (default: 0)
            
        Returns:
            Path to extracted audio file
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path is None:
            output_path = video_path.with_suffix('.wav')
        else:
            output_path = Path(output_path)
        
        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ac", "1",  # Mono
            "-ar", str(self.target_sample_rate),  # Target sample rate
            "-map", f"0:a:{audio_track}",  # Select audio track
            "-y",  # Overwrite output
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        
        return str(output_path)
    
    def extract_with_timestamps(
        self,
        video_path: Union[str, Path],
        segment_duration: float = 30.0,
        overlap: float = 0.0
    ) -> List[dict]:
        """
        Extract audio in segments with timestamps.
        
        Args:
            video_path: Path to video file
            segment_duration: Segment duration in seconds
            overlap: Overlap between segments in seconds
            
        Returns:
            List of dicts with 'start', 'end', and 'audio_path' keys
        """
        video_path = Path(video_path)
        
        # Get video duration
        duration = self.get_duration(video_path)
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        segments = []
        start = 0.0
        
        while start < duration:
            end = min(start + segment_duration, duration)
            
            segment_path = Path(temp_dir) / f"segment_{start:.1f}_{end:.1f}.wav"
            
            # Extract segment
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", str(self.target_sample_rate),
                "-ss", str(start),
                "-to", str(end),
                "-y",
                str(segment_path)
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            segments.append({
                'start': start,
                'end': end,
                'audio_path': str(segment_path)
            })
            
            start += segment_duration - overlap
        
        return segments
    
    def get_duration(self, video_path: Union[str, Path]) -> float:
        """
        Get video duration in seconds.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-show_entries", "format=duration",
            "-v", "quiet",
            "-of", "csv=p=0"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Try ffprobe
            cmd[0] = "ffprobe"
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        try:
            return float(result.stdout.strip())
        except ValueError:
            raise RuntimeError(f"Could not get video duration: {result.stderr}")
    
    def get_audio_tracks(self, video_path: Union[str, Path]) -> List[dict]:
        """
        Get information about audio tracks in video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of audio track information dicts
        """
        cmd = [
            "ffprobe",
            "-i", str(video_path),
            "-show_streams",
            "-select_streams", "a",
            "-v", "quiet",
            "-of", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        
        import json
        data = json.loads(result.stdout)
        
        tracks = []
        for stream in data.get('streams', []):
            tracks.append({
                'index': stream.get('index'),
                'codec': stream.get('codec_name'),
                'sample_rate': stream.get('sample_rate'),
                'channels': stream.get('channels'),
                'language': stream.get('tags', {}).get('language', 'unknown')
            })
        
        return tracks
    
    def is_supported(self, video_path: Union[str, Path]) -> bool:
        """Check if video format is supported."""
        ext = Path(video_path).suffix.lower()
        return ext in self.SUPPORTED_FORMATS
