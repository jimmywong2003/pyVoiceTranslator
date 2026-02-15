"""
Configuration classes for audio processing module
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AudioSource(Enum):
    """Audio source types"""
    MICROPHONE = "microphone"
    SYSTEM_AUDIO = "system_audio"
    FILE = "file"


@dataclass
class AudioConfig:
    """Configuration for audio capture and processing"""
    sample_rate: int = 16000
    chunk_duration_ms: int = 30
    channels: int = 1
    dtype: str = "int16"
    device_index: Optional[int] = None
    
    @property
    def chunk_samples(self) -> int:
        """Calculate number of samples per chunk"""
        return int(self.sample_rate * self.chunk_duration_ms / 1000)


@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection"""
    model: str = "silero"  # "silero" or "webrtc"
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 100
    speech_pad_ms: int = 30
    use_onnx: bool = False  # Use ONNX runtime for Silero


@dataclass
class PipelineConfig:
    """Configuration for audio streaming pipeline"""
    buffer_size_ms: int = 3000
    processing_threads: int = 2
    enable_backpressure: bool = True
    max_queue_size: int = 100


@dataclass
class SegmentationConfig:
    """Configuration for audio segmentation"""
    max_segment_duration: float = 30.0
    min_segment_duration: float = 0.5
    padding_before: float = 0.3
    padding_after: float = 0.3
    merge_gap_threshold: float = 0.5
