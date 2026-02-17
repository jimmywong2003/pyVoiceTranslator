"""
Audio Processing Module for Real-Time Voice Translation

This module provides:
- Cross-platform audio capture (microphone + system audio)
- Voice Activity Detection (VAD)
- Audio segmentation
- Streaming pipeline
- Performance optimization

Supported Platforms:
- Windows (WASAPI)
- macOS (CoreAudio + BlackHole)

Author: AI Assistant
Version: 1.0.0
"""

__version__ = "1.0.0"
__all__ = [
    "AudioManager",
    "AudioConfig",
    "AudioSource",
    "SileroVADProcessor",
    "SegmentationEngine",
    "AudioStreamingPipeline",
    "AudioDetectionTester",
    "VideoAudioExtractor",
]

from .config import AudioConfig, AudioSource
from .capture.manager import AudioManager
from .vad.silero_vad import SileroVADProcessor
from .segmentation.engine import SegmentationEngine, SegmentationConfig
from .pipeline.streaming import AudioStreamingPipeline, PipelineConfig
from .testing.detection import AudioDetectionTester
from .video.extractor import VideoAudioExtractor
