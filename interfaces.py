"""
Real-Time Voice Translation System - Core Interfaces
====================================================

This module defines all abstract interfaces and data structures
for the voice translation application.

Target Platforms: Windows, macOS (Apple Silicon M1 Pro)
Supported Languages: Chinese, English, Japanese, French
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import numpy as np
from datetime import datetime


# ============================================================================
# ENUMERATIONS
# ============================================================================

class EventType(Enum):
    """Event types for the event bus system"""
    # Audio events
    AUDIO_CAPTURE_STARTED = auto()
    AUDIO_CAPTURE_STOPPED = auto()
    AUDIO_CHUNK_RECEIVED = auto()
    AUDIO_LEVEL_CHANGED = auto()
    
    # VAD events
    VAD_VOICE_DETECTED = auto()
    VAD_VOICE_ENDED = auto()
    VAD_STATE_CHANGED = auto()
    
    # Segmentation events
    SEGMENT_CREATED = auto()
    SEGMENT_QUEUE_UPDATED = auto()
    SEGMENT_PROCESSING_STARTED = auto()
    
    # ASR events
    ASR_TRANSCRIPTION_STARTED = auto()
    ASR_TRANSCRIPTION_COMPLETE = auto()
    ASR_TRANSCRIPTION_FAILED = auto()
    
    # Translation events
    TRANSLATION_STARTED = auto()
    TRANSLATION_COMPLETE = auto()
    TRANSLATION_FAILED = auto()
    
    # UI events
    UI_SETTINGS_CHANGED = auto()
    UI_THEME_CHANGED = auto()
    UI_LANGUAGE_CHANGED = auto()
    
    # Performance events
    PERFORMANCE_METRICS_UPDATED = auto()
    BENCHMARK_COMPLETE = auto()
    
    # System events
    SYSTEM_ERROR = auto()
    SYSTEM_WARNING = auto()


class ProcessingMode(Enum):
    """Processing mode for ASR and translation"""
    EDGE_ONLY = "edge"           # Local processing only
    CLOUD_ONLY = "cloud"         # Cloud processing only
    HYBRID = "hybrid"            # Edge first, cloud fallback
    AUTO = "auto"                # Automatic selection


class AudioSourceType(Enum):
    """Types of audio input sources"""
    MICROPHONE = "microphone"
    SYSTEM_AUDIO = "system_audio"
    FILE = "file"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class AudioTestResult:
    """Result of audio input test"""
    success: bool
    source_type: AudioSourceType
    sample_rate: int
    channels: int
    duration_tested: float
    average_level: float
    peak_level: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VADResult:
    """Result from Voice Activity Detection"""
    is_speech: bool
    confidence: float
    speech_probability: float
    timestamp: float
    audio_level: float = 0.0


@dataclass
class AudioSegment:
    """Represents a segmented piece of audio containing speech"""
    audio_data: np.ndarray
    start_time: float
    end_time: float
    duration: float
    sample_rate: int
    confidence: float
    source: AudioSourceType = AudioSourceType.MICROPHONE
    
    def __post_init__(self):
        if self.duration == 0 and self.sample_rate > 0:
            self.duration = len(self.audio_data) / self.sample_rate


@dataclass
class TranscriptionSegment:
    """A single segment of transcription with timing"""
    start: float
    end: float
    text: str
    confidence: float
    words: Optional[List[Dict[str, Any]]] = None


@dataclass
class TranscriptionResult:
    """Result from Automatic Speech Recognition"""
    text: str
    confidence: float
    language: str
    language_probability: float
    segments: List[TranscriptionSegment]
    processing_time: float
    model_used: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class TranslationResult:
    """Result from translation engine"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    processing_time: float
    engine_used: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class LanguagePair:
    """Supported language pair for translation"""
    source: str
    target: str
    source_name: str
    target_name: str
    supported: bool = True


@dataclass
class SegmentationConfig:
    """Configuration for audio segmentation"""
    min_segment_duration: float = 1.0      # Minimum segment length (seconds)
    max_segment_duration: float = 30.0     # Maximum segment length (seconds)
    padding_before: float = 0.3            # Padding before speech (seconds)
    padding_after: float = 0.5             # Padding after speech (seconds)
    silence_threshold: float = 0.5         # Silence duration to split (seconds)
    energy_threshold: float = 0.01         # Energy threshold for speech detection


@dataclass
class ASRModelConfig:
    """Configuration for ASR model"""
    model_name: str = "base"               # tiny, base, small, medium, large
    model_path: Optional[str] = None
    device: str = "cpu"                    # cpu, cuda, mps (Apple Silicon)
    compute_type: str = "int8"             # int8, float16, float32
    language: Optional[str] = None         # Auto-detect if None
    beam_size: int = 5
    best_of: int = 5
    patience: float = 1.0
    length_penalty: float = 1.0
    temperature: float = 0.0
    compression_ratio_threshold: float = 2.4
    logprob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    condition_on_previous_text: bool = True
    initial_prompt: Optional[str] = None


@dataclass
class TranslationConfig:
    """Configuration for translation engine"""
    engine: str = "argos"                  # argos, opus, cloud
    model_path: Optional[str] = None
    beam_size: int = 5
    max_length: int = 512
    temperature: float = 0.0
    top_k: int = 50
    top_p: float = 0.9


@dataclass
class PerformanceMetrics:
    """Performance metrics for a module"""
    module_name: str
    cpu_percent: float
    memory_mb: float
    latency_ms: float
    throughput: float
    timestamp: float


@dataclass
class BenchmarkResult:
    """Result from performance benchmark"""
    module_name: str
    duration_ms: float
    cpu_percent: float
    memory_mb: int
    timestamp: float
    iterations: int = 1


@dataclass
class LatencyStats:
    """Latency statistics for a module"""
    module_name: str
    min_ms: float
    max_ms: float
    avg_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int


@dataclass
class Event:
    """Event for the event bus system"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: float
    source: str


@dataclass
class Subscription:
    """Subscription to event bus"""
    event_type: EventType
    callback: Callable[[Event], None]
    subscription_id: str


@dataclass
class DeviceInfo:
    """Audio device information"""
    device_id: Union[int, str]
    name: str
    channels_input: int
    channels_output: int
    sample_rate: int
    is_default: bool = False
    is_loopback: bool = False


# ============================================================================
# ABSTRACT INTERFACES
# ============================================================================

class IAudioCapture(ABC):
    """
    Abstract interface for audio capture sources.
    
    Implementations:
    - MicrophoneCapture: Capture from physical microphone
    - SystemAudioCapture: Capture system audio output (loopback)
    - FileAudioCapture: Capture from audio file
    """
    
    @abstractmethod
    def initialize(self, sample_rate: int = 16000, channels: int = 1,
                   device_id: Optional[Union[int, str]] = None) -> bool:
        """
        Initialize the audio capture device.
        
        Args:
            sample_rate: Target sample rate (Hz)
            channels: Number of channels (1 for mono, 2 for stereo)
            device_id: Specific device ID (None for default)
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def start_capture(self, callback: Callable[[np.ndarray], None]) -> bool:
        """
        Start capturing audio with callback for each chunk.
        
        Args:
            callback: Function to call with each audio chunk (numpy array)
            
        Returns:
            True if capture started successfully
        """
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop audio capture."""
        pass
    
    @abstractmethod
    def is_capturing(self) -> bool:
        """Check if currently capturing audio."""
        pass
    
    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """Return current device information."""
        pass
    
    @abstractmethod
    def test_input(self, duration_ms: int = 3000) -> AudioTestResult:
        """
        Test if input source is working properly.
        
        Args:
            duration_ms: Duration of test in milliseconds
            
        Returns:
            AudioTestResult with test results
        """
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[DeviceInfo]:
        """Return list of available audio devices."""
        pass
    
    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """
        Set capture volume (0.0 to 1.0).
        
        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (max)
        """
        pass


class IVADEngine(ABC):
    """
    Abstract interface for Voice Activity Detection engines.
    
    Implementations:
    - SileroVAD: PyTorch-based, high accuracy
    - WebRTCVAD: Lightweight, fast
    - EnergyBasedVAD: Simple threshold-based
    """
    
    @abstractmethod
    def initialize(self, model_path: Optional[str] = None,
                   use_gpu: bool = False) -> bool:
        """
        Initialize VAD engine with optional model.
        
        Args:
            model_path: Path to custom model (None for default)
            use_gpu: Whether to use GPU acceleration
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def process(self, audio_chunk: np.ndarray,
                sample_rate: int = 16000) -> VADResult:
        """
        Process audio chunk and return voice activity detection result.
        
        Args:
            audio_chunk: Audio data as numpy array (float32, -1.0 to 1.0)
            sample_rate: Sample rate of audio (must be 8000, 16000, 32000, or 48000)
            
        Returns:
            VADResult with detection results
        """
        pass
    
    @abstractmethod
    def set_threshold(self, threshold: float) -> None:
        """
        Set voice detection threshold.
        
        Args:
            threshold: Threshold from 0.0 to 1.0 (higher = less sensitive)
        """
        pass
    
    @abstractmethod
    def get_threshold(self) -> float:
        """Get current voice detection threshold."""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (call when starting new session)."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return engine name for display."""
        pass


class IAudioSegmenter(ABC):
    """
    Abstract interface for audio segmentation engines.
    
    Segments continuous audio into discrete speech segments based on
    VAD results and timing parameters.
    """
    
    @abstractmethod
    def initialize(self, config: SegmentationConfig) -> bool:
        """
        Initialize segmenter with configuration.
        
        Args:
            config: Segmentation configuration parameters
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def feed_audio(self, audio_chunk: np.ndarray,
                   vad_result: VADResult) -> Optional[AudioSegment]:
        """
        Feed audio chunk and VAD result.
        
        Args:
            audio_chunk: Audio data as numpy array
            vad_result: VAD detection result for this chunk
            
        Returns:
            AudioSegment if a complete segment is ready, None otherwise
        """
        pass
    
    @abstractmethod
    def flush(self) -> Optional[AudioSegment]:
        """
        Force flush any pending audio as a segment.
        Call when stopping capture to get final segment.
        
        Returns:
            AudioSegment if there's pending audio, None otherwise
        """
        pass
    
    @abstractmethod
    def get_pending_duration(self) -> float:
        """Get duration of pending audio in buffer (seconds)."""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset internal state."""
        pass


class IASREngine(ABC):
    """
    Abstract interface for Automatic Speech Recognition engines.
    
    Implementations:
    - WhisperLocalASR: Local Whisper (whisper.cpp or faster-whisper)
    - WhisperCloudASR: OpenAI Whisper API
    - GoogleCloudASR: Google Cloud Speech-to-Text
    """
    
    @abstractmethod
    def initialize(self, config: ASRModelConfig) -> bool:
        """
        Initialize ASR engine with model configuration.
        
        Args:
            config: ASR model configuration
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def transcribe(self, audio_segment: AudioSegment) -> TranscriptionResult:
        """
        Transcribe audio segment to text.
        
        Args:
            audio_segment: Audio segment containing speech
            
        Returns:
            TranscriptionResult with transcription data
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes (ISO 639-1)."""
        pass
    
    @abstractmethod
    def is_language_supported(self, language_code: str) -> bool:
        """Check if a specific language is supported."""
        pass
    
    @abstractmethod
    def unload(self) -> None:
        """Unload model to free memory."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return model information (name, size, languages, etc.)."""
        pass


class ITranslator(ABC):
    """
    Abstract interface for Translation engines.
    
    Implementations:
    - ArgosTranslator: Local ArgosMT
    - OpusTranslator: Opus-MT with CTranslate2
    - CloudTranslator: Cloud translation APIs
    """
    
    @abstractmethod
    def initialize(self, config: TranslationConfig) -> bool:
        """
        Initialize translator with configuration.
        
        Args:
            config: Translation configuration
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def translate(self, text: str, source_lang: str,
                  target_lang: str) -> TranslationResult:
        """
        Translate text from source to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (ISO 639-1)
            
        Returns:
            TranslationResult with translation data
        """
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.
        
        Args:
            text: Text to analyze
            
        Returns:
            ISO 639-1 language code
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[LanguagePair]:
        """Return list of supported language pairs."""
        pass
    
    @abstractmethod
    def is_pair_supported(self, source_lang: str, target_lang: str) -> bool:
        """Check if a specific language pair is supported."""
        pass


class IPerformanceMonitor(ABC):
    """
    Abstract interface for Performance Monitoring.
    
    Tracks CPU usage, memory consumption, and latency for all modules.
    """
    
    @abstractmethod
    def start_benchmark(self, module_name: str) -> str:
        """
        Start benchmarking a module.
        
        Args:
            module_name: Name of module to benchmark
            
        Returns:
            Benchmark ID for ending the benchmark
        """
        pass
    
    @abstractmethod
    def end_benchmark(self, benchmark_id: str) -> BenchmarkResult:
        """
        End benchmarking and return results.
        
        Args:
            benchmark_id: Benchmark ID from start_benchmark
            
        Returns:
            BenchmarkResult with metrics
        """
        pass
    
    @abstractmethod
    def get_cpu_usage(self) -> Dict[str, float]:
        """
        Get CPU usage by module.
        
        Returns:
            Dictionary mapping module names to CPU percentage
        """
        pass
    
    @abstractmethod
    def get_memory_usage(self) -> Dict[str, int]:
        """
        Get memory usage by module (in MB).
        
        Returns:
            Dictionary mapping module names to memory in MB
        """
        pass
    
    @abstractmethod
    def get_latency_report(self) -> Dict[str, LatencyStats]:
        """
        Get latency statistics by module.
        
        Returns:
            Dictionary mapping module names to LatencyStats
        """
        pass
    
    @abstractmethod
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get overall system metrics.
        
        Returns:
            Dictionary with system-wide metrics
        """
        pass


class IEventBus(ABC):
    """
    Abstract interface for Event Bus (Pub/Sub system).
    
    Enables loose coupling between modules through event-driven communication.
    """
    
    @abstractmethod
    def subscribe(self, event_type: EventType,
                  callback: Callable[[Event], None]) -> Subscription:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            
        Returns:
            Subscription object for unsubscribing
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription: Subscription) -> None:
        """
        Unsubscribe from events.
        
        Args:
            subscription: Subscription object from subscribe()
        """
        pass
    
    @abstractmethod
    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
        """
        pass
    
    @abstractmethod
    def publish_sync(self, event: Event) -> None:
        """
        Publish an event synchronously (blocking).
        
        Args:
            event: Event to publish
        """
        pass


class IConfigurationManager(ABC):
    """
    Abstract interface for Configuration Management.
    
    Handles persistence and retrieval of application settings.
    """
    
    @abstractmethod
    def load_config(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from storage."""
        pass
    
    @abstractmethod
    def save_config(self, config: Dict[str, Any],
                    profile_name: Optional[str] = None) -> bool:
        """Save configuration to storage."""
        pass
    
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        pass
    
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        pass
    
    @abstractmethod
    def get_profiles(self) -> List[str]:
        """Get list of available profiles."""
        pass


# ============================================================================
# FACTORY CLASSES
# ============================================================================

class VADFactory:
    """Factory for creating VAD engine instances"""
    
    @staticmethod
    def create(engine_type: str, **kwargs) -> IVADEngine:
        """
        Create a VAD engine instance.
        
        Args:
            engine_type: Type of VAD engine ("silero", "webrtc", "energy")
            **kwargs: Additional arguments for the engine
            
        Returns:
            IVADEngine instance
        """
        # Import implementations here to avoid circular imports
        if engine_type == "silero":
            from processing.vad.silero_vad import SileroVAD
            return SileroVAD(**kwargs)
        elif engine_type == "webrtc":
            from processing.vad.webrtc_vad import WebRTCVAD
            return WebRTCVAD(**kwargs)
        elif engine_type == "energy":
            from processing.vad.energy_vad import EnergyBasedVAD
            return EnergyBasedVAD(**kwargs)
        else:
            raise ValueError(f"Unknown VAD engine type: {engine_type}")


class ASRFactory:
    """Factory for creating ASR engine instances"""
    
    @staticmethod
    def create(engine_type: str, **kwargs) -> IASREngine:
        """
        Create an ASR engine instance.
        
        Args:
            engine_type: Type of ASR engine ("whisper_local", "whisper_cloud")
            **kwargs: Additional arguments for the engine
            
        Returns:
            IASREngine instance
        """
        if engine_type == "whisper_local":
            from processing.asr.whisper_local import WhisperLocalASR
            return WhisperLocalASR(**kwargs)
        elif engine_type == "whisper_cloud":
            from processing.asr.whisper_cloud import WhisperCloudASR
            return WhisperCloudASR(**kwargs)
        else:
            raise ValueError(f"Unknown ASR engine type: {engine_type}")


class TranslatorFactory:
    """Factory for creating Translator engine instances"""
    
    @staticmethod
    def create(engine_type: str, **kwargs) -> ITranslator:
        """
        Create a Translator engine instance.
        
        Args:
            engine_type: Type of translator ("argos", "opus", "cloud")
            **kwargs: Additional arguments for the engine
            
        Returns:
            ITranslator instance
        """
        if engine_type == "argos":
            from processing.translation.argos_translator import ArgosTranslator
            return ArgosTranslator(**kwargs)
        elif engine_type == "opus":
            from processing.translation.opus_translator import OpusTranslator
            return OpusTranslator(**kwargs)
        elif engine_type == "cloud":
            from processing.translation.cloud_translator import CloudTranslator
            return CloudTranslator(**kwargs)
        else:
            raise ValueError(f"Unknown translator engine type: {engine_type}")


class AudioCaptureFactory:
    """Factory for creating Audio Capture instances"""
    
    @staticmethod
    def create(source_type: AudioSourceType, **kwargs) -> IAudioCapture:
        """
        Create an audio capture instance.
        
        Args:
            source_type: Type of audio source
            **kwargs: Additional arguments for the capture
            
        Returns:
            IAudioCapture instance
        """
        if source_type == AudioSourceType.MICROPHONE:
            from audio.microphone_capture import MicrophoneCapture
            return MicrophoneCapture(**kwargs)
        elif source_type == AudioSourceType.SYSTEM_AUDIO:
            from audio.system_capture import SystemAudioCapture
            return SystemAudioCapture(**kwargs)
        elif source_type == AudioSourceType.FILE:
            from audio.file_capture import FileAudioCapture
            return FileAudioCapture(**kwargs)
        else:
            raise ValueError(f"Unknown audio source type: {source_type}")


# ============================================================================
# CONSTANTS
# ============================================================================

# Supported languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "fr": "French"
}

# Default audio parameters
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_CHUNK_DURATION_MS = 30  # 30ms chunks for VAD

# VAD parameters
DEFAULT_VAD_THRESHOLD = 0.5
DEFAULT_VAD_FRAME_MS = 30

# Performance targets
TARGET_END_TO_END_LATENCY_MS = 1000
TARGET_VAD_LATENCY_MS = 50
TARGET_ASR_LATENCY_MS = 500
TARGET_TRANSLATION_LATENCY_MS = 200

# Model URLs and paths
WHISPER_MODEL_URLS = {
    "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
    "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
    "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
}

# File paths
MODEL_CACHE_DIR = "~/.voice_translate/models"
CONFIG_DIR = "~/.voice_translate/config"
LOG_DIR = "~/.voice_translate/logs"
