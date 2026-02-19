# VoiceTranslate Pro - Agent Documentation

> **For AI Coding Agents**: This document provides essential context for working with this codebase. The information is based on actual project files and structure.

---

## Project Overview

**VoiceTranslate Pro** (also known as pyLiveTranslator) is a real-time voice translation application that enables seamless communication across language barriers. The system captures audio from microphone or system audio, performs speech recognition (ASR), translates the text, and outputs the translation.

### Key Capabilities

- 🎤 **Real-time Speech Recognition** - Capture and transcribe speech instantly using OpenAI Whisper
- 🔄 **Instant Translation** - Translate between multiple languages using MarianMT/NLLB
- 🖥️ **Multi-source Audio** - Support for microphone and system audio (loopback) capture
- 🌐 **Cross-Platform** - Windows 10/11 and macOS (Apple Silicon optimized)
- 📹 **Video Translation** - Batch video translation with subtitle export
- 🔊 **Voice Activity Detection** - Silero VAD and WebRTC VAD implementations

### Target Platforms

- **Windows**: 10/11 (x86_64) with CUDA support
- **macOS**: 11.0+ (Apple Silicon M1/M2/M3 and Intel)

### Supported Languages

Chinese (zh), English (en), Japanese (ja), French (fr), and 50+ more via translation backends.

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Language** | Python 3.9+ | Minimum version enforced |
| **GUI Framework** | PySide6 | Modern Qt-based GUI |
| **Audio I/O** | sounddevice, PyAudio | Cross-platform via PortAudio |
| **System Audio Capture** | pyaudiowpatch (Win), BlackHole (macOS) | Platform-specific loopback |
| **VAD** | silero-vad, webrtcvad | Silero VAD v5.1 primary |
| **ASR (Edge)** | faster-whisper, whisper.cpp | CTranslate2 backend |
| **ASR (Apple)** | mlx-whisper | Apple Silicon optimized |
| **Translation** | MarianMT, NLLB-200 | Via Hugging Face Transformers |
| **Video Processing** | FFmpeg, ffmpeg-python | Audio extraction from video |
| **ML Framework** | PyTorch 2.0+ | MPS (Apple) / CUDA (Windows) support |
| **Testing** | pytest | Unit and integration tests |
| **Packaging** | setuptools, py2app | macOS app bundle support |

---

## Project Structure

```
pyLiveTranslator_kimi/
├── README.md                    # Main project documentation
├── STATUS.md                    # Current development status
├── .gitignore                   # Git ignore rules
│
├── src/                         # Source code
│   ├── __init__.py
│   ├── core/                    # Core translation system
│   │   ├── asr/                # Automatic Speech Recognition
│   │   │   ├── base.py
│   │   │   ├── faster_whisper.py
│   │   │   ├── mlx_whisper.py
│   │   │   ├── whisper_cpp.py
│   │   │   └── post_processor.py    # ASR hallucination filter
│   │   ├── pipeline/           # Translation pipelines
│   │   │   ├── base.py
│   │   │   ├── realtime.py
│   │   │   ├── batch.py
│   │   │   ├── hybrid.py
│   │   │   ├── orchestrator.py      # Main pipeline orchestrator
│   │   │   └── orchestrator_parallel.py  # Parallel processing
│   │   ├── translation/        # Translation engines
│   │   │   ├── base.py
│   │   │   ├── marian.py
│   │   │   ├── nllb.py
│   │   │   ├── pivot.py
│   │   │   └── cache.py
│   │   ├── configs/            # Configuration files
│   │   │   ├── cloud.yaml
│   │   │   └── edge.yaml
│   │   ├── utils/              # Utility functions
│   │   │   └── latency_analyzer.py
│   │   ├── cli.py              # Core CLI entry
│   │   └── interfaces.py       # Abstract interfaces
│   │
│   ├── audio/                   # Audio processing module
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── capture/            # Audio capture (mic, system audio)
│   │   │   ├── base.py
│   │   │   ├── macos.py
│   │   │   ├── windows.py
│   │   │   └── manager.py
│   │   ├── vad/                # Voice Activity Detection
│   │   │   ├── silero_vad.py
│   │   │   ├── silero_vad_improved.py
│   │   │   ├── silero_vad_adaptive.py
│   │   │   ├── environment_aware_vad.py
│   │   │   └── webrtc_vad.py
│   │   ├── segmentation/       # Audio segmentation
│   │   │   └── engine.py
│   │   ├── pipeline/           # Audio streaming pipeline
│   │   │   └── streaming.py
│   │   ├── video/              # Video audio extraction
│   │   │   └── extractor.py
│   │   ├── benchmarking/       # Performance benchmarks
│   │   │   └── performance.py
│   │   └── testing/            # Audio testing utilities
│   │       └── detection.py
│   │
│   ├── gui/                     # GUI application
│   │   ├── __init__.py
│   │   └── main.py             # Main GUI entry (54KB+)
│   │
│   └── app/                     # Standalone app components
│       ├── __init__.py
│       ├── main.py             # CLI entry point
│       ├── platform_utils.py   # Cross-platform utilities
│       ├── audio_platform.py   # Unified audio capture
│       ├── ml_platform.py      # ML optimization
│       └── config/             # App packaging config
│           ├── entitlements.plist
│           ├── voice-translate-macos.spec
│           └── voice-translate-windows.spec
│
├── cli/                         # Command-line tools
│   ├── vad_visualizer.py       # Real-time VAD GUI visualizer
│   ├── demo_realtime_translation.py
│   ├── demo_video_translation.py
│   └── benchmark_translation.py
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_platform.py        # Platform utility tests
│   ├── test_translation.py     # Translation engine tests
│   └── test_vad_simple.py      # VAD functionality tests
│
├── scripts/                     # Setup and utility scripts
│   ├── setup_environment.py    # Environment setup
│   ├── example_usage.py        # Usage examples
│   └── analyze_overlap.py      # Overlap analysis
│
├── docs/                        # Documentation
│   ├── AGENTS.md               # Existing agent docs (older)
│   ├── architecture/           # Architecture documents
│   │   ├── voice_translation_system_architecture.md
│   │   ├── audio_processing_subsystem_design.md
│   │   └── AUDIO_SUBSYSTEM_SUMMARY.md
│   ├── design/                 # Design documents
│   │   ├── voice_translation_design.md
│   │   ├── voice_translation_gui_design.md
│   │   └── asr-post-processing-design.md
│   ├── guides/                 # Implementation guides
│   │   ├── SETUP_GUIDE.md
│   │   ├── ADAPTIVE_VAD_IMPLEMENTATION.md
│   │   ├── PARALLEL_PIPELINE_GUIDE.md
│   │   └── LATENCY_ANALYSIS_GUIDE.md
│   ├── installation.md
│   ├── test-plan.md
│   ├── troubleshooting.md
│   └── user-guide.md
│
├── config/                      # Configuration files
│   ├── requirements/
│   │   └── requirements.txt    # Core audio requirements
│   └── environments/
│       ├── macos-arm64.yml     # Conda env for macOS
│       └── windows.yml         # Conda env for Windows
│
└── assets/                      # Static assets
    └── icon.icns               # App icon
```

---

## Key Entry Points

### 1. Main Application (Cross-Platform)

```bash
# Run the cross-platform application
python src/app/main.py

# List audio devices
python src/app/main.py --list-devices

# Check dependencies
python src/app/main.py --check-deps

# Use specific audio device
python src/app/main.py --device 4

# Capture system audio
python src/app/main.py --system-audio

# Verbose logging
python src/app/main.py --verbose
```

### 2. GUI Application

```bash
# Launch PySide6 GUI
python src/gui/main.py
```

### 3. CLI Tools

```bash
# VAD Visualizer (GUI with real-time audio meter)
python cli/vad_visualizer.py

# Real-time translation demo
python cli/demo_realtime_translation.py

# Video translation with subtitle export
python cli/demo_video_translation.py video.mp4 --source en --target zh --export-srt

# Performance benchmark
python cli/benchmark_translation.py
```

### 4. Core Pipeline (Programmatic)

```python
from src.core.pipeline.orchestrator import TranslationPipeline, PipelineConfig

config = PipelineConfig(
    source_language="ja",
    target_language="en",
    asr_model_size="base",
    audio_source=AudioSource.MICROPHONE
)

pipeline = TranslationPipeline(config)
pipeline.start()
```

---

## Build and Test Commands

### Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies (platform-specific)
pip install -r config/requirements/requirements.txt

# Or use Conda environment (recommended)
conda env create -f config/environments/macos-arm64.yml  # macOS
conda env create -f config/environments/windows.yml      # Windows
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_vad_simple.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run VAD test with device selection
python tests/test_vad_simple.py --device 4 --duration 30

# List audio devices
python tests/test_vad_simple.py --list
```

### Building Application

```bash
# Install in development mode
pip install -e src/app/setup.py

# Build macOS app bundle (py2app)
cd src/app
python setup.py py2app

# Build Windows executable (PyInstaller)
pyinstaller src/app/config/voice-translate-windows.spec
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

- Use `src/app/platform_utils.py` patterns for platform detection
- Use decorators: `@macos_only`, `@windows_only`, `@apple_silicon_only`
- Keep platform-specific implementations in separate files (`macos.py`, `windows.py`)

---

## Testing Instructions

### Test Organization

```
tests/
├── test_platform.py          # Platform utility tests
├── test_translation.py       # Translation engine tests  
└── test_vad_simple.py        # VAD functionality tests
```

### Running Tests

```bash
# Run unit tests
pytest tests/ -v

# Run VAD test with audio capture
python tests/test_vad_simple.py --device 4 --duration 30

# Run platform tests
python tests/test_platform.py
```

### Verification Tools

```bash
# GUI visualizer with real-time audio meter and VAD graph
python cli/vad_visualizer.py

# Simple CLI test that saves captured speech segments
python tests/test_vad_simple.py --device 4 --duration 30

# List available audio devices
python tests/test_vad_simple.py --list
```

---

## Configuration

### Key Constants

```python
# Default audio parameters
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_CHUNK_DURATION_MS = 30

# VAD parameters
DEFAULT_VAD_THRESHOLD = 0.5
max_segment_duration_ms = 8000  # Max segment before forced split

# Performance targets
TARGET_END_TO_END_LATENCY_MS = 1000
TARGET_ASR_LATENCY_MS = 500
TARGET_TRANSLATION_LATENCY_MS = 200

# Model cache directory
MODEL_CACHE_DIR = "~/.voice_translate/models"
```

### Pipeline Configuration

```python
from src.core.pipeline.orchestrator import PipelineConfig

config = PipelineConfig(
    sample_rate=16000,
    vad_threshold=0.35,
    min_speech_duration_ms=250,
    min_silence_duration_ms=400,
    max_segment_duration_ms=8000,
    asr_model_size="base",  # or "tiny", "small"
    source_language="ja",
    target_language="en",
    translator_type="marian",  # or "nllb"
    enable_translation_cache=True
)
```

### Configuration Files

- `src/core/configs/cloud.yaml` - Cloud processing configuration
- `src/core/configs/edge.yaml` - Edge processing configuration
- `src/app/config/entitlements.plist` - macOS app entitlements

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceTranslate Pro                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   GUI Layer  │  │  CLI Tools   │  │  API Layer   │      │
│  │  (PySide6)   │  │  (Click)     │  │  (FastAPI)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│  ┌──────┴─────────────────┴─────────────────┴───────┐      │
│  │              Core Translation Engine               │      │
│  ├───────────────────────────────────────────────────┤      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │      │
│  │  │   ASR    │  │    MT    │  │   TTS    │        │      │
│  │  │ (Whisper)│  │(Marian/  │  │ (Future) │        │      │
│  │  │          │  │  NLLB)   │  │          │        │      │
│  │  └──────────┘  └──────────┘  └──────────┘        │      │
│  └───────────────────────────────────────────────────┘      │
│         │                 │                 │               │
│  ┌──────┴─────────────────┴─────────────────┴───────┐      │
│  │              Audio Processing Layer                │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │      │
│  │  │  Capture │  │   VAD    │  │  Segment │        │      │
│  │  │(Mic/Sys) │  │(Silero)  │  │ (Engine) │        │      │
│  │  └──────────┘  └──────────┘  └──────────┘        │      │
│  └───────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Flow

1. **Audio Capture** → Raw audio from microphone or system audio
2. **VAD Processing** → Detect speech segments
3. **ASR (Speech-to-Text)** → Transcribe using faster-whisper
4. **Post-Processing** → Filter hallucinations, normalize text
5. **Translation** → Translate using MarianMT/NLLB
6. **Output** → Display and/or text-to-speech

---

## Security Considerations

1. **Audio Data**: Audio is processed locally by default (edge mode)
2. **Cloud Mode**: Only sends data to cloud APIs when explicitly enabled
3. **Model Downloads**: Models downloaded from trusted sources (Hugging Face)
4. **Permissions**: Requires microphone access (platform-specific prompts)
5. **macOS App Sandboxing**: `entitlements.plist` configures sandbox permissions

---

## Important Notes

1. **Audio Format**: All internal audio processing uses:
   - Sample rate: 16000 Hz
   - Format: numpy float32 or int16
   - Channels: Mono (1 channel) by default

2. **Threading**: Audio capture runs in separate threads
   - Use thread-safe queues for data passing
   - Pipeline uses thread pools for processing

3. **Memory Management**:
   - Models can be large (Whisper Medium = 769MB)
   - Implement `unload()` methods to free memory
   - Use buffer pooling to reduce GC pressure

4. **Platform-Specific Dependencies**:
   - **macOS**: PortAudio (`brew install portaudio`), BlackHole (`brew install blackhole-2ch`)
   - **Windows**: pyaudiowpatch (pip installable)

5. **Python Environment**:
   - Minimum Python 3.9 required
   - Virtual environment strongly recommended
   - PyTorch should be installed with platform-specific index URL

6. **Model Caching**:
   - Models cached at `~/.voice_translate/models/` and `~/.cache/torch/hub/`
   - First run will download models (requires internet)

---

## Documentation References

| Document | Description |
|----------|-------------|
| `README.md` | Main project overview and user guide |
| `STATUS.md` | Current development status and phase tracking |
| `docs/architecture.md` | System architecture details |
| `docs/installation.md` | Platform-specific installation |
| `docs/test-plan.md` | Testing strategy |
| `docs/guides/SETUP_GUIDE.md` | Detailed setup instructions |
| `docs/guides/PARALLEL_PIPELINE_GUIDE.md` | Parallel processing documentation |
| `docs/design/asr-post-processing-design.md` | ASR post-processing design |

---

*This file should be updated when significant architectural changes are made.*
*Last updated: 2026-02-19*
