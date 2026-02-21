# VoiceTranslate Pro - Agent Documentation

> **For AI Coding Agents**: This document provides essential context for working with this codebase. The information is based on actual project files and structure.

---

## Project Overview

**VoiceTranslate Pro** (also known as pyLiveTranslator) is a production-ready real-time voice translation application featuring streaming translation with draft/final modes. Version 2.0.0+ supports English, Chinese (Simplified/Traditional), Japanese, and French with hardware acceleration and Docker deployment.

### Key Capabilities

- 🎤 **Streaming Translation** - Draft previews every 2s, final translation on silence
- 🔄 **Multi-Language** - EN, ZH, JA with optimized MarianMT models
- ⚡ **Low Latency** - TTFT ~1.5s, Meaning Latency ~1.8s
- 🎛️ **Multiple Modes** - Standard, Interview (documentary), Sentence modes
- 🎙️ **Mic Selection** - GUI dropdown + CLI support
- 🐳 **Docker Ready** - Production deployment with Prometheus/Grafana
- 🖥️ **Cross-Platform** - Windows, macOS (Apple Silicon optimized), Linux

### Target Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| macOS 11+ | ✅ Fully Supported | Apple Silicon M1/M2/M3 optimized (MPS backend) |
| Windows 10/11 | ✅ Fully Supported | x86_64 with CUDA/OpenVINO support |
| Linux | ✅ Supported | Primary for Docker deployment |

### Supported Languages

| Language | Code | ASR | Translation | Quality |
|----------|------|-----|-------------|---------|
| English | en | ✅ | ✅ | Excellent |
| Chinese (Simplified) | zh | ✅ | ✅ | Good |
| Chinese (Traditional) | zh-TW | ✅ | ✅ | Good |
| Japanese | ja | ✅ | ✅ | Good |
| French | fr | ✅ | ✅ | Good |

---

## Technology Stack

| Component | Technology | Version/Notes |
|-----------|------------|---------------|
| **Language** | Python | 3.9+ required, 3.11 recommended |
| **GUI Framework** | PySide6 | Qt-based GUI |
| **ASR** | faster-whisper | CTranslate2 backend, int8 quantization |
| **ASR (Apple)** | mlx-whisper | Apple Silicon optimized |
| **Translation** | MarianMT | Helsinki-NLP models |
| **VAD** | Silero VAD v5.1 | Primary voice detection |
| **VAD (Fallback)** | WebRTC VAD | Lightweight alternative |
| **Audio I/O** | sounddevice, PyAudio | PortAudio backend |
| **System Audio** | pyaudiowpatch (Win), BlackHole (macOS) | Loopback capture |
| **ML Framework** | PyTorch 2.0+ | MPS (Apple) / CUDA (NVIDIA) |
| **Hardware Opt** | OpenVINO, CoreML | Intel/Apple acceleration |
| **Backend API** | FastAPI | Optional REST API |
| **Monitoring** | Prometheus, Grafana | Metrics and dashboards |
| **Testing** | pytest | Unit and integration tests |

### Translation Models

| Pair | Model | Size |
|------|-------|------|
| zh → en | Helsinki-NLP/opus-mt-zh-en | ~400MB |
| en → zh | Helsinki-NLP/opus-mt-en-zh | ~400MB |
| ja → en | Helsinki-NLP/opus-mt-ja-en | ~400MB |
| en → ja | Helsinki-NLP/opus-mt-en-ja | ~400MB |

---

## Project Structure

```
pyLiveTranslator_kimi/
├── README.md                    # Main project documentation
├── STATUS.md                    # Development status and phases
├── AGENTS.md                    # This file - AI agent documentation
├── FINAL_IMPLEMENTATION_SUMMARY.md  # Complete feature summary
├── SENTENCE_MODE_GUIDE.md       # Sentence mode documentation
├── JAPANESE_TRANSLATION_GUIDE.md    # Japanese translation guide
├── SPEECH_LOSS_EVALUATION_GUIDE.md  # Speech loss evaluation
│
├── src/                         # Source code
│   ├── __init__.py
│   ├── core/                    # Core translation engine
│   │   ├── asr/                 # Automatic Speech Recognition
│   │   │   ├── base.py
│   │   │   ├── faster_whisper.py      # Primary ASR (faster-whisper)
│   │   │   ├── mlx_whisper.py         # Apple Silicon ASR
│   │   │   ├── whisper_cpp.py
│   │   │   ├── streaming_asr.py       # Draft/final streaming modes
│   │   │   ├── post_processor.py      # Hallucination filter (CJK-aware)
│   │   │   └── hardware_backends.py   # OpenVINO/CoreML backends
│   │   ├── pipeline/            # Translation pipelines
│   │   │   ├── base.py
│   │   │   ├── realtime.py
│   │   │   ├── batch.py
│   │   │   ├── hybrid.py
│   │   │   ├── orchestrator.py        # Main pipeline orchestrator
│   │   │   ├── orchestrator_parallel.py  # Parallel ASR processing
│   │   │   ├── streaming_pipeline.py  # End-to-end streaming
│   │   │   ├── segment_tracker.py     # UUID-based segment tracking
│   │   │   ├── queue_monitor.py       # Queue overflow monitoring
│   │   │   └── adaptive_controller.py # Adaptive pipeline control
│   │   ├── translation/         # Translation engines
│   │   │   ├── base.py
│   │   │   ├── marian.py              # MarianMT translator
│   │   │   ├── nllb.py
│   │   │   ├── streaming_translator.py # Semantic gating, SOV safety
│   │   │   ├── pivot.py
│   │   │   └── cache.py               # Translation caching
│   │   ├── configs/             # Configuration files
│   │   │   ├── cloud.yaml
│   │   │   └── edge.yaml
│   │   ├── utils/               # Utility functions
│   │   │   └── latency_analyzer.py
│   │   ├── cli.py               # Core CLI entry
│   │   └── interfaces.py        # Abstract interfaces and data structures
│   │
│   ├── audio/                   # Audio processing module
│   │   ├── __init__.py
│   │   ├── config.py            # Audio configuration
│   │   ├── capture/             # Audio capture (mic, system audio)
│   │   │   ├── base.py
│   │   │   ├── macos.py
│   │   │   ├── windows.py
│   │   │   └── manager.py
│   │   ├── vad/                 # Voice Activity Detection
│   │   │   ├── silero_vad.py
│   │   │   ├── silero_vad_improved.py
│   │   │   ├── silero_vad_adaptive.py
│   │   │   ├── environment_aware_vad.py
│   │   │   └── webrtc_vad.py
│   │   ├── segmentation/        # Audio segmentation
│   │   │   └── engine.py
│   │   ├── pipeline/            # Audio streaming pipeline
│   │   │   └── streaming.py
│   │   ├── video/               # Video audio extraction
│   │   │   └── extractor.py
│   │   ├── benchmarking/        # Performance benchmarks
│   │   │   └── performance.py
│   │   └── testing/             # Audio testing utilities
│   │       └── detection.py
│   │
│   ├── gui/                     # GUI application
│   │   ├── __init__.py
│   │   ├── main.py              # Main PySide6 GUI (54KB+)
│   │   ├── streaming_ui.py      # Streaming UI components
│   │   └── export/              # Export functionality (planned)
│   │
│   └── app/                     # Standalone app components
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── platform_utils.py    # Cross-platform utilities
│       ├── audio_platform.py    # Unified audio capture
│       ├── ml_platform.py       # ML optimization
│       ├── setup.py             # Package setup
│       └── config/              # App packaging config
│           ├── entitlements.plist
│           ├── voice-translate-macos.spec
│           └── voice-translate-windows.spec
│
├── cli/                         # Command-line tools
│   ├── vad_visualizer.py        # Real-time VAD GUI visualizer
│   ├── demo_realtime_translation.py
│   ├── demo_streaming_mode.py
│   ├── demo_video_translation.py
│   └── benchmark_translation.py
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_platform.py         # Platform utility tests
│   ├── test_translation.py      # Translation engine tests
│   ├── test_vad_simple.py       # VAD functionality tests
│   ├── test_week0_data_integrity.py
│   ├── test_phase11_metrics.py
│   ├── test_phase12_streaming_asr.py
│   ├── test_phase13_streaming_translator.py
│   ├── test_phase14_streaming_ui.py
│   ├── test_phase15_integration.py
│   └── benchmarks/              # Performance benchmarks
│
├── scripts/                     # Setup and utility scripts
│   ├── setup_environment.py     # Environment setup
│   ├── example_usage.py         # Usage examples
│   └── analyze_overlap.py       # Overlap analysis
│
├── config/                      # Configuration files
│   ├── interview_mode.json      # Interview mode settings
│   ├── sentence_mode.json       # Sentence mode settings
│   ├── documentary_mode.json    # Documentary mode settings
│   ├── sentence_aware.yaml      # Sentence-aware config
│   ├── environments/            # Conda environments
│   │   ├── macos-arm64.yml
│   │   └── windows.yml
│   └── requirements/            # Requirements files
│       └── requirements.txt
│
├── docs/                        # Documentation
│   ├── architecture/            # Architecture documents
│   ├── design/                  # Design documents
│   ├── guides/                  # Implementation guides
│   ├── installation.md
│   ├── test-plan.md
│   ├── troubleshooting.md
│   └── user-guide.md
│
├── monitoring/                  # Prometheus/Grafana config
│   ├── prometheus.yml
│   └── grafana/
│
├── assets/                      # Static assets
│   └── icon.icns
│
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml           # Docker orchestration
├── requirements-prod.txt        # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── run_interview_mode.sh        # Interview mode launcher
├── run_sentence_mode.sh         # Sentence mode launcher
├── run_japanese_to_english.sh   # Japanese translation launcher
├── run_documentary_mode.sh      # Documentary mode launcher
├── test_microphone.py           # Microphone test utility
└── test_japanese_translation.py # Japanese translation test
```

---

## Key Entry Points

### 1. GUI Application (Primary)

```bash
# Standard mode
python src/gui/main.py

# Interview mode (documentary)
./run_interview_mode.sh

# Sentence mode (dialogue)
./run_sentence_mode.sh

# Japanese translation
./run_japanese_to_english.sh
```

### 2. CLI Tools

```bash
# Real-time translation demo
python cli/demo_realtime_translation.py --source zh --target en --device 4

# Streaming mode with draft/final
python cli/demo_streaming_mode.py --source ja --target en --draft-interval 2000

# Video translation with subtitle export
python cli/demo_video_translation.py video.mp4 --source zh --target en --export-srt

# VAD Visualizer (GUI with real-time audio meter)
python cli/vad_visualizer.py

# Performance benchmark
python cli/benchmark_translation.py
```

### 3. Core Application (Cross-Platform)

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

### 4. Testing Utilities

```bash
# Test microphone
python test_microphone.py

# Test Japanese translation
python test_japanese_translation.py

# Test VAD with device selection
python tests/test_vad_simple.py --device 4 --duration 30

# List audio devices
python tests/test_vad_simple.py --list
```

---

## Build and Test Commands

### Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
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

# Run VAD test with audio capture
python tests/test_vad_simple.py --device 4 --duration 30

# Run platform tests
python tests/test_platform.py

# Run unit tests (unittest)
python -m unittest discover tests/
```

### Docker Deployment

```bash
# Production
docker-compose up -d app

# With monitoring (Prometheus/Grafana)
docker-compose --profile monitoring up -d

# Development mode with live reload
docker-compose --profile dev up -d app-dev

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
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

| Type | Convention | Example |
|------|------------|---------|
| **Classes** | PascalCase | `AudioManager`, `SileroVADProcessor` |
| **Functions/Variables** | snake_case | `process_chunk`, `sample_rate` |
| **Constants** | UPPER_SNAKE_CASE | `DEFAULT_SAMPLE_RATE` |
| **Abstract Interfaces** | Start with 'I' | `IAudioCapture`, `IVADEngine` |
| **Private Members** | Leading underscore | `_audio_buffer`, `_process_internal` |

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
├── test_vad_simple.py        # VAD functionality tests
├── test_week0_data_integrity.py    # Data integrity verification
├── test_phase11_metrics.py   # Phase 1.1 metrics tests
├── test_phase12_streaming_asr.py   # Streaming ASR tests
├── test_phase13_streaming_translator.py  # Streaming translator tests
├── test_phase14_streaming_ui.py        # Streaming UI tests
├── test_phase15_integration.py         # Integration tests
└── benchmarks/               # Performance benchmarks
```

### Verification Tools

```bash
# GUI visualizer with real-time audio meter and VAD graph
python cli/vad_visualizer.py

# Simple CLI test that saves captured speech segments
python tests/test_vad_simple.py --device 4 --duration 30

# List available audio devices
python tests/test_vad_simple.py --list

# Test microphone recording
python test_microphone.py

# Test Japanese translation
python test_japanese_translation.py
```

---

## Configuration

### Mode Configurations

**Standard Mode** (default):
- Max segment: 12 seconds
- Silence threshold: 400ms
- Balanced quality/speed

**Interview Mode** (`config/interview_mode.json`):
- Max segment: 15 seconds
- Lenient filtering (12% diversity)
- Keeps filler words
- Low confidence threshold (0.2)

**Sentence Mode** (`config/sentence_mode.json`):
- Max segment: 20 seconds
- Silence threshold: 600ms
- CJK-aware hallucination filter
- Filters short fragments (500ms min)

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
from src.core.pipeline.orchestrator import PipelineConfig, AudioSource

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
    enable_translation_cache=True,
    audio_source=AudioSource.MICROPHONE
)
```

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceTranslate Pro 2.0                    │
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
│  │  │   ASR    │  │    MT    │  │   VAD    │        │      │
│  │  │ (Whisper)│  │(Marian/  │  │(Silero)  │        │      │
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

### Streaming Pipeline Flow

```
Audio → VAD → [Adaptive Controller] → StreamingASR
              ↓
          Skip if: paused, busy, <2s
              ↓
  ┌─────────────────────┐  ┌─────────────────────┐
  │ Draft Mode          │  │ Final Mode          │
  │ • Every 2s          │  │ • On silence        │
  │ • INT8, beam=1      │  │ • Standard, beam=5  │
  │ • Cumulative (0-N)  │  │ • High confidence   │
  └──────────┬──────────┘  └──────────┬──────────┘
             ↓                        ↓
  ┌──────────────────────────────────────────┐
  │     StreamingTranslator                  │
  │     • Semantic gating                    │
  │     • SOV safety (JA/KO/DE)              │
  │     • Stability scoring                  │
  └──────────────────┬───────────────────────┘
                     ↓
  ┌──────────────────────────────────────────┐
  │     Diff-Based UI                        │
  │     • Word-level diff                    │
  │     • Stability (● ○ ✓)                  │
  │     • Delta time display                 │
  └──────────────────────────────────────────┘
```

---

## Security Considerations

1. **Audio Data**: Audio is processed locally by default (edge mode)
2. **Cloud Mode**: Only sends data to cloud APIs when explicitly enabled
3. **Model Downloads**: Models downloaded from trusted sources (Hugging Face)
4. **Permissions**: Requires microphone access (platform-specific prompts)
5. **macOS App Sandboxing**: `entitlements.plist` configures sandbox permissions
6. **Docker Security**: Non-root user (`voicetranslate`) in production containers

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

## Troubleshooting

### No Audio Input

```bash
# List devices
python cli/demo_realtime_translation.py --list-devices

# Test microphone
python test_microphone.py

# Grant macOS permission
# System Settings → Privacy & Security → Microphone → Enable Terminal
```

### Japanese Not Recognized

- Select "Japanese (ja)" as source (NOT "Auto-detect")
- Use "base" or "small" model (not "tiny")
- Check `JAPANESE_TRANSLATION_GUIDE.md`

### Sentences Cut Mid-Way

- Use **Sentence Mode**: `./run_sentence_mode.sh`
- Increases max duration to 20s
- Better pause detection

### High Latency

- Enable INT8 quantization (enabled by default)
- Use hardware acceleration (OpenVINO/CoreML)
- Check CPU usage

---

## Documentation References

| Document | Description |
|----------|-------------|
| `README.md` | Main project overview and user guide |
| `STATUS.md` | Current development status and phase tracking |
| `FINAL_IMPLEMENTATION_SUMMARY.md` | Complete implementation summary |
| `SENTENCE_MODE_GUIDE.md` | Sentence mode documentation |
| `JAPANESE_TRANSLATION_GUIDE.md` | Japanese translation guide |
| `docs/architecture/` | System architecture details |
| `docs/design/` | Design documents |
| `docs/guides/` | Implementation guides |
| `docs/installation.md` | Platform-specific installation |
| `docs/test-plan.md` | Testing strategy |
| `docs/troubleshooting.md` | Troubleshooting guide |

---

*This file should be updated when significant architectural changes are made.*
*Last updated: 2026-02-21*
