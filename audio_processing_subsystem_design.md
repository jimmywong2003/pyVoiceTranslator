# Audio Processing Subsystem Design
## Real-Time Voice Translation Application

---

## 1. VAD Library Comparison & Recommendations

### 1.1 Summary Table

| Library | Accuracy | CPU Usage | Latency | Model Size | License | Best For |
|---------|----------|-----------|---------|------------|---------|----------|
| **Silero VAD** | High (92.5% F1) | Medium (0.43% CPU) | 30-100ms | ~1MB | MIT | **Recommended Primary** |
| **WebRTC VAD** | Low (64.6% F1) | Very Low (~0.05% CPU) | 10-30ms | <100KB | BSD | Low-resource fallback |
| **Pyannote.audio** | High (92.3% F1) | High | 2000ms | ~2.4MB | MIT | Research/Diarization |
| **Cobra VAD** | Very High (98.9% TPR) | Ultra Low (0.05% CPU) | ~30ms | ~115KB | Commercial | Production enterprise |

### 1.2 Detailed Analysis

#### Silero VAD (RECOMMENDED PRIMARY)
```
Version: silero-vad v5.1 (latest as of 2024)
Installation: pip install silero-vad
```

**Pros:**
- Deep learning-based with excellent accuracy
- Supports multiple sample rates (8kHz, 16kHz, 32kHz, 48kHz)
- Streaming-ready with 30-100ms chunks
- ONNX runtime option for better performance
- Multilingual training (>6,000 languages)
- Active development and community

**Cons:**
- Requires PyTorch/ONNX dependency
- Higher memory footprint than WebRTC
- Not optimized for microcontrollers

**Performance Metrics:**
- RTF (Real-Time Factor): 0.004 on AMD Ryzen 9 5900X
- Processing: 15.4 sec/hour of audio
- CPU Usage: ~0.43% on desktop, ~43% on Raspberry Pi Zero

#### WebRTC VAD (FALLBACK OPTION)
```
Version: webrtcvad v2.0.10
Installation: pip install webrtcvad
```

**Pros:**
- Extremely lightweight
- No external dependencies
- Very low latency
- Battle-tested in production

**Cons:**
- Uses outdated Gaussian Mixture Models
- Lower accuracy in noise
- Limited to 8/16/32/48 kHz
- Primarily English-focused

**Performance Metrics:**
- At 5% FPR: 50% TPR (misses 1/2 speech frames)
- At 25% FPR: Better performance but high false positives

#### Pyannote.audio (NOT RECOMMENDED FOR EDGE)
```
Version: pyannote.audio 3.1.x
Installation: pip install pyannote.audio
```

**Pros:**
- State-of-the-art accuracy
- Good for speaker diarization
- Open source

**Cons:**
- Research-oriented, not production-optimized
- High resource usage
- 2-second window (not streaming-friendly)
- Requires large model downloads

### 1.3 Recommended Strategy

**Hybrid Approach:**
1. **Primary**: Silero VAD for high accuracy
2. **Fallback**: WebRTC VAD for low-resource scenarios
3. **Configuration**: Allow runtime switching based on CPU load

---

## 2. Audio Capture Architecture

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Audio Capture Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Microphone  │    │ System Audio │    │ Video File   │      │
│  │   Capture    │    │  (Loopback)  │    │  Extraction  │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                    │              │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐      │
│  │  PortAudio   │    │   WASAPI     │    │    FFmpeg    │      │
│  │   (Cross)    │    │  (Windows)   │    │  (Cross)     │      │
│  │              │    │   CoreAudio  │    │              │      │
│  │              │    │   (macOS)    │    │              │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
└─────────┼───────────────────┼───────────────────┼──────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│              Audio Processing Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Resample   │───▶│    VAD       │───▶│ Segmentation │      │
│  │  (16kHz)     │    │  (Silero)    │    │   Engine     │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                  │              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐      │
│  │   Output     │◀───│   Buffer     │◀───│   Chunk      │      │
│  │   Queue      │    │   Manager    │    │   Buffer     │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Platform-Specific Capture Implementation

#### Windows (WASAPI Loopback)

```python
# Windows System Audio Capture via WASAPI
import pyaudiowpatch as pyaudio
import numpy as np

class WindowsAudioCapture:
    """WASAPI-based audio capture for Windows"""
    
    def __init__(self, sample_rate=16000, chunk_duration_ms=30):
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        self.p = None
        self.stream = None
        
    def get_loopback_device(self):
        """Find WASAPI loopback device"""
        p = pyaudio.PyAudio()
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"]
            )
            
            # Check if already loopback
            if default_speakers.get("isLoopbackDevice"):
                return default_speakers
                
            # Find matching loopback device
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    return loopback
            return None
        finally:
            p.terminate()
    
    def start_capture(self, callback):
        """Start capturing system audio"""
        device = self.get_loopback_device()
        if not device:
            raise RuntimeError("No loopback device found")
            
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=device["maxInputChannels"],
            rate=int(device["defaultSampleRate"]),
            frames_per_buffer=self.chunk_size,
            input=True,
            input_device_index=device["index"],
            stream_callback=callback
        )
        self.stream.start_stream()
```

#### macOS (CoreAudio + BlackHole)

```python
# macOS Audio Capture via CoreAudio
import sounddevice as sd
import numpy as np

class MacOSAudioCapture:
    """CoreAudio-based audio capture for macOS"""
    
    def __init__(self, sample_rate=16000, chunk_duration_ms=30):
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        self.stream = None
        
    def find_blackhole_device(self):
        """Find BlackHole virtual audio device"""
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if "BlackHole" in device["name"] and device["max_input_channels"] > 0:
                return idx, device
        return None, None
    
    def find_microphone(self):
        """Find default microphone"""
        devices = sd.query_devices()
        default_input = sd.query_devices(kind="input")
        for idx, device in enumerate(devices):
            if device["name"] == default_input["name"]:
                return idx, device
        return None, None
    
    def start_capture(self, device_idx, callback):
        """Start audio capture"""
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")
            callback(indata.copy())
            
        self.stream = sd.InputStream(
            device=device_idx,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            dtype=np.int16,
            callback=audio_callback
        )
        self.stream.start()
```

### 2.3 Cross-Platform Audio Manager

```python
# audio_manager.py
import platform
import numpy as np
from enum import Enum
from typing import Callable, Optional
from dataclasses import dataclass

class AudioSource(Enum):
    MICROPHONE = "microphone"
    SYSTEM_AUDIO = "system_audio"
    FILE = "file"

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    chunk_duration_ms: int = 30
    channels: int = 1
    dtype: str = "int16"

class AudioManager:
    """Cross-platform audio capture manager"""
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.platform = platform.system()
        self.capture = None
        self.is_recording = False
        
    def initialize(self, source: AudioSource):
        """Initialize audio capture for specified source"""
        if self.platform == "Windows":
            from .windows_capture import WindowsAudioCapture
            self.capture = WindowsAudioCapture(
                self.config.sample_rate,
                self.config.chunk_duration_ms
            )
        elif self.platform == "Darwin":  # macOS
            from .macos_capture import MacOSAudioCapture
            self.capture = MacOSAudioCapture(
                self.config.sample_rate,
                self.config.chunk_duration_ms
            )
        else:
            raise NotImplementedError(f"Platform {self.platform} not supported")
            
    def list_devices(self) -> list:
        """List available audio devices"""
        return self.capture.list_devices()
    
    def start(self, callback: Callable[[np.ndarray], None]):
        """Start audio capture"""
        self.capture.start_capture(callback)
        self.is_recording = True
        
    def stop(self):
        """Stop audio capture"""
        self.capture.stop_capture()
        self.is_recording = False
```

---

## 3. Voice Activity Detection & Segmentation

### 3.1 VAD Pipeline Architecture

```python
# vad_pipeline.py
import numpy as np
import torch
from collections import deque
from typing import List, Callable, Optional
from dataclasses import dataclass
from enum import Enum

class VADState(Enum):
    SILENCE = "silence"
    SPEECH = "speech"
    UNKNOWN = "unknown"

@dataclass
class AudioSegment:
    """Represents a detected speech segment"""
    start_time: float
    end_time: float
    audio_data: np.ndarray
    confidence: float
    sample_rate: int
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def to_bytes(self) -> bytes:
        return self.audio_data.tobytes()

class SileroVADProcessor:
    """Silero VAD processor with streaming support"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        speech_pad_ms: int = 30
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        
        # Load Silero VAD model
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False  # Set to True for ONNX runtime
        )
        self.get_speech_timestamps = utils[0]
        
        # State tracking
        self.buffer = deque(maxlen=int(3000 / 30))  # 3 seconds buffer
        self.current_segment: Optional[AudioSegment] = None
        self.silence_counter = 0
        self.speech_counter = 0
        self.state = VADState.SILENCE
        self.start_time = 0.0
        self.chunk_idx = 0
        
    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[AudioSegment]:
        """
        Process a single audio chunk through VAD
        
        Args:
            audio_chunk: Audio data as numpy array (int16 or float32)
            
        Returns:
            AudioSegment if speech segment completed, None otherwise
        """
        # Convert to float32 tensor
        if audio_chunk.dtype == np.int16:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk.astype(np.float32)
            
        audio_tensor = torch.from_numpy(audio_float)
        
        # Get VAD probability
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
        
        # State machine
        segment = None
        current_time = self.chunk_idx * 30 / 1000  # 30ms chunks
        
        if speech_prob >= self.threshold:
            # Speech detected
            self.speech_counter += 1
            self.silence_counter = 0
            
            if self.state == VADState.SILENCE and self.speech_counter >= 3:
                # Transition to speech
                self.state = VADState.SPEECH
                self.start_time = current_time - self.speech_pad_ms / 1000
                self.current_segment_audio = []
                
        else:
            # Silence detected
            self.silence_counter += 1
            self.speech_counter = 0
            
            if self.state == VADState.SPEECH and self.silence_counter >= 5:
                # Transition to silence - finalize segment
                segment = self._finalize_segment(current_time)
                self.state = VADState.SILENCE
                
        # Accumulate audio if in speech state
        if self.state == VADState.SPEECH:
            self.current_segment_audio.append(audio_chunk)
            
        self.chunk_idx += 1
        return segment
    
    def _finalize_segment(self, end_time: float) -> AudioSegment:
        """Finalize current speech segment"""
        audio_data = np.concatenate(self.current_segment_audio)
        
        return AudioSegment(
            start_time=self.start_time,
            end_time=end_time + self.speech_pad_ms / 1000,
            audio_data=audio_data,
            confidence=0.8,  # Could be averaged from VAD probs
            sample_rate=self.sample_rate
        )
    
    def reset(self):
        """Reset VAD state"""
        self.buffer.clear()
        self.current_segment = None
        self.silence_counter = 0
        self.speech_counter = 0
        self.state = VADState.SILENCE
        self.chunk_idx = 0
```

### 3.2 Advanced Segmentation with Context

```python
# segmentation_engine.py
import numpy as np
from typing import List, Callable
from dataclasses import dataclass, field
from collections import deque

@dataclass
class SegmentationConfig:
    """Configuration for audio segmentation"""
    max_segment_duration: float = 30.0  # Maximum segment length in seconds
    min_segment_duration: float = 0.5   # Minimum segment length
    padding_before: float = 0.3         # Padding before speech (seconds)
    padding_after: float = 0.3          # Padding after speech (seconds)
    merge_gap_threshold: float = 0.5    # Merge segments with gap < threshold
    
class SegmentationEngine:
    """Advanced audio segmentation with context awareness"""
    
    def __init__(self, config: SegmentationConfig = None):
        self.config = config or SegmentationConfig()
        self.segments: List[AudioSegment] = []
        self.pending_segment: AudioSegment = None
        self.pre_buffer = deque(maxlen=100)  # Pre-speech buffer
        
    def process_vad_result(
        self,
        is_speech: bool,
        audio_chunk: np.ndarray,
        timestamp: float,
        confidence: float
    ) -> List[AudioSegment]:
        """
        Process VAD result and generate segments
        
        Returns:
            List of completed segments
        """
        completed_segments = []
        
        if is_speech:
            if self.pending_segment is None:
                # Start new segment with pre-buffer
                pre_audio = list(self.pre_buffer)
                if pre_audio:
                    audio_data = np.concatenate(pre_audio + [audio_chunk])
                else:
                    audio_data = audio_chunk
                    
                self.pending_segment = AudioSegment(
                    start_time=timestamp - len(pre_audio) * 0.03,
                    end_time=timestamp + 0.03,
                    audio_data=audio_data,
                    confidence=confidence,
                    sample_rate=16000
                )
            else:
                # Extend current segment
                self.pending_segment.audio_data = np.concatenate([
                    self.pending_segment.audio_data,
                    audio_chunk
                ])
                self.pending_segment.end_time = timestamp + 0.03
                self.pending_segment.confidence = (
                    self.pending_segment.confidence * 0.9 + confidence * 0.1
                )
                
            # Check max duration
            if self.pending_segment.duration >= self.config.max_segment_duration:
                completed_segments.append(self._finalize_pending())
        else:
            # Not speech
            self.pre_buffer.append(audio_chunk)
            
            if self.pending_segment is not None:
                # Check if silence duration exceeds threshold
                silence_duration = timestamp - self.pending_segment.end_time
                if silence_duration >= self.config.padding_after:
                    completed_segments.append(self._finalize_pending())
                    
        return completed_segments
    
    def _finalize_pending(self) -> AudioSegment:
        """Finalize pending segment"""
        segment = self.pending_segment
        self.pending_segment = None
        self.pre_buffer.clear()
        
        # Apply post-padding
        segment.end_time += self.config.padding_after
        
        return segment
    
    def get_visualization_data(self) -> dict:
        """Get data for visualization"""
        return {
            "segments": [
                {
                    "start": s.start_time,
                    "end": s.end_time,
                    "duration": s.duration,
                    "confidence": s.confidence
                }
                for s in self.segments
            ],
            "total_speech_duration": sum(s.duration for s in self.segments),
            "segment_count": len(self.segments)
        }
```

---

## 4. Audio Streaming Pipeline

### 4.1 Pipeline Architecture

```python
# streaming_pipeline.py
import asyncio
import numpy as np
from typing import AsyncIterator, Callable, Optional
from dataclasses import dataclass
from queue import Queue
import threading
import time

@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    buffer_size_ms: int = 3000
    processing_threads: int = 2
    enable_backpressure: bool = True
    max_queue_size: int = 100

class AudioStreamingPipeline:
    """High-performance audio streaming pipeline"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.input_queue = Queue(maxsize=self.config.max_queue_size)
        self.output_queue = Queue()
        self.processors: List[Callable] = []
        self.is_running = False
        self.threads: List[threading.Thread] = []
        self.metrics = {
            "chunks_processed": 0,
            "chunks_dropped": 0,
            "avg_processing_time": 0.0,
            "start_time": None
        }
        
    def add_processor(self, processor: Callable[[np.ndarray], np.ndarray]):
        """Add audio processor to pipeline"""
        self.processors.append(processor)
        
    def start(self):
        """Start the pipeline"""
        self.is_running = True
        self.metrics["start_time"] = time.time()
        
        # Start processing threads
        for i in range(self.config.processing_threads):
            thread = threading.Thread(
                target=self._processing_loop,
                name=f"AudioProcessor-{i}"
            )
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
            
    def stop(self):
        """Stop the pipeline"""
        self.is_running = False
        for thread in self.threads:
            thread.join(timeout=1.0)
            
    def feed(self, audio_chunk: np.ndarray) -> bool:
        """
        Feed audio chunk into pipeline
        
        Returns:
            True if accepted, False if dropped (backpressure)
        """
        if not self.config.enable_backpressure:
            # Drop oldest if full
            while self.input_queue.full():
                try:
                    self.input_queue.get_nowait()
                    self.metrics["chunks_dropped"] += 1
                except:
                    break
                    
        try:
            self.input_queue.put_nowait(audio_chunk)
            return True
        except:
            self.metrics["chunks_dropped"] += 1
            return False
            
    def _processing_loop(self):
        """Main processing loop"""
        while self.is_running:
            try:
                chunk = self.input_queue.get(timeout=0.1)
                start_time = time.perf_counter()
                
                # Process through all processors
                processed = chunk
                for processor in self.processors:
                    processed = processor(processed)
                    
                processing_time = time.perf_counter() - start_time
                self._update_metrics(processing_time)
                
                self.output_queue.put(processed)
                
            except:
                continue
                
    def _update_metrics(self, processing_time: float):
        """Update performance metrics"""
        self.metrics["chunks_processed"] += 1
        # Exponential moving average
        alpha = 0.1
        self.metrics["avg_processing_time"] = (
            alpha * processing_time +
            (1 - alpha) * self.metrics["avg_processing_time"]
        )
        
    def get_output(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get processed audio chunk"""
        try:
            return self.output_queue.get(timeout=timeout)
        except:
            return None
            
    def get_metrics(self) -> dict:
        """Get pipeline metrics"""
        runtime = time.time() - self.metrics["start_time"]
        return {
            **self.metrics,
            "runtime_seconds": runtime,
            "throughput_chunks_per_sec": (
                self.metrics["chunks_processed"] / runtime if runtime > 0 else 0
            ),
            "drop_rate": (
                self.metrics["chunks_dropped"] /
                (self.metrics["chunks_processed"] + self.metrics["chunks_dropped"])
                if (self.metrics["chunks_processed"] + self.metrics["chunks_dropped"]) > 0 else 0
            )
        }
```

### 4.2 Async Streaming Support

```python
# async_pipeline.py
import asyncio
import numpy as np
from typing import AsyncIterator, Callable

class AsyncAudioPipeline:
    """Async audio streaming pipeline for coroutine-based processing"""
    
    def __init__(self):
        self.input_queue = asyncio.Queue(maxsize=100)
        self.processors: List[Callable[[np.ndarray], np.ndarray]] = []
        self.is_running = False
        
    async def feed(self, audio_chunk: np.ndarray):
        """Feed audio chunk asynchronously"""
        await self.input_queue.put(audio_chunk)
        
    async def process_stream(
        self,
        input_stream: AsyncIterator[np.ndarray]
    ) -> AsyncIterator[np.ndarray]:
        """
        Process async audio stream
        
        Usage:
            async for chunk in pipeline.process_stream(audio_source):
                await output_handler(chunk)
        """
        async for chunk in input_stream:
            processed = chunk
            for processor in self.processors:
                processed = processor(processed)
            yield processed
            
    def add_processor(self, processor: Callable[[np.ndarray], np.ndarray]):
        """Add processor to pipeline"""
        self.processors.append(processor)
```

---

## 5. CPU Optimization Strategies

### 5.1 Optimization Techniques

```python
# optimizations.py
import numpy as np
import numba
from functools import lru_cache
import torch

class CPUOptimizations:
    """CPU optimization utilities for audio processing"""
    
    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def fast_rms(audio: np.ndarray) -> float:
        """Fast RMS calculation using Numba"""
        return np.sqrt(np.mean(audio.astype(np.float64) ** 2))
    
    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def fast_energy(audio: np.ndarray) -> float:
        """Fast energy calculation"""
        return np.sum(audio.astype(np.float64) ** 2)
    
    @staticmethod
    def optimize_torch():
        """Optimize PyTorch for inference"""
        # Disable gradient computation
        torch.set_grad_enabled(False)
        
        # Set number of threads
        torch.set_num_threads(2)
        
        # Enable inference mode
        torch.inference_mode(True)
        
        # Use MKL if available (Intel)
        if hasattr(torch, 'backends') and hasattr(torch.backends, 'mkl'):
            torch.backends.mkl.verbose = False
            
    @staticmethod
    def resample_fast(
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """Fast audio resampling using linear interpolation"""
        if orig_sr == target_sr:
            return audio
            
        # Simple linear interpolation (fast but lower quality)
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)

class AudioBufferPool:
    """Object pool for audio buffers to reduce GC pressure"""
    
    def __init__(self, buffer_size: int, pool_size: int = 10):
        self.buffer_size = buffer_size
        self.pool = [np.zeros(buffer_size, dtype=np.int16) 
                     for _ in range(pool_size)]
        self.available = list(range(pool_size))
        self.lock = threading.Lock()
        
    def acquire(self) -> np.ndarray:
        """Acquire buffer from pool"""
        with self.lock:
            if self.available:
                idx = self.available.pop()
                return self.pool[idx], idx
            else:
                # Pool exhausted - allocate new
                return np.zeros(self.buffer_size, dtype=np.int16), -1
                
    def release(self, idx: int):
        """Release buffer back to pool"""
        if idx >= 0:
            with self.lock:
                self.available.append(idx)
```

### 5.2 Platform-Specific Optimizations

```python
# platform_optimizations.py
import platform
import os

def apply_platform_optimizations():
    """Apply platform-specific optimizations"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # Apple Silicon optimizations
        if platform.machine() == "arm64":
            # Use MPS (Metal Performance Shaders) if available
            import torch
            if torch.backends.mps.is_available():
                print("MPS backend available for Apple Silicon")
                
        # Set process priority
        os.nice(-5)  # Higher priority
        
    elif system == "Windows":
        # Windows-specific optimizations
        try:
            import ctypes
            # Set high priority
            ctypes.windll.kernel32.SetPriorityClass(
                ctypes.windll.kernel32.GetCurrentProcess(),
                0x00000080  # HIGH_PRIORITY_CLASS
            )
        except:
            pass
            
        # Disable Windows timer resolution throttling
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            winmm.timeBeginPeriod(1)
        except:
            pass
            
    # Common optimizations
    import torch
    torch.set_num_threads(2)  # Limit threads for better latency
```

---

## 6. Audio Detection Test Functionality

### 6.1 Test Suite

```python
# audio_tests.py
import numpy as np
import time
from typing import Dict, List, Callable
from dataclasses import dataclass
import sounddevice as sd

@dataclass
class TestResult:
    """Audio test result"""
    test_name: str
    passed: bool
    message: str
    metrics: Dict = None
    duration_ms: float = 0.0

class AudioDetectionTester:
    """Test functionality for audio input sources"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.test_duration = 3  # seconds
        
    def test_microphone(self) -> TestResult:
        """Test microphone input"""
        start_time = time.time()
        
        try:
            # Query devices
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if not input_devices:
                return TestResult(
                    "microphone",
                    False,
                    "No input devices found"
                )
                
            # Try to record
            recording = sd.rec(
                int(self.test_duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16
            )
            sd.wait()
            
            # Analyze recording
            rms = np.sqrt(np.mean(recording.astype(np.float64) ** 2))
            max_val = np.max(np.abs(recording))
            
            # Check if signal is present
            if rms < 10:  # Very low signal
                return TestResult(
                    "microphone",
                    False,
                    f"Microphone signal too weak (RMS: {rms:.2f}). Check if muted.",
                    {"rms": rms, "max": max_val},
                    (time.time() - start_time) * 1000
                )
                
            return TestResult(
                "microphone",
                True,
                f"Microphone working. RMS: {rms:.2f}, Max: {max_val}",
                {"rms": rms, "max": max_val},
                (time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return TestResult(
                "microphone",
                False,
                f"Microphone test failed: {str(e)}"
            )
            
    def test_system_audio(self) -> TestResult:
        """Test system audio capture (loopback)"""
        start_time = time.time()
        system = platform.system()
        
        try:
            if system == "Windows":
                return self._test_windows_loopback()
            elif system == "Darwin":
                return self._test_macos_loopback()
            else:
                return TestResult(
                    "system_audio",
                    False,
                    f"System audio not supported on {system}"
                )
        except Exception as e:
            return TestResult(
                "system_audio",
                False,
                f"System audio test failed: {str(e)}"
            )
            
    def _test_windows_loopback(self) -> TestResult:
        """Test Windows WASAPI loopback"""
        import pyaudiowpatch as pyaudio
        
        p = pyaudio.PyAudio()
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"]
            )
            
            # Check for loopback capability
            if not default_speakers.get("isLoopbackDevice"):
                # Try to find loopback device
                found = False
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        found = True
                        break
                        
                if not found:
                    return TestResult(
                        "system_audio",
                        False,
                        "No loopback device found. Install stereo mix or VB-Cable."
                    )
                    
            return TestResult(
                "system_audio",
                True,
                f"Windows loopback available: {default_speakers['name']}"
            )
            
        finally:
            p.terminate()
            
    def _test_macos_loopback(self) -> TestResult:
        """Test macOS loopback via BlackHole"""
        devices = sd.query_devices()
        blackhole = None
        
        for idx, device in enumerate(devices):
            if "BlackHole" in device["name"] and device["max_input_channels"] > 0:
                blackhole = device
                break
                
        if blackhole is None:
            return TestResult(
                "system_audio",
                False,
                "BlackHole not found. Install from https://github.com/ExistentialAudio/BlackHole"
            )
            
        return TestResult(
            "system_audio",
            True,
            f"BlackHole found: {blackhole['name']}"
        )
        
    def run_all_tests(self) -> List[TestResult]:
        """Run all audio detection tests"""
        tests = [
            self.test_microphone(),
            self.test_system_audio()
        ]
        return tests
```

---

## 7. Video File Audio Extraction

```python
# video_audio_extractor.py
import subprocess
import tempfile
import os
from typing import Optional
import numpy as np

class VideoAudioExtractor:
    """Extract audio from video files for testing"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        
    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Extract audio from video file
        
        Args:
            video_path: Path to video file
            output_path: Optional output path (auto-generated if None)
            
        Returns:
            Path to extracted audio file
        """
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")
            
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ar", str(self.sample_rate),  # Sample rate
            "-ac", "1",  # Mono
            "-y",  # Overwrite
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
        return output_path
        
    def extract_to_numpy(self, video_path: str) -> np.ndarray:
        """
        Extract audio directly to numpy array
        
        Args:
            video_path: Path to video file
            
        Returns:
            Audio as numpy array (int16)
        """
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate),
            "-ac", "1",
            "-f", "wav",
            "-"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed")
            
        # Parse WAV header and extract data
        import io
        import wave
        
        wav_file = wave.open(io.BytesIO(result.stdout), 'rb')
        n_frames = wav_file.getnframes()
        audio_data = np.frombuffer(
            wav_file.readframes(n_frames),
            dtype=np.int16
        )
        wav_file.close()
        
        return audio_data
```

---

## 8. Performance Benchmarking

```python
# benchmarking.py
import time
import numpy as np
from typing import Dict, List, Callable
from dataclasses import dataclass
import statistics

@dataclass
class BenchmarkResult:
    """Benchmark result"""
    name: str
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput_chunks_per_sec: float
    cpu_percent: float
    
class AudioBenchmark:
    """Performance benchmarking for audio pipeline"""
    
    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        
    def benchmark_vad(
        self,
        vad_processor,
        num_chunks: int = 1000,
        audio_data: np.ndarray = None
    ) -> BenchmarkResult:
        """Benchmark VAD processor"""
        
        if audio_data is None:
            # Generate test audio
            audio_data = np.random.randint(
                -32768, 32767,
                size=self.chunk_samples,
                dtype=np.int16
            )
            
        times = []
        
        # Warmup
        for _ in range(10):
            vad_processor.process_chunk(audio_data)
            
        # Benchmark
        start = time.perf_counter()
        for _ in range(num_chunks):
            chunk_start = time.perf_counter()
            vad_processor.process_chunk(audio_data)
            times.append((time.perf_counter() - chunk_start) * 1000)
            
        total_time = time.perf_counter() - start
        
        return BenchmarkResult(
            name="VAD Processing",
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            throughput_chunks_per_sec=num_chunks / total_time,
            cpu_percent=0  # Would need psutil
        )
        
    def benchmark_pipeline(
        self,
        pipeline,
        num_chunks: int = 1000
    ) -> BenchmarkResult:
        """Benchmark full pipeline"""
        
        # Generate test chunks
        chunks = [
            np.random.randint(-32768, 32767, size=self.chunk_samples, dtype=np.int16)
            for _ in range(num_chunks)
        ]
        
        times = []
        
        # Warmup
        for chunk in chunks[:10]:
            pipeline.feed(chunk)
            
        # Benchmark
        start = time.perf_counter()
        for chunk in chunks:
            chunk_start = time.perf_counter()
            pipeline.feed(chunk)
            times.append((time.perf_counter() - chunk_start) * 1000)
            
        total_time = time.perf_counter() - start
        
        return BenchmarkResult(
            name="Full Pipeline",
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            throughput_chunks_per_sec=num_chunks / total_time,
            cpu_percent=0
        )
        
    def run_full_benchmark(
        self,
        vad_processor,
        pipeline
    ) -> Dict[str, BenchmarkResult]:
        """Run complete benchmark suite"""
        return {
            "vad": self.benchmark_vad(vad_processor),
            "pipeline": self.benchmark_pipeline(pipeline)
        }
```

---

## 9. Recommended Library Versions

### 9.1 Core Dependencies

```
# requirements.txt

# Audio Processing
sounddevice>=0.4.6          # Cross-platform audio I/O
soundfile>=0.12.1           # Audio file I/O
librosa>=0.10.1             # Audio analysis (optional)

# VAD
silero-vad>=5.1             # Primary VAD (PyTorch-based)
webrtcvad>=2.0.10           # Fallback VAD
onnxruntime>=1.16.0         # ONNX runtime for Silero (optional)

# Platform-specific
pyaudiowpatch>=1.2.0; platform_system=='Windows'  # WASAPI loopback

# Utilities
numpy>=1.24.0
numba>=0.58.0               # JIT compilation for performance
torch>=2.0.0                # For Silero VAD
torchaudio>=2.0.0           # Audio utilities for PyTorch

# Video Processing
ffmpeg-python>=0.2.0        # FFmpeg wrapper

# Benchmarking
psutil>=5.9.0               # System monitoring

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### 9.2 Development Dependencies

```
# requirements-dev.txt

# Development
black>=23.0.0               # Code formatting
mypy>=1.5.0                 # Type checking
ruff>=0.0.290               # Linting

# Profiling
py-spy>=0.3.14              # Performance profiling
line_profiler>=4.1.0        # Line-by-line profiling

# Documentation
mkdocs>=1.5.0
mkdocstrings>=0.23.0
```

---

## 10. Complete Module Structure

```
audio_processing/
├── __init__.py
├── config.py                 # Configuration classes
├── capture/
│   ├── __init__.py
│   ├── base.py              # Base capture interface
│   ├── windows.py           # WASAPI implementation
│   ├── macos.py             # CoreAudio implementation
│   └── manager.py           # Cross-platform manager
├── vad/
│   ├── __init__.py
│   ├── silero_vad.py        # Silero VAD wrapper
│   ├── webrtc_vad.py        # WebRTC VAD wrapper
│   └── pipeline.py          # VAD pipeline
├── segmentation/
│   ├── __init__.py
│   ├── engine.py            # Segmentation logic
│   └── buffer.py            # Audio buffer management
├── pipeline/
│   ├── __init__.py
│   ├── streaming.py         # Main streaming pipeline
│   ├── async_pipeline.py    # Async support
│   └── optimizations.py     # Performance optimizations
├── testing/
│   ├── __init__.py
│   ├── detection.py         # Audio detection tests
│   └── video_extractor.py   # Video audio extraction
├── benchmarking/
│   ├── __init__.py
│   └── performance.py       # Benchmarking tools
└── utils/
    ├── __init__.py
    ├── resampling.py        # Audio resampling
    └── visualization.py     # Visualization helpers
```

---

## 11. Usage Example

```python
# example_usage.py
import numpy as np
from audio_processing import AudioManager, AudioConfig, AudioSource
from audio_processing.vad import SileroVADProcessor
from audio_processing.segmentation import SegmentationEngine
from audio_processing.testing import AudioDetectionTester

def main():
    # 1. Test audio sources
    tester = AudioDetectionTester()
    results = tester.run_all_tests()
    for result in results:
        print(f"{result.test_name}: {'✓' if result.passed else '✗'} {result.message}")
    
    # 2. Initialize audio capture
    config = AudioConfig(sample_rate=16000, chunk_duration_ms=30)
    manager = AudioManager(config)
    manager.initialize(AudioSource.MICROPHONE)
    
    # 3. Initialize VAD
    vad = SileroVADProcessor(
        sample_rate=16000,
        threshold=0.5,
        min_speech_duration_ms=250
    )
    
    # 4. Initialize segmentation
    segmenter = SegmentationEngine()
    
    # 5. Define audio callback
    def on_audio(chunk: np.ndarray):
        # Process through VAD
        segment = vad.process_chunk(chunk)
        if segment:
            print(f"Speech segment: {segment.duration:.2f}s")
            # Send to translation service...
    
    # 6. Start capture
    print("Starting audio capture...")
    manager.start(on_audio)
    
    # Run for 30 seconds
    import time
    time.sleep(30)
    
    # 7. Stop
    manager.stop()
    print("Capture stopped")

if __name__ == "__main__":
    main()
```

---

## 12. Key Recommendations Summary

### VAD Selection
- **Primary**: Silero VAD v5.1 (best accuracy/performance balance)
- **Fallback**: WebRTC VAD (lowest resource usage)
- **Threshold**: 0.5 default, adjustable per environment

### Audio Capture
- **Windows**: WASAPI loopback via pyaudiowpatch
- **macOS**: CoreAudio via sounddevice + BlackHole for loopback
- **Sample Rate**: 16kHz for VAD, 48kHz capture then resample

### Performance Targets
- **Latency**: <100ms end-to-end
- **CPU Usage**: <5% on Apple Silicon M1 Pro
- **Throughput**: >30 chunks/second (30ms chunks)

### Optimization Priority
1. Use ONNX runtime for Silero VAD
2. Implement buffer pooling
3. Use Numba for numerical operations
4. Limit PyTorch threads to 2
5. Enable MPS on Apple Silicon

---

*Document Version: 1.0*
*Last Updated: 2024*
