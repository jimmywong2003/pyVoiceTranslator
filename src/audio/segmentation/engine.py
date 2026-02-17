"""
Audio segmentation engine

Advanced segmentation with context awareness, gap merging,
and visualization data generation.
"""

import numpy as np
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import logging

from ..vad.silero_vad import AudioSegment

logger = logging.getLogger(__name__)


@dataclass
class SegmentationConfig:
    """Configuration for audio segmentation"""
    max_segment_duration: float = 30.0  # Maximum segment length in seconds
    min_segment_duration: float = 0.5   # Minimum segment length
    padding_before: float = 0.3         # Padding before speech (seconds)
    padding_after: float = 0.3          # Padding after speech (seconds)
    merge_gap_threshold: float = 0.5    # Merge segments with gap < threshold
    
    # Visualization settings
    generate_waveform: bool = True
    waveform_samples: int = 100


@dataclass
class SegmentedAudio:
    """Extended audio segment with metadata"""
    segment: AudioSegment
    waveform: Optional[np.ndarray] = None
    peak_amplitude: float = 0.0
    rms_amplitude: float = 0.0
    
    @property
    def start_time(self) -> float:
        return self.segment.start_time
    
    @property
    def end_time(self) -> float:
        return self.segment.end_time
    
    @property
    def duration(self) -> float:
        return self.segment.duration


class SegmentationEngine:
    """
    Advanced audio segmentation engine
    
    Features:
    - Context-aware segmentation
    - Gap merging for continuous speech
    - Amplitude analysis
    - Waveform generation for visualization
    
    Usage:
        config = SegmentationConfig(max_segment_duration=30.0)
        engine = SegmentationEngine(config)
        
        for vad_result in vad_stream:
            segments = engine.process_vad_result(vad_result)
            for segment in segments:
                print(f"Segment: {segment.duration:.2f}s")
    """
    
    def __init__(self, config: Optional[SegmentationConfig] = None):
        """
        Initialize segmentation engine
        
        Args:
            config: Segmentation configuration
        """
        self.config = config or SegmentationConfig()
        self.segments: List[SegmentedAudio] = []
        self.pending_segment: Optional[SegmentedAudio] = None
        self.pre_buffer = deque(maxlen=int(self.config.padding_before / 0.03) + 1)
        
        logger.info(f"SegmentationEngine initialized: "
                   f"max_duration={self.config.max_segment_duration}s, "
                   f"merge_gap={self.config.merge_gap_threshold}s")
    
    def process_vad_result(
        self,
        is_speech: bool,
        audio_chunk: np.ndarray,
        timestamp: float,
        confidence: float = 0.5
    ) -> List[SegmentedAudio]:
        """
        Process VAD result and generate segments
        
        Args:
            is_speech: Whether speech is detected
            audio_chunk: Audio data
            timestamp: Current timestamp
            confidence: VAD confidence score
            
        Returns:
            List of completed segments
        """
        completed_segments = []
        
        if is_speech:
            if self.pending_segment is None:
                # Start new segment
                self._start_new_segment(audio_chunk, timestamp, confidence)
            else:
                # Check if we need to split (max duration)
                current_duration = timestamp - self.pending_segment.start_time
                
                if current_duration >= self.config.max_segment_duration:
                    # Finalize current and start new
                    completed_segments.append(self._finalize_pending())
                    self._start_new_segment(audio_chunk, timestamp, confidence)
                else:
                    # Extend current segment
                    self._extend_segment(audio_chunk, timestamp, confidence)
        else:
            # Not speech
            self.pre_buffer.append(audio_chunk)
            
            if self.pending_segment is not None:
                # Check if silence duration exceeds threshold
                silence_duration = timestamp - self.pending_segment.end_time
                
                if silence_duration >= self.config.padding_after:
                    completed_segments.append(self._finalize_pending())
        
        return completed_segments
    
    def _start_new_segment(
        self,
        audio_chunk: np.ndarray,
        timestamp: float,
        confidence: float
    ):
        """Start a new speech segment"""
        # Include pre-buffer for natural start
        pre_audio = list(self.pre_buffer)
        
        if pre_audio:
            audio_data = np.concatenate(pre_audio + [audio_chunk])
            start_time = timestamp - len(pre_audio) * 0.03
        else:
            audio_data = audio_chunk
            start_time = timestamp
        
        base_segment = AudioSegment(
            start_time=start_time,
            end_time=timestamp + 0.03,
            audio_data=audio_data,
            confidence=confidence,
            sample_rate=16000  # Assumed, could be parameterized
        )
        
        self.pending_segment = self._create_segmented_audio(base_segment)
        logger.debug(f"New segment started at {start_time:.3f}s")
    
    def _extend_segment(
        self,
        audio_chunk: np.ndarray,
        timestamp: float,
        confidence: float
    ):
        """Extend current segment"""
        # Concatenate audio
        self.pending_segment.segment.audio_data = np.concatenate([
            self.pending_segment.segment.audio_data,
            audio_chunk
        ])
        self.pending_segment.segment.end_time = timestamp + 0.03
        
        # Update confidence (exponential moving average)
        alpha = 0.1
        self.pending_segment.segment.confidence = (
            self.pending_segment.segment.confidence * (1 - alpha) +
            confidence * alpha
        )
    
    def _finalize_pending(self) -> SegmentedAudio:
        """Finalize pending segment"""
        segment = self.pending_segment
        self.pending_segment = None
        self.pre_buffer.clear()
        
        # Apply post-padding
        segment.segment.end_time += self.config.padding_after
        
        # Calculate amplitude metrics
        audio_float = segment.segment.audio_data.astype(np.float32) / 32768.0
        segment.peak_amplitude = float(np.max(np.abs(audio_float)))
        segment.rms_amplitude = float(np.sqrt(np.mean(audio_float ** 2)))
        
        # Generate waveform if enabled
        if self.config.generate_waveform:
            segment.waveform = self._generate_waveform(segment.segment.audio_data)
        
        # Store segment
        self.segments.append(segment)
        
        logger.debug(f"Segment finalized: {segment.duration:.3f}s, "
                    f"peak={segment.peak_amplitude:.3f}")
        
        return segment
    
    def _create_segmented_audio(self, segment: AudioSegment) -> SegmentedAudio:
        """Create SegmentedAudio from AudioSegment"""
        return SegmentedAudio(
            segment=segment,
            waveform=None,
            peak_amplitude=0.0,
            rms_amplitude=0.0
        )
    
    def _generate_waveform(self, audio_data: np.ndarray) -> np.ndarray:
        """Generate downsampled waveform for visualization"""
        audio_float = np.abs(audio_data.astype(np.float32) / 32768.0)
        
        # Downsample to specified number of samples
        samples = self.config.waveform_samples
        if len(audio_float) <= samples:
            return audio_float
        
        # Reshape and take max of each bin
        bin_size = len(audio_float) // samples
        reshaped = audio_float[:bin_size * samples].reshape(samples, bin_size)
        return np.max(reshaped, axis=1)
    
    def merge_close_segments(self, segments: List[SegmentedAudio] = None) -> List[SegmentedAudio]:
        """
        Merge segments that are close together
        
        Args:
            segments: List to merge (uses stored segments if None)
            
        Returns:
            Merged segment list
        """
        if segments is None:
            segments = self.segments
        
        if len(segments) <= 1:
            return segments
        
        merged = [segments[0]]
        
        for segment in segments[1:]:
            last = merged[-1]
            gap = segment.start_time - last.end_time
            
            if gap <= self.config.merge_gap_threshold:
                # Merge segments
                last.segment.end_time = segment.end_time
                last.segment.audio_data = np.concatenate([
                    last.segment.audio_data,
                    segment.segment.audio_data
                ])
                last.segment.confidence = (last.segment.confidence + segment.segment.confidence) / 2
            else:
                merged.append(segment)
        
        return merged
    
    def get_visualization_data(self) -> Dict:
        """
        Get data for visualization
        
        Returns:
            Dictionary with segment info and waveforms
        """
        return {
            "segments": [
                {
                    "start": s.start_time,
                    "end": s.end_time,
                    "duration": s.duration,
                    "confidence": s.segment.confidence,
                    "peak_amplitude": s.peak_amplitude,
                    "rms_amplitude": s.rms_amplitude,
                    "waveform": s.waveform.tolist() if s.waveform is not None else None
                }
                for s in self.segments
            ],
            "total_speech_duration": sum(s.duration for s in self.segments),
            "segment_count": len(self.segments),
            "average_segment_duration": (
                sum(s.duration for s in self.segments) / len(self.segments)
                if self.segments else 0
            )
        }
    
    def get_segments(self) -> List[SegmentedAudio]:
        """Get all completed segments"""
        return self.segments.copy()
    
    def clear(self):
        """Clear all segments"""
        self.segments = []
        self.pending_segment = None
        self.pre_buffer.clear()
        logger.debug("SegmentationEngine cleared")
    
    def force_finalize(self) -> Optional[SegmentedAudio]:
        """Force finalize any pending segment"""
        if self.pending_segment is not None:
            return self._finalize_pending()
        return None
