# Project Structure

This document outlines the organization of the VoiceTranslate Pro repository.

## Overview

```
Kimi_Agent_Hybrid Edge-Cloud Real-Time Translator/
├── README.md                   # Main project documentation
├── LICENSE                     # License file
├── VERSION                     # Current version
├── .gitignore                  # Git ignore rules
│
├── src/                        # Source code
│   ├── __init__.py
│   ├── core/                   # Core translation system
│   │   ├── asr/               # Automatic Speech Recognition
│   │   ├── pipeline/          # Translation pipelines
│   │   ├── translation/       # Translation engines
│   │   └── utils/             # Utility functions
│   │
│   ├── audio/                  # Audio processing module
│   │   ├── capture/           # Audio capture (mic, system audio)
│   │   ├── vad/               # Voice Activity Detection
│   │   ├── segmentation/      # Audio segmentation
│   │   ├── pipeline/          # Audio streaming pipeline
│   │   ├── video/             # Video audio extraction
│   │   ├── benchmarking/      # Performance benchmarks
│   │   └── testing/           # Audio testing utilities
│   │
│   ├── gui/                    # GUI application
│   │   └── main.py            # Main GUI entry point
│   │
│   └── app/                    # Standalone app components
│       ├── main.py
│       ├── platform_utils.py
│       └── ...
│
├── cli/                        # Command-line tools
│   ├── demo_realtime_translation.py
│   ├── demo_video_translation.py
│   ├── vad_visualizer.py
│   └── benchmark_translation.py
│
├── tests/                      # Test suite
│   ├── test_translation.py
│   ├── test_vad_simple.py
│   └── test_platform.py
│
├── scripts/                    # Setup and utility scripts
│   ├── setup_environment.py
│   └── example_usage.py
│
├── docs/                       # Documentation
│   ├── README.md              # Documentation index
│   ├── architecture/          # Architecture documents
│   ├── design/                # Design documents
│   ├── guides/                # Implementation guides
│   └── releases/              # Release notes
│
├── config/                     # Configuration files
│   ├── requirements/          # Python requirements
│   └── environments/          # Conda environment files
│
└── assets/                     # Static assets
    ├── *.png                  # Screenshots, diagrams
    └── *.html                 # HTML exports
```

## Source Code Organization

### `src/core/`
Core translation functionality independent of audio capture or GUI.

- **`asr/`** - Speech recognition implementations (Whisper, faster-whisper)
- **`pipeline/`** - Pipeline orchestration (real-time, batch, hybrid)
- **`translation/`** - Translation engines (MarianMT, NLLB)
- **`utils/`** - Shared utilities (latency analyzer, etc.)

### `src/audio/`
Audio processing and capture functionality.

- **`capture/`** - Platform-specific audio capture (macOS, Windows)
- **`vad/`** - Voice Activity Detection (Silero VAD, WebRTC VAD)
- **`segmentation/`** - Audio segmentation engine
- **`pipeline/`** - Audio streaming pipeline with processors
- **`video/`** - Video audio extraction using FFmpeg
- **`benchmarking/`** - Performance benchmarking tools
- **`testing/`** - Audio testing and detection utilities

### `src/gui/`
PySide6-based graphical user interface.

- **`main.py`** - Main GUI application (previously `voice_translate_gui.py`)

### `src/app/`
Standalone application components for packaging.

## Command Line Tools

### `cli/`
Command-line demonstrations and utilities.

| Script | Purpose |
|--------|---------|
| `demo_realtime_translation.py` | Real-time translation demo |
| `demo_video_translation.py` | Video file translation |
| `vad_visualizer.py` | Real-time VAD visualization |
| `benchmark_translation.py` | Performance benchmarking |

## Tests

### `tests/`
Test suite for the project.

| Test | Purpose |
|------|---------|
| `test_translation.py` | Translation engine tests |
| `test_vad_simple.py` | VAD functionality tests |
| `test_platform.py` | Platform utility tests |

## Documentation

### `docs/`
Comprehensive documentation organized by type.

- **`architecture/`** - System architecture and subsystem designs
- **`design/`** - UI/UX design documents
- **`guides/`** - Implementation guides and proposals
- **`releases/`** - Release notes and changelogs

## Configuration

### `config/`
Configuration files for dependencies and environments.

- **`requirements/`** - pip requirements files
- **`environments/`** - Conda environment specifications

## Migration from Old Structure

If you have scripts referencing the old structure, update imports:

| Old Import | New Import |
|------------|------------|
| `from audio_module import ...` | `from src.audio import ...` |
| `from voice_translation.src.asr import ...` | `from src.core.asr import ...` |
| `from voice_translation.src.translation import ...` | `from src.core.translation import ...` |
| `from voice_translation.src.pipeline import ...` | `from src.core.pipeline import ...` |
| `from voice_translation_app.src import ...` | `from src.app import ...` |

### Entry Points

| Old Path | New Path |
|----------|----------|
| `voice_translate_gui.py` | `src/gui/main.py` |
| `voice_translation/main.py` | `src/core/cli.py` |
| `demo_video_translation.py` | `cli/demo_video_translation.py` |
| `test_vad_simple.py` | `tests/test_vad_simple.py` |
