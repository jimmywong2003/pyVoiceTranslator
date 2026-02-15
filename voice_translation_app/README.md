# Voice Translation Application

A cross-platform real-time voice translation application supporting macOS (Intel & Apple Silicon) and Windows 10/11.

## Features

- 🎙️ Real-time audio capture from microphone and system audio
- 🗣️ Speech recognition using OpenAI Whisper
- 🌐 Translation to multiple languages
- ⚡ Hardware-accelerated inference (MPS on Apple Silicon, CUDA on Windows)
- 📦 Standalone executable distribution

## Supported Platforms

| Platform | Architecture | Acceleration |
|----------|-------------|--------------|
| macOS 11+ | Apple Silicon (M1/M2/M3) | MPS |
| macOS 11+ | Intel (x86_64) | CPU |
| Windows 10/11 | x86_64 | CUDA / DirectML |

## Quick Start

### macOS (Apple Silicon)

```bash
# Install dependencies
brew install portaudio ffmpeg blackhole-2ch

# Setup environment
conda env create -f environment-macos-arm64.yml
conda activate voice-translate-arm64

# Run
python src/main.py
```

### Windows

```bash
# Setup environment
conda env create -f environment-windows.yml
conda activate voice-translate-win

# Run
python src/main.py
```

## Usage

```bash
# List audio devices
python src/main.py --list-devices

# Use specific device
python src/main.py --device 1

# Capture system audio (requires setup)
python src/main.py --system-audio

# Use specific model
python src/main.py --model base

# Check dependencies
python src/main.py --check-deps
```

## Building

### macOS

```bash
# Build app bundle
python setup.py py2app

# Or use PyInstaller
pyinstaller config/voice-translate-macos.spec
```

### Windows

```bash
pyinstaller config/voice-translate-windows.spec
```

## Project Structure

```
voice_translation_app/
├── src/
│   ├── main.py              # Entry point
│   ├── audio_platform.py    # Cross-platform audio capture
│   ├── ml_platform.py       # ML optimizations
│   └── platform_utils.py    # Platform detection & utilities
├── config/
│   ├── voice-translate-macos.spec     # PyInstaller spec (macOS)
│   ├── voice-translate-windows.spec   # PyInstaller spec (Windows)
│   └── entitlements.plist             # macOS entitlements
├── tests/
│   └── test_platform.py     # Unit tests
├── docs/
│   └── CROSS_PLATFORM_GUIDE.md        # Detailed documentation
├── requirements.txt                     # Base requirements
├── requirements-macos-arm64.txt         # macOS ARM64 requirements
├── requirements-windows.txt             # Windows requirements
├── environment-macos-arm64.yml          # Conda env (macOS)
├── environment-windows.yml              # Conda env (Windows)
└── setup.py                             # Setup script
```

## Documentation

See [docs/CROSS_PLATFORM_GUIDE.md](docs/CROSS_PLATFORM_GUIDE.md) for detailed documentation on:
- Audio capture architecture
- ML optimizations
- Environment setup
- Building & packaging
- Code signing
- Testing strategy
- Troubleshooting

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## License

MIT License - See LICENSE file for details
