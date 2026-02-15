# VoiceTranslate Pro - Agent Documentation

> **For AI Coding Agents**: This document provides essential context for working with this codebase.

## Project Overview

**VoiceTranslate Pro** is a real-time voice translation application that enables seamless communication across language barriers. The system supports:

- Real-time speech recognition and translation
- Multi-source audio input (microphone + system audio)
- Hybrid edge/cloud processing modes
- Cross-platform support (Windows, macOS with Apple Silicon optimization)
- 50+ languages with focus on Chinese, English, Japanese, French

### Target Platforms
- Windows 10/11 (x86_64)
- macOS 11.0+ (Apple Silicon M1/M2 and Intel)

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Language** | Python 3.9+ | Minimum version enforced |
| **GUI** | PyQt6 / PySide6 | Microsoft Edge theme style |
| **Audio I/O** | sounddevice, PyAudio | Cross-platform via PortAudio |
| **System Audio** | pyaudiowpatch (Win), BlackHole (macOS) | Platform-specific loopback |
| **VAD** | Silero VAD v5.1 | Primary; WebRTC VAD as fallback |
| **ASR (Edge)** | faster-whisper, whisper.cpp | CTranslate2 backend |
| **ASR (Apple)** | MLX Whisper | Apple Silicon optimized |
| **Translation** | NLLB, MarianMT, ArgosMT | Local edge translation |
| **Video** | FFmpeg, OpenCV | Audio extraction from video |
| **ML Framework** | PyTorch, Transformers | With inference optimizations |

---

## Project Structure

```
workspace_root/
├── interfaces.py                      # Core abstract interfaces and data classes
│                                      # IAudioCapture, IVADEngine, IASREngine, etc.
│
├── example_usage.py                   # Audio module usage examples and demos
│
├── requirements.txt                   # Python dependencies (audio-focused)
│
├── voice_translation/                 # Core translation system
│   ├── main.py                        # CLI entry point with argument parsing
│   └── src/
│       ├── audio/                     # Audio processing components
│       │   ├── processor.py           # Audio preprocessing
│       │   ├── vad.py                 # VAD wrapper and streaming
│       │   └── video.py               # Video audio extraction
│       ├── asr/                       # ASR implementations
│       │   ├── base.py                # Abstract ASR interface
│       │   ├── faster_whisper.py      # faster-whisper integration
│       │   ├── mlx_whisper.py         # Apple Silicon optimized
│       │   └── whisper_cpp.py         # whisper.cpp bindings
│       ├── pipeline/                  # Translation pipelines
│       │   ├── base.py                # Pipeline base class
│       │   ├── realtime.py            # Real-time streaming pipeline
│       │   ├── batch.py               # Batch video processing
│       │   └── hybrid.py              # Edge-cloud hybrid mode
│       └── translation/               # Translation engines
│           ├── base.py                # Abstract translator interface
│           ├── marian.py              # MarianMT implementation
│           └── nllb.py                # NLLB-200 implementation
│
├── audio_module/                      # Audio processing subsystem (standalone)
│   ├── __init__.py                    # Exports: AudioManager, SileroVADProcessor, etc.
│   ├── config.py                      # AudioConfig, AudioSource enums
│   ├── capture/                       # Platform-specific audio capture
│   │   ├── base.py                    # Abstract capture interface
│   │   ├── windows.py                 # WASAPI loopback capture
│   │   ├── macos.py                   # CoreAudio + BlackHole capture
│   │   └── manager.py                 # Cross-platform AudioManager
│   ├── vad/                           # Voice Activity Detection
│   │   ├── silero_vad.py              # Silero VAD processor
│   │   └── webrtc_vad.py              # WebRTC VAD fallback
│   ├── segmentation/                  # Audio segmentation
│   │   └── engine.py                  # SegmentationEngine with config
│   ├── pipeline/                      # Streaming pipeline
│   │   └── streaming.py               # AudioStreamingPipeline, processors
│   ├── video/                         # Video audio extraction
│   │   └── extractor.py               # VideoAudioExtractor using FFmpeg
│   ├── testing/                       # Audio testing utilities
│   │   └── detection.py               # AudioDetectionTester
│   └── benchmarking/                  # Performance benchmarks
│       └── performance.py             # AudioBenchmark suite
│
├── voice_translation_app/             # Full application with packaging
│   ├── setup.py                       # setuptools configuration, py2app for macOS
│   ├── src/
│   │   ├── main.py                    # Application entry point
│   │   ├── platform_utils.py          # Cross-platform utilities and detection
│   │   ├── audio_platform.py          # Unified audio capture wrapper
│   │   └── ml_platform.py             # ML optimization and device selection
│   └── tests/
│       └── test_platform.py           # Unit tests for platform utilities
│
└── docs/                              # Comprehensive documentation
    ├── user-guide.md                  # End-user documentation
    ├── installation.md                # Platform-specific installation
    ├── architecture.md                # System architecture
    ├── api-reference.md               # REST API documentation
    ├── test-plan.md                   # Testing strategy
    └── ...
```

---

## Key Entry Points

### 1. CLI Usage (voice_translation)

```bash
# Real-time translation from microphone
python voice_translation/main.py --mode realtime --source zh --target en

# Batch video translation
python voice_translation/main.py --mode batch -i video.mp4 --source ja --target en

# Hybrid edge-cloud mode
python voice_translation/main.py --mode hybrid -i audio.wav --source fr --target en
```

### 2. Application Usage (voice_translation_app)

```bash
# Run application
python voice_translation_app/src/main.py

# List audio devices
python voice_translation_app/src/main.py --list-devices

# Check dependencies
python voice_translation_app/src/main.py --check-deps

# Capture system audio
python voice_translation_app/src/main.py --system-audio
```

### 3. Audio Module (standalone)

```python
from audio_module import AudioManager, AudioConfig, AudioSource, SileroVADProcessor

config = AudioConfig(sample_rate=16000)
manager = AudioManager(config)
vad = SileroVADProcessor(sample_rate=16000)

# Start capture with callback
def on_audio(chunk):
    segment = vad.process_chunk(chunk)
    if segment:
        print(f"Speech: {segment.duration:.2f}s")

manager.start_capture(AudioSource.MICROPHONE, on_audio)
```

---

## Core Interfaces

All core interfaces are defined in `interfaces.py`. Key abstractions:

### IAudioCapture
```python
class IAudioCapture(ABC):
    def initialize(self, sample_rate=16000, channels=1) -> bool
    def start_capture(self, callback: Callable[[np.ndarray], None]) -> bool
    def stop_capture(self) -> None
    def test_input(self, duration_ms=3000) -> AudioTestResult
```

### IVADEngine
```python
class IVADEngine(ABC):
    def initialize(self, model_path=None, use_gpu=False) -> bool
    def process(self, audio_chunk: np.ndarray, sample_rate=16000) -> VADResult
    def set_threshold(self, threshold: float) -> None
```

### IASREngine
```python
class IASREngine(ABC):
    def initialize(self, config: ASRModelConfig) -> bool
    def transcribe(self, audio_segment: AudioSegment) -> TranscriptionResult
    def get_supported_languages(self) -> List[str]
```

### ITranslator
```python
class ITranslator(ABC):
    def initialize(self, config: TranslationConfig) -> bool
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult
    def detect_language(self, text: str) -> str
```

---

## Build and Package Commands

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode (voice_translation_app)
cd voice_translation_app
pip install -e .
```

### Running Tests

```bash
# Run unit tests (voice_translation_app)
cd voice_translation_app
python -m pytest tests/ -v

# Or run directly
python tests/test_platform.py
```

### Building Application

```bash
# macOS (py2app)
cd voice_translation_app
python setup.py py2app

# Windows (PyInstaller - typical approach)
cd voice_translation_app
pyinstaller --onefile src/main.py
```

---

## Code Style Guidelines

### Python Style
- Follow **PEP 8** style guidelines
- Use **type hints** for function signatures
- Docstrings use **Google-style** format
- Maximum line length: 100 characters

### Example:
```python
def process_audio(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    channels: int = 1
) -> AudioSegment:
    """Process audio data and return segmented result.
    
    Args:
        audio_data: Raw audio samples as numpy array
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels
        
    Returns:
        AudioSegment containing processed audio segment
        
    Raises:
        ValueError: If audio_data is invalid
    """
    # Implementation
```

### Naming Conventions
- **Classes**: PascalCase (`AudioManager`, `SileroVADProcessor`)
- **Functions/Variables**: snake_case (`process_chunk`, `sample_rate`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_SAMPLE_RATE`)
- **Abstract Interfaces**: Start with 'I' (`IAudioCapture`, `IVADEngine`)
- **Private Members**: Leading underscore (`_audio_buffer`, `_process_internal`)

---

## Testing Strategy

### Test Organization
```
voice_translation_app/tests/
└── test_platform.py          # Unit tests for platform utilities
```

### Test Approach
- Use `unittest` framework
- Mock platform-specific dependencies
- Test cross-platform compatibility with mocked platform detection

### Running Tests
```bash
# All tests
python -m pytest voice_translation_app/tests/ -v

# Specific test class
python -m pytest voice_translation_app/tests/test_platform.py::TestPlatformDetection -v
```

---

## Configuration and Constants

### Key Constants (from interfaces.py)

```python
# Supported languages (ISO 639-1)
SUPPORTED_LANGUAGES = {
    "zh": "Chinese",
    "en": "English", 
    "ja": "Japanese",
    "fr": "French"
}

# Default audio parameters
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_CHUNK_DURATION_MS = 30

# Performance targets
TARGET_END_TO_END_LATENCY_MS = 1000
TARGET_VAD_LATENCY_MS = 50
TARGET_ASR_LATENCY_MS = 500
TARGET_TRANSLATION_LATENCY_MS = 200

# Model paths
MODEL_CACHE_DIR = "~/.voice_translate/models"
CONFIG_DIR = "~/.voice_translate/config"
```

### Configuration Files
- No central config file in repository
- Runtime configuration via `IConfigurationManager` interface
- User settings stored in platform-specific directories

---

## Security Considerations

1. **Audio Data**: Audio is processed locally by default (edge mode)
2. **Cloud Mode**: Only sends data to cloud APIs when explicitly enabled
3. **Model Downloads**: Models downloaded from trusted sources (Hugging Face)
4. **Permissions**: Requires microphone access (platform-specific prompts)

---

## Common Tasks for Agents

### Adding a New ASR Engine
1. Create class in `voice_translation/src/asr/` inheriting from `BaseASR`
2. Implement `initialize()` and `transcribe()` methods
3. Register in factory if applicable
4. Update `interfaces.py` ASRFactory if needed

### Adding a New Audio Capture Source
1. Create class in `audio_module/capture/` inheriting from `IAudioCapture`
2. Implement all abstract methods
3. Register in `AudioCaptureFactory` in `interfaces.py`

### Adding a New VAD Engine
1. Create class in `audio_module/vad/` inheriting from `IVADEngine`
2. Implement `process()`, `set_threshold()`, `reset()`
3. Register in `VADFactory` in `interfaces.py`

### Platform-Specific Code
- Use `platform_utils.py` patterns for platform detection
- Use `@macos_only`, `@windows_only` decorators for platform-specific functions
- Keep platform-specific implementations in separate files (e.g., `windows.py`, `macos.py`)

---

## Important Notes

1. **Audio Format**: All internal audio processing uses:
   - Sample rate: 16000 Hz (configurable)
   - Format: numpy float32, range [-1.0, 1.0]
   - Channels: Mono (1 channel) by default

2. **Threading**: Audio capture runs in separate threads
   - Use thread-safe queues for data passing
   - Pipeline uses thread pools for processing

3. **Memory Management**: 
   - Models can be large (Whisper Medium = 769MB)
   - Implement `unload()` methods to free memory
   - Use buffer pooling to reduce GC pressure

4. **Dependencies**: Some dependencies are platform-specific:
   - `pyaudiowpatch` - Windows only
   - `blackhole` - macOS only (external install)

---

## Documentation References

| Document | Description |
|----------|-------------|
| `README.md` | Main project overview |
| `voice_translation_system_architecture.md` | System architecture |
| `audio_processing_subsystem_design.md` | Audio system design |
| `voice_translation_gui_design.md` | GUI design specification |
| `DOCUMENTATION_SUMMARY.md` | Documentation index |
| `docs/` | Full documentation suite |

---

*This file should be updated when significant architectural changes are made.*
