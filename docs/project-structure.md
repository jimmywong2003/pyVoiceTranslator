# Project Structure Documentation

## VoiceTranslate Pro - Directory Structure and Organization

This document describes the complete project structure, file organization, and module hierarchy of VoiceTranslate Pro.

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Module Organization](#module-organization)
4. [File Naming Conventions](#file-naming-conventions)
5. [Configuration Files](#configuration-files)
6. [Asset Organization](#asset-organization)
7. [Build and Distribution](#build-and-distribution)

---

## Overview

VoiceTranslate Pro follows a modular, well-organized project structure that separates concerns and facilitates development, testing, and deployment.

### Design Principles

1. **Modularity**: Each component is self-contained
2. **Separation of Concerns**: UI, logic, and data are separated
3. **Testability**: Easy to write and run tests
4. **Scalability**: Easy to add new features
5. **Maintainability**: Clear organization and documentation

---

## Directory Structure

```
voicetranslate-pro/
├── .github/                          # GitHub configuration
│   ├── workflows/                    # CI/CD workflows
│   │   ├── test.yml                  # Test automation
│   │   ├── build.yml                 # Build automation
│   │   └── release.yml               # Release automation
│   ├── ISSUE_TEMPLATE/               # Issue templates
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/                             # Documentation
│   ├── README.md                     # Documentation index
│   ├── installation.md               # Installation guide
│   ├── user-guide.md                 # User manual
│   ├── api-reference.md              # API documentation
│   ├── architecture.md               # System architecture
│   ├── test-plan.md                  # Testing documentation
│   ├── contributing.md               # Contribution guidelines
│   ├── troubleshooting.md            # Troubleshooting guide
│   ├── user-scenarios.md             # Use case documentation
│   ├── project-structure.md          # This file
│   ├── languages.md                  # Supported languages
│   ├── video-testing.md              # Video testing docs
│   ├── gui-documentation.md          # GUI documentation
│   └── assets/                       # Documentation assets
│       ├── screenshots/              # UI screenshots
│       ├── diagrams/                 # Architecture diagrams
│       └── videos/                   # Demo videos
│
├── src/                              # Source code
│   └── voicetranslate_pro/           # Main package
│       ├── __init__.py               # Package initialization
│       ├── __main__.py               # Entry point
│       ├── version.py                # Version information
│       │
│       ├── core/                     # Core functionality
│       │   ├── __init__.py
│       │   ├── config.py             # Configuration management
│       │   ├── exceptions.py         # Custom exceptions
│       │   ├── logger.py             # Logging setup
│       │   └── constants.py          # Constants and enums
│       │
│       ├── asr/                      # Speech Recognition
│       │   ├── __init__.py
│       │   ├── base.py               # Base ASR class
│       │   ├── whisper_asr.py        # Whisper implementation
│       │   ├── google_asr.py         # Google Speech-to-Text
│       │   ├── azure_asr.py          # Azure Speech Services
│       │   ├── local_asr.py          # Local ASR models
│       │   └── utils.py              # ASR utilities
│       │
│       ├── translation/              # Translation
│       │   ├── __init__.py
│       │   ├── base.py               # Base translator class
│       │   ├── deepl_translator.py   # DeepL implementation
│       │   ├── google_translator.py  # Google Translate
│       │   ├── azure_translator.py   # Azure Translator
│       │   ├── local_translator.py   # Local translation
│       │   └── utils.py              # Translation utilities
│       │
│       ├── tts/                      # Text-to-Speech
│       │   ├── __init__.py
│       │   ├── base.py               # Base TTS class
│       │   ├── coqui_tts.py          # Coqui TTS
│       │   ├── elevenlabs_tts.py     # ElevenLabs
│       │   ├── google_tts.py         # Google TTS
│       │   ├── azure_tts.py          # Azure TTS
│       │   └── utils.py              # TTS utilities
│       │
│       ├── audio/                    # Audio Processing
│       │   ├── __init__.py
│       │   ├── processor.py          # Audio processing
│       │   ├── recorder.py           # Audio recording
│       │   ├── player.py             # Audio playback
│       │   ├── vad.py                # Voice Activity Detection
│       │   ├── noise_reduction.py    # Noise reduction
│       │   └── utils.py              # Audio utilities
│       │
│       ├── video/                    # Video Processing
│       │   ├── __init__.py
│       │   ├── capture.py            # Video capture
│       │   ├── overlay.py            # Overlay rendering
│       │   ├── webrtc.py             # WebRTC integration
│       │   ├── virtual_camera.py     # Virtual camera
│       │   └── utils.py              # Video utilities
│       │
│       ├── gui/                      # Graphical User Interface
│       │   ├── __init__.py
│       │   ├── main_window.py        # Main window
│       │   ├── widgets/              # Custom widgets
│       │   │   ├── __init__.py
│       │   │   ├── language_combo.py
│       │   │   ├── audio_visualizer.py
│       │   │   ├── translation_display.py
│       │   │   └── status_bar.py
│       │   ├── dialogs/              # Dialog windows
│       │   │   ├── __init__.py
│       │   │   ├── settings_dialog.py
│       │   │   ├── about_dialog.py
│       │   │   └── error_dialog.py
│       │   ├── styles/               # UI styles
│       │   │   ├── dark_theme.qss
│       │   │   ├── light_theme.qss
│       │   │   └── common.qss
│       │   └── resources/            # UI resources
│       │       ├── icons/
│       │       ├── images/
│       │       └── fonts/
│       │
│       ├── api/                      # REST API
│       │   ├── __init__.py
│       │   ├── server.py             # FastAPI server
│       │   ├── routes/               # API routes
│       │   │   ├── __init__.py
│       │   │   ├── translation.py
│       │   │   ├── languages.py
│       │   │   ├── sessions.py
│       │   │   └── health.py
│       │   ├── middleware/           # API middleware
│       │   │   ├── __init__.py
│       │   │   ├── auth.py
│       │   │   ├── rate_limit.py
│       │   │   └── logging.py
│       │   └── models/               # API models
│       │       ├── __init__.py
│       │       ├── requests.py
│       │       └── responses.py
│       │
│       ├── websocket/                # WebSocket Server
│       │   ├── __init__.py
│       │   ├── server.py             # WebSocket server
│       │   ├── handlers.py           # Message handlers
│       │   └── session.py            # Session management
│       │
│       ├── pipeline/                 # Translation Pipeline
│       │   ├── __init__.py
│       │   ├── base.py               # Base pipeline
│       │   ├── realtime.py           # Real-time pipeline
│       │   ├── batch.py              # Batch pipeline
│       │   └── video.py              # Video pipeline
│       │
│       ├── cache/                    # Caching
│       │   ├── __init__.py
│       │   ├── base.py               # Base cache
│       │   ├── memory_cache.py       # In-memory cache
│       │   ├── redis_cache.py        # Redis cache
│       │   └── disk_cache.py         # Disk cache
│       │
│       ├── database/                 # Database
│       │   ├── __init__.py
│       │   ├── models.py             # Database models
│       │   ├── crud.py               # CRUD operations
│       │   └── migrations/           # Database migrations
│       │
│       ├── utils/                    # Utilities
│       │   ├── __init__.py
│       │   ├── file_utils.py
│       │   ├── text_utils.py
│       │   ├── network_utils.py
│       │   ├── time_utils.py
│       │   └── validators.py
│       │
│       └── cli/                      # Command Line Interface
│           ├── __init__.py
│           ├── main.py               # CLI entry point
│           └── commands/             # CLI commands
│               ├── __init__.py
│               ├── translate.py
│               ├── config.py
│               └── diagnose.py
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # pytest configuration
│   ├── unit/                         # Unit tests
│   │   ├── __init__.py
│   │   ├── test_asr.py
│   │   ├── test_translation.py
│   │   ├── test_tts.py
│   │   ├── test_audio.py
│   │   ├── test_video.py
│   │   ├── test_gui.py
│   │   └── test_utils.py
│   ├── integration/                  # Integration tests
│   │   ├── __init__.py
│   │   ├── test_pipeline.py
│   │   ├── test_api.py
│   │   └── test_websocket.py
│   ├── performance/                  # Performance tests
│   │   ├── __init__.py
│   │   ├── test_latency.py
│   │   ├── test_throughput.py
│   │   └── test_memory.py
│   ├── e2e/                          # End-to-end tests
│   │   ├── __init__.py
│   │   └── test_workflows.py
│   └── fixtures/                     # Test fixtures
│       ├── audio/
│       ├── text/
│       └── video/
│
├── scripts/                          # Utility scripts
│   ├── setup.sh                      # Setup script
│   ├── build.sh                      # Build script
│   ├── release.sh                    # Release script
│   └── benchmark.py                  # Benchmarking
│
├── configs/                          # Configuration templates
│   ├── config.yaml.example
│   ├── logging.yaml
│   └── docker/
│       ├── Dockerfile
│       └── docker-compose.yml
│
├── assets/                           # Application assets
│   ├── icons/                        # Application icons
│   ├── sounds/                       # Sound effects
│   ├── images/                       # Images
│   └── fonts/                        # Custom fonts
│
├── locales/                          # Internationalization
│   ├── en/                           # English
│   │   └── LC_MESSAGES/
│   ├── zh/                           # Chinese
│   │   └── LC_MESSAGES/
│   ├── ja/                           # Japanese
│   │   └── LC_MESSAGES/
│   └── fr/                           # French
│       └── LC_MESSAGES/
│
├── models/                           # ML Models (downloaded)
│   ├── asr/                          # ASR models
│   ├── translation/                  # Translation models
│   └── tts/                          # TTS models
│
├── data/                             # Application data
│   ├── cache/                        # Cache directory
│   ├── logs/                         # Log files
│   └── history/                      # Conversation history
│
├── .gitignore                        # Git ignore rules
├── .pre-commit-config.yaml           # Pre-commit hooks
├── LICENSE                           # License file
├── README.md                         # Project README
├── CHANGELOG.md                      # Change log
├── CONTRIBUTING.md                   # Contribution guidelines
├── MANIFEST.in                       # Package manifest
├── pyproject.toml                    # Project configuration
├── requirements.txt                  # Dependencies
├── requirements-dev.txt              # Dev dependencies
└── setup.py                          # Setup script
```

---

## Module Organization

### Core Module (`core/`)

Contains foundational components used throughout the application.

```python
# core/config.py
class Configuration:
    """Centralized configuration management."""
    
    def __init__(self, config_path: Optional[str] = None):
        self._config = self._load_config(config_path)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self._config[key] = value
        self._save_config()
```

### ASR Module (`asr/`)

Speech recognition implementations with a common interface.

```python
# asr/base.py
from abc import ABC, abstractmethod

class BaseASR(ABC):
    """Abstract base class for ASR engines."""
    
    @abstractmethod
    async def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if engine is available."""
        pass

# asr/whisper_asr.py
class WhisperASR(BaseASR):
    """OpenAI Whisper ASR implementation."""
    
    def __init__(self, model_name: str = "base"):
        self.model = whisper.load_model(model_name)
    
    async def transcribe(self, audio, language=None):
        result = self.model.transcribe(audio, language=language)
        return TranscriptionResult(
            text=result["text"],
            confidence=result.get("confidence", 0.9)
        )
```

### Translation Module (`translation/`)

Machine translation implementations.

```python
# translation/base.py
class BaseTranslator(ABC):
    """Abstract base class for translation engines."""
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> TranslationResult:
        """Translate text."""
        pass
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        pass
```

### GUI Module (`gui/`)

User interface components organized by functionality.

```
gui/
├── main_window.py          # Main application window
├── widgets/                # Reusable UI components
│   ├── language_combo.py   # Language selector
│   ├── audio_visualizer.py # Audio level display
│   └── translation_display.py  # Translation output
├── dialogs/                # Modal dialogs
│   ├── settings_dialog.py  # Settings window
│   └── about_dialog.py     # About window
└── styles/                 # Stylesheets
    ├── dark_theme.qss
    └── light_theme.qss
```

---

## File Naming Conventions

### Python Files

| Pattern | Example | Purpose |
|---------|---------|---------|
| `module_name.py` | `whisper_asr.py` | Implementation files |
| `base.py` | `base.py` | Abstract base classes |
| `utils.py` | `audio_utils.py` | Utility functions |
| `test_*.py` | `test_asr.py` | Test files |
| `*_test.py` | `integration_test.py` | Alternative test naming |

### Configuration Files

| Pattern | Example | Purpose |
|---------|---------|---------|
| `*.yaml` | `config.yaml` | YAML configuration |
| `*.json` | `settings.json` | JSON configuration |
| `*.ini` | `logging.ini` | INI configuration |
| `*.example` | `config.yaml.example` | Example templates |

### Resource Files

| Pattern | Example | Purpose |
|---------|---------|---------|
| `icon_*.png` | `icon_main.png` | Icons |
| `*_theme.qss` | `dark_theme.qss` | Stylesheets |
| `*.wav` | `notification.wav` | Sound files |

---

## Configuration Files

### Main Configuration (`config.yaml`)

```yaml
# config.yaml structure
app:
  name: "VoiceTranslate Pro"
  version: "2.1.0"
  debug: false

audio:
  input_device: "default"
  output_device: "default"
  sample_rate: 16000

translation:
  default_source: "en"
  default_target: "zh"
  engine: "deepl"

gui:
  theme: "dark"
  language: "en"

api:
  host: "0.0.0.0"
  port: 8000
```

### Environment Variables

```bash
# .env file
VOICETRANSLATE_CONFIG_PATH=/path/to/config.yaml
VOICETRANSLATE_LOG_LEVEL=INFO
VOICETRANSLATE_API_KEY=your-api-key
DEEPL_API_KEY=your-deepl-key
```

### Loading Configuration

```python
# core/config.py
import os
import yaml
from pathlib import Path

class ConfigLoader:
    """Load configuration from multiple sources."""
    
    DEFAULT_PATHS = [
        Path.home() / ".voicetranslate-pro" / "config.yaml",
        Path("/etc/voicetranslate-pro/config.yaml"),
        Path("config.yaml"),
    ]
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> dict:
        """Load configuration from file."""
        if path:
            config_path = Path(path)
        else:
            config_path = cls._find_config()
        
        if config_path and config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        
        return cls._default_config()
    
    @classmethod
    def _find_config(cls) -> Optional[Path]:
        """Find configuration file."""
        for path in cls.DEFAULT_PATHS:
            if path.exists():
                return path
        return None
```

---

## Asset Organization

### Icons

```
assets/icons/
├── app/
│   ├── icon_16x16.png
│   ├── icon_32x32.png
│   ├── icon_48x48.png
│   ├── icon_128x128.png
│   ├── icon_256x256.png
│   └── icon_512x512.png
├── actions/
│   ├── play.png
│   ├── pause.png
│   ├── stop.png
│   ├── record.png
│   └── settings.png
└── flags/
    ├── en.png
    ├── zh.png
    ├── ja.png
    └── ...
```

### Sounds

```
assets/sounds/
├── ui/
│   ├── click.wav
│   ├── notification.wav
│   └── error.wav
├── translation/
│   ├── start.wav
│   ├── complete.wav
│   └── error.wav
└── effects/
    ├── beep.wav
    └── success.wav
```

### Loading Assets

```python
# utils/file_utils.py
from pathlib import Path
import pkg_resources

class AssetLoader:
    """Load application assets."""
    
    ASSET_DIR = Path(__file__).parent.parent / "assets"
    
    @classmethod
    def get_icon(cls, name: str, size: int = 32) -> str:
        """Get icon path."""
        icon_path = cls.ASSET_DIR / "icons" / f"{name}_{size}x{size}.png"
        return str(icon_path)
    
    @classmethod
    def get_sound(cls, name: str) -> str:
        """Get sound file path."""
        sound_path = cls.ASSET_DIR / "sounds" / f"{name}.wav"
        return str(sound_path)
```

---

## Build and Distribution

### Build Structure

```
build/
├── lib/                    # Compiled libraries
├── exe/                    # Executable files
├── installer/              # Installer packages
│   ├── windows/
│   ├── macos/
│   └── linux/
└── dist/                   # Distribution packages
    ├── pip/
    ├── conda/
    └── docker/
```

### Package Structure

```
voicetranslate_pro-2.1.0/
├── voicetranslate_pro/     # Package directory
│   ├── __init__.py
│   ├── ...
├── voicetranslate_pro.exe  # Windows executable
├── voicetranslate-pro      # Linux/macOS executable
├── assets/                   # Bundled assets
├── models/                   # Bundled models
├── config.yaml.example       # Example config
├── README.md
└── LICENSE
```

### PyInstaller Spec

```python
# build.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/voicetranslate_pro/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('locales', 'locales'),
    ],
    hiddenimports=[
        'pyaudio',
        'whisper',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VoiceTranslatePro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app/icon_256x256.png',
)
```

---

## Import Structure

### Public API

```python
# voicetranslate_pro/__init__.py
"""VoiceTranslate Pro - Real-time voice translation."""

__version__ = "2.1.0"
__author__ = "VoiceTranslate Team"

# Public API
from .core.config import Configuration
from .asr import ASRFactory
from .translation import TranslatorFactory
from .tts import TTSFactory
from .pipeline import TranslationPipeline

__all__ = [
    "Configuration",
    "ASRFactory",
    "TranslatorFactory",
    "TTSFactory",
    "TranslationPipeline",
]
```

### Internal Imports

```python
# Internal module imports
from ..core.config import Configuration
from ..core.exceptions import TranslationError
from ..utils.audio_utils import normalize_audio
```

---

This project structure ensures maintainability, testability, and scalability of VoiceTranslate Pro.
