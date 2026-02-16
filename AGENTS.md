# VoiceTranslate Pro - Agent Documentation

> **For AI Coding Agents**: This document provides essential context for working with this codebase. The information is based on actual project files and structure.

---

## Project Overview

**VoiceTranslate Pro** is a real-time voice translation application that enables seamless communication across language barriers. The system supports:

- Real-time speech recognition and translation
- Multi-source audio input (microphone + system audio via loopback)
- Hybrid edge/cloud processing modes
- Batch video translation with subtitle export
- Cross-platform support (Windows, macOS with Apple Silicon optimization)
- Focus languages: Chinese (zh), English (en), Japanese (ja), French (fr)

### Target Platforms
- Windows 10/11 (x86_64)
- macOS 11.0+ (Apple Silicon M1/M2/M3 and Intel)

### Development Status
As of 2026-02-16: 
- ✅ Phase 1 (Environment Setup) - Complete
- ✅ Phase 2 (Core Audio Pipeline) - Complete (<1ms latency)
- ✅ Phase 3 (ASR Integration) - Complete (faster-whisper)
- ✅ Phase 4 (Translation Engine) - Complete (MarianMT, NLLB-200)
- ✅ Phase 5 (End-to-End Pipeline) - Complete (Pipeline Orchestrator)

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Language** | Python 3.9+ | Minimum version enforced |
| **Audio I/O** | sounddevice, PyAudio | Cross-platform via PortAudio |
| **System Audio** | pyaudiowpatch (Win), BlackHole (macOS) | Platform-specific loopback |
| **VAD** | silero-vad, webrtcvad | Silero VAD v5.1 primary; WebRTC VAD fallback |
| **ASR (Edge)** | openai-whisper, faster-whisper, whisper.cpp | CTranslate2 backend |
| **ASR (Apple)** | mlx-whisper | Apple Silicon optimized (optional) |
| **Translation** | NLLB-200, MarianMT | Via Hugging Face Transformers |
| **Video** | FFmpeg, ffmpeg-python | Audio extraction from video |
| **ML Framework** | PyTorch 2.0+ | With MPS (Apple Silicon) / CUDA (Windows) support |
| **Testing** | pytest, unittest | Unit and integration tests |
| **Packaging** | setuptools, py2app | macOS app bundle support |

---

## Project Structure

```
workspace_root/
├── interfaces.py                      # Core abstract interfaces and data classes
│                                      # IAudioCapture, IVADEngine, IASREngine, ITranslator, etc.
│
├── requirements.txt                   # Core audio module dependencies (sounddevice, silero-vad, etc.)
├── setup_environment.py               # Automated environment setup script with validation
├── example_usage.py                   # Audio module usage examples and demos
│
├── voice_translation/                 # Core translation system (CLI-focused)
│   ├── main.py                        # CLI entry point with argument parsing
│   ├── requirements.txt               # Module-specific requirements
│   └── src/
│       ├── audio/                     # Audio processing components
│       │   ├── processor.py           # Audio preprocessing
│       │   ├── vad.py                 # VAD wrapper and streaming
│       │   └── video.py               # Video audio extraction
│       ├── asr/                       # ASR implementations
│       │   ├── base.py                # Abstract ASR interface
│       │   ├── faster_whisper.py      # faster-whisper integration
│       │   ├── mlx_whisper.py         # Apple Silicon optimized (optional)
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
├── audio_module/                      # Audio processing subsystem (standalone module)
│   ├── __init__.py                    # Exports: AudioManager, SileroVADProcessor, etc.
│   ├── config.py                      # AudioConfig, AudioSource enums
│   ├── capture/                       # Platform-specific audio capture
│   │   ├── base.py                    # Abstract capture interface
│   │   ├── windows.py                 # WASAPI loopback capture (Windows)
│   │   ├── macos.py                   # CoreAudio + BlackHole capture (macOS)
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
├── voice_translation_app/             # Full application with cross-platform support
│   ├── setup.py                       # setuptools configuration, py2app for macOS
│   ├── requirements.txt               # Base requirements
│   ├── requirements-macos-arm64.txt   # macOS Apple Silicon specific
│   ├── requirements-windows.txt       # Windows specific
│   ├── environment-macos-arm64.yml    # Conda environment (macOS)
│   ├── environment-windows.yml        # Conda environment (Windows)
│   ├── config/                        # App configuration files
│   │   └── entitlements.plist         # macOS entitlements for app bundle
│   ├── src/
│   │   ├── main.py                    # Application entry point
│   │   ├── platform_utils.py          # Cross-platform utilities and detection
│   │   ├── audio_platform.py          # Unified audio capture wrapper
│   │   └── ml_platform.py             # ML optimization and device selection
│   └── tests/
│       └── test_platform.py           # Unit tests for platform utilities
│
└── docs/                              # Comprehensive documentation
    ├── architecture.md                # System architecture
    ├── contributing.md                # Contribution guidelines
    ├── gui-documentation.md           # GUI design specification
    ├── installation.md                # Platform-specific installation
    ├── test-plan.md                   # Testing strategy
    ├── troubleshooting.md             # Troubleshooting guide
    ├── user-guide.md                  # End-user documentation
    └── video-testing.md               # Video feature testing
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
python voice_translation/main.py --mode hybrid -i audio.wav --source fr --target en --asr whisper.cpp
```

**CLI Arguments:**
- `--mode`: Processing mode (`realtime`, `batch`, `hybrid`)
- `--source/-s`: Source language (`zh`, `en`, `ja`, `fr`, `auto`)
- `--target/-t`: Target language (`zh`, `en`, `ja`, `fr`)
- `--asr`: ASR implementation (`whisper.cpp`, `faster-whisper`, `mlx-whisper`)
- `--model-size`: Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`, etc.)
- `--device`: Compute device (`auto`, `cpu`, `cuda`, `mps`)
- `--system-audio`: Capture system audio instead of microphone

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

# Verbose logging
python voice_translation_app/src/main.py --verbose
```

### 3. Environment Setup

```bash
# Run automated environment setup
python setup_environment.py

# Skip checks and install all
python setup_environment.py --install-all
```

### 4. Audio Module (standalone)

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

### 5. Examples

```bash
# Run interactive examples
python example_usage.py
```

---

## Build and Package Commands

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies (platform-specific)
pip install -r voice_translation_app/requirements-macos-arm64.txt  # macOS Apple Silicon
pip install -r voice_translation_app/requirements-windows.txt      # Windows
pip install -r requirements.txt                                    # Core only

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

# Run all tests with coverage
pytest --cov=voice_translation_app --cov-report=html
```

### Building Application

```bash
# macOS (py2app)
cd voice_translation_app
python setup.py py2app

# Windows (PyInstaller - typical approach, not yet configured)
cd voice_translation_app
pyinstaller --onefile src/main.py
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
    def get_available_devices(self) -> List[DeviceInfo]
```

### IVADEngine
```python
class IVADEngine(ABC):
    def initialize(self, model_path=None, use_gpu=False) -> bool
    def process(self, audio_chunk: np.ndarray, sample_rate=16000) -> VADResult
    def set_threshold(self, threshold: float) -> None
    def reset(self) -> None
```

### IASREngine
```python
class IASREngine(ABC):
    def initialize(self, config: ASRModelConfig) -> bool
    def transcribe(self, audio_segment: AudioSegment) -> TranscriptionResult
    def get_supported_languages(self) -> List[str]
    def unload(self) -> None  # Free memory
```

### ITranslator
```python
class ITranslator(ABC):
    def initialize(self, config: TranslationConfig) -> bool
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult
    def detect_language(self, text: str) -> str
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

### Platform-Specific Code
- Use `platform_utils.py` patterns for platform detection
- Use `@macos_only`, `@windows_only`, `@apple_silicon_only` decorators
- Keep platform-specific implementations in separate files (e.g., `windows.py`, `macos.py`)

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
- Run with: `python -m pytest voice_translation_app/tests/ -v`

### Test Classes in test_platform.py:
- `TestPlatformDetection` - Platform type detection
- `TestPlatformInfo` - PlatformInfo dataclass
- `TestPlatformDecorators` - @macos_only, @windows_only decorators
- `TestPlatformPaths` - Cross-platform path management
- `TestAudioPlatformHelper` - Audio settings per platform
- `TestDependencyChecker` - Dependency validation
- `TestCrossPlatformCompatibility` - General compatibility

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

# VAD parameters
DEFAULT_VAD_THRESHOLD = 0.5
DEFAULT_VAD_FRAME_MS = 30

# Performance targets
TARGET_END_TO_END_LATENCY_MS = 1000
TARGET_VAD_LATENCY_MS = 50
TARGET_ASR_LATENCY_MS = 500
TARGET_TRANSLATION_LATENCY_MS = 200

# Model URLs and paths
MODEL_CACHE_DIR = "~/.voice_translate/models"
CONFIG_DIR = "~/.voice_translate/config"
LOG_DIR = "~/.voice_translate/logs"

# Whisper model URLs (from Hugging Face)
WHISPER_MODEL_URLS = {
    "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
    "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
    "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
}
```

### Configuration Files
- `voice_translation_app/config/entitlements.plist` - macOS app entitlements
- `voice_translation_app/config/` - Other app configuration files
- No central runtime config file in repository (runtime config via `IConfigurationManager`)

---

## Security Considerations

1. **Audio Data**: Audio is processed locally by default (edge mode)
2. **Cloud Mode**: Only sends data to cloud APIs when explicitly enabled
3. **Model Downloads**: Models downloaded from trusted sources (Hugging Face)
4. **Permissions**: Requires microphone access (platform-specific prompts)
5. **macOS App Sandboxing**: `entitlements.plist` configures sandbox permissions

---

## Common Tasks for Agents

### Adding a New ASR Engine
1. Create class in `voice_translation/src/asr/` inheriting from `BaseASR`
2. Implement `initialize()` and `transcribe()` methods
3. Add to `voice_translation/src/asr/__init__.py` exports
4. Update CLI in `voice_translation/main.py` to support the new engine

### Adding a New Audio Capture Source
1. Create class in `audio_module/capture/` inheriting from `IAudioCapture` (or base.py)
2. Implement all abstract methods
3. Register in `AudioCaptureFactory` in `interfaces.py` if needed
4. Update `audio_module/capture/manager.py` if cross-platform support needed

### Adding a New VAD Engine
1. Create class in `audio_module/vad/` inheriting from `IVADEngine`
2. Implement `process()`, `set_threshold()`, `reset()`
3. Register in `VADFactory` in `interfaces.py`
4. Add to `audio_module/__init__.py` exports

### Adding Platform-Specific Code
1. Use decorators from `platform_utils.py`:
   - `@macos_only` - macOS only functions
   - `@windows_only` - Windows only functions
   - `@apple_silicon_only` - Apple Silicon specific
2. Keep implementations in platform-specific files (`macos.py`, `windows.py`)
3. Use `detect_platform()` to check current platform at runtime

---

## Important Notes

1. **Audio Format**: All internal audio processing uses:
   - Sample rate: 16000 Hz (configurable, but 16kHz is standard)
   - Format: numpy float32, range [-1.0, 1.0] OR int16 depending on component
   - Channels: Mono (1 channel) by default

2. **Threading**: Audio capture runs in separate threads
   - Use thread-safe queues for data passing
   - Pipeline uses thread pools for processing

3. **Memory Management**:
   - Models can be large (Whisper Medium = 769MB)
   - Implement `unload()` methods to free memory
   - Use buffer pooling to reduce GC pressure

4. **Platform-Specific Dependencies**:
   - **macOS**: PortAudio (via Homebrew: `brew install portaudio`), BlackHole (`brew install blackhole-2ch`)
   - **Windows**: pyaudiowpatch (pip installable)

5. **Python Environment**:
   - Minimum Python 3.9 required
   - Virtual environment strongly recommended
   - PyTorch should be installed with platform-specific index URL for CUDA/MPS support

6. **Model Caching**:
   - Models cached at `~/.voice_translate/models/` and `~/.cache/torch/hub/`
   - First run will download models (requires internet)

---

## Documentation References

| Document | Description |
|----------|-------------|
| `README.md` | Main project overview and user guide |
| `STATUS.md` | Current development status and phase tracking |
| `SETUP_GUIDE.md` | Detailed environment setup instructions |
| `DOCUMENTATION_SUMMARY.md` | Index of all documentation |
| `AUDIO_SUBSYSTEM_SUMMARY.md` | Audio module documentation |
| `voice_translation_system_architecture.md` | Detailed system architecture |
| `audio_processing_subsystem_design.md` | Audio system design |
| `voice_translation_gui_design.md` | GUI design specification |
| `voice_translation_design.md` | Translation system design |
| `docs/architecture.md` | Architecture details |
| `docs/installation.md` | Platform-specific installation |
| `docs/test-plan.md` | Testing strategy |

---

*This file should be updated when significant architectural changes are made.*
*Last updated: 2026-02-16*
