"""
Audio streaming pipeline module

Provides high-performance audio processing pipelines
with backpressure handling and multi-threading support.
"""

from .streaming import AudioStreamingPipeline, PipelineConfig

__all__ = ["AudioStreamingPipeline", "PipelineConfig"]
