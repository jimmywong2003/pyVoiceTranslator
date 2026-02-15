# VoiceTranslate Pro 🎙️🌐

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

> **Real-time voice translation application with multi-language support, modern GUI, and video call integration.**

[English](README.md) | [中文](docs/README.zh.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Supported Languages](#supported-languages)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## 🎯 Overview

**VoiceTranslate Pro** is a cutting-edge real-time voice translation application that enables seamless communication across language barriers. Whether you're in a business meeting, traveling abroad, or collaborating with international teams, VoiceTranslate Pro provides instant, accurate translations with natural-sounding speech output.

### Key Capabilities

- 🎤 **Real-time Speech Recognition** - Capture and transcribe speech instantly
- 🔄 **Instant Translation** - Translate between 50+ languages with AI-powered accuracy
- 🔊 **Natural Text-to-Speech** - Output translations with human-like voice synthesis
- 🖥️ **Modern GUI Interface** - Intuitive, responsive user interface
- 📹 **Video Call Integration** - Translate during video conferences
- 🌐 **Multi-Platform Support** - Windows, macOS, and Linux compatibility

---

## ✨ Features

### Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| Real-time Translation | Instant voice-to-voice translation | ✅ Available |
| Multi-Language Support | 50+ languages supported | ✅ Available |
| Modern GUI | Clean, intuitive interface | ✅ Available |
| Video Call Mode | Translate during video conferences | ✅ Available |
| Offline Mode | Basic translation without internet | 🚧 In Progress |
| Custom Voices | Personalized voice profiles | 🚧 In Progress |
| Conversation History | Save and review past translations | ✅ Available |
| Pronunciation Guide | Learn correct pronunciation | ✅ Available |

### Advanced Features

- **Noise Cancellation** - Filter background noise for better recognition
- **Accent Adaptation** - Adjust to different accents and dialects
- **Context Awareness** - Understand conversation context for better translations
- **Privacy Mode** - Local processing for sensitive conversations
- **Batch Translation** - Translate recorded audio files
- **Export Options** - Save translations as text, audio, or subtitles

---

## 📸 Screenshots

### Main Interface
![Main Interface](docs/assets/screenshots/main_interface.png)

### Translation in Progress
![Translation Mode](docs/assets/screenshots/translation_mode.png)

### Video Call Integration
![Video Mode](docs/assets/screenshots/video_mode.png)

### Settings Panel
![Settings](docs/assets/screenshots/settings.png)

---

## 🚀 Installation

### System Requirements

**Minimum Requirements:**
- OS: Windows 10/11, macOS 10.15+, or Ubuntu 20.04+
- RAM: 4 GB
- Storage: 2 GB free space
- Internet: Broadband connection (for cloud features)
- Microphone: Built-in or external

**Recommended Requirements:**
- OS: Windows 11, macOS 12+, or Ubuntu 22.04+
- RAM: 8 GB or more
- Storage: 5 GB free space
- Internet: High-speed connection
- Microphone: High-quality external microphone
- GPU: NVIDIA GPU with CUDA support (for enhanced performance)

### Quick Installation

#### Windows

```powershell
# Download the installer
Invoke-WebRequest -Uri "https://github.com/yourusername/voicetranslate-pro/releases/latest/download/VoiceTranslatePro-Setup.exe" -OutFile "VoiceTranslatePro-Setup.exe"

# Run the installer
.\VoiceTranslatePro-Setup.exe
```

#### macOS

```bash
# Using Homebrew
brew install voicetranslate-pro

# Or download DMG
curl -L -o VoiceTranslatePro.dmg "https://github.com/yourusername/voicetranslate-pro/releases/latest/download/VoiceTranslatePro.dmg"
open VoiceTranslatePro.dmg
```

#### Linux

```bash
# Ubuntu/Debian
wget https://github.com/yourusername/voicetranslate-pro/releases/latest/download/voicetranslate-pro.deb
sudo dpkg -i voicetranslate-pro.deb

# Or using snap
sudo snap install voicetranslate-pro
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/voicetranslate-pro.git
cd voicetranslate-pro

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .

# Run the application
python -m voicetranslate_pro
```

For detailed installation instructions, see [Installation Guide](docs/installation.md).

---

## 🎬 Quick Start

### 1. Launch the Application

```bash
# If installed via package manager
voicetranslate-pro

# If running from source
python -m voicetranslate_pro
```

### 2. Select Languages

1. Choose your **source language** (the language you speak)
2. Choose your **target language** (the language to translate to)

### 3. Start Translating

1. Click the **"Start"** button or press `Space`
2. Speak clearly into your microphone
3. View the translation in real-time
4. Hear the translated speech output

### 4. Example Usage

```python
from voicetranslate_pro import VoiceTranslator

# Initialize translator
translator = VoiceTranslator(
    source_lang='en',
    target_lang='zh'
)

# Start real-time translation
translator.start_translation()

# Stop when done
translator.stop_translation()
```

---

## 📖 Usage Guide

### Basic Translation Mode

1. **Open the application**
2. **Select source and target languages** from dropdown menus
3. **Click "Start Listening"** to begin
4. **Speak naturally** - the app will detect speech automatically
5. **View translation** in the text display area
6. **Listen to output** through speakers or headphones

### Video Call Mode

1. **Click "Video Mode"** in the main menu
2. **Select your video source** (camera or screen share)
3. **Choose translation direction**:
   - Incoming: Translate what others say
   - Outgoing: Translate what you say
   - Bidirectional: Translate both directions
4. **Join your video call** (Zoom, Teams, Meet, etc.)
5. **Enable overlay** to see translations on screen

### Conversation Mode

For face-to-face conversations:

1. **Select "Conversation Mode"**
2. **Set up two language pairs** (e.g., English ↔ Japanese)
3. **Place device between speakers**
4. **Auto-detect speaker** feature identifies who's speaking
5. **Each person hears translation** in their language

### Batch Translation

For recorded audio files:

1. **Go to "File" → "Batch Translate"**
2. **Select audio files** (MP3, WAV, M4A supported)
3. **Choose output format**:
   - Transcript only
   - Translated audio
   - Subtitle file (SRT)
4. **Click "Process"** and wait for completion

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Start/Stop listening |
| `Ctrl + T` | Toggle translation |
| `Ctrl + R` | Record conversation |
| `Ctrl + S` | Save translation |
| `Ctrl + ,` | Open settings |
| `Esc` | Stop current operation |
| `F1` | Open help |

For complete usage instructions, see [User Guide](docs/user-guide.md).

---

## 🌍 Supported Languages

### Fully Supported Languages (50+)

| Language | Code | Speech Recognition | Translation | TTS |
|----------|------|-------------------|-------------|-----|
| English | en | ✅ | ✅ | ✅ |
| Chinese (Simplified) | zh-CN | ✅ | ✅ | ✅ |
| Chinese (Traditional) | zh-TW | ✅ | ✅ | ✅ |
| Japanese | ja | ✅ | ✅ | ✅ |
| French | fr | ✅ | ✅ | ✅ |
| German | de | ✅ | ✅ | ✅ |
| Spanish | es | ✅ | ✅ | ✅ |
| Italian | it | ✅ | ✅ | ✅ |
| Portuguese | pt | ✅ | ✅ | ✅ |
| Russian | ru | ✅ | ✅ | ✅ |
| Korean | ko | ✅ | ✅ | ✅ |
| Arabic | ar | ✅ | ✅ | ✅ |
| Hindi | hi | ✅ | ✅ | ✅ |
| ... and 37 more | | | | |

See [Supported Languages](docs/languages.md) for complete list.

---

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceTranslate Pro                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   GUI Layer  │  │  API Layer   │  │  Video Layer │      │
│  │  (PyQt6)     │  │  (FastAPI)   │  │  (WebRTC)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│  ┌──────┴─────────────────┴─────────────────┴───────┐      │
│  │              Core Translation Engine               │      │
│  ├───────────────────────────────────────────────────┤      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │      │
│  │  │   ASR    │  │    MT    │  │   TTS    │        │      │
│  │  │ (Whisper)│  │(DeepL/   │  │(Coqui/   │        │      │
│  │  │          │  │ Google)  │  │ Eleven)  │        │      │
│  │  └──────────┘  └──────────┘  └──────────┘        │      │
│  └───────────────────────────────────────────────────┘      │
│         │                 │                 │               │
│  ┌──────┴─────────────────┴─────────────────┴───────┐      │
│  │              Service Layer                         │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │      │
│  │  │  Audio   │  │  Config  │  │  Cache   │        │      │
│  │  │  Service │  │  Service │  │  Service │        │      │
│  │  └──────────┘  └──────────┘  └──────────┘        │      │
│  └───────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| GUI Framework | PyQt6 / PySide6 |
| Speech Recognition | OpenAI Whisper, Google Speech-to-Text |
| Machine Translation | DeepL API, Google Translate API |
| Text-to-Speech | Coqui TTS, ElevenLabs API |
| Video Processing | WebRTC, OpenCV |
| Audio Processing | PyAudio, librosa |
| Backend API | FastAPI |
| Database | SQLite (local), PostgreSQL (cloud) |
| Caching | Redis |

For detailed architecture documentation, see [Architecture Guide](docs/architecture.md).

---

## 📚 API Documentation

VoiceTranslate Pro provides a RESTful API for integration with other applications.

### API Endpoints

```
POST   /api/v1/translate/text       # Translate text
POST   /api/v1/translate/audio      # Translate audio file
POST   /api/v1/translate/stream     # Real-time translation stream
GET    /api/v1/languages            # List supported languages
GET    /api/v1/status               # Service status
```

### Example API Usage

```python
import requests

# Translate text
response = requests.post(
    'http://localhost:8000/api/v1/translate/text',
    json={
        'text': 'Hello, how are you?',
        'source_lang': 'en',
        'target_lang': 'zh'
    }
)
print(response.json())
# Output: {'translation': '你好，你好吗？', 'confidence': 0.98}
```

For complete API documentation, see [API Reference](docs/api-reference.md).

---

## 🧪 Testing

VoiceTranslate Pro includes comprehensive test coverage.

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_asr.py         # Speech recognition tests
│   ├── test_translation.py # Translation tests
│   ├── test_tts.py         # Text-to-speech tests
│   └── test_gui.py         # GUI tests
├── integration/            # Integration tests
│   ├── test_pipeline.py    # Full pipeline tests
│   └── test_api.py         # API endpoint tests
├── performance/            # Performance tests
│   ├── test_latency.py     # Latency benchmarks
│   └── test_throughput.py  # Throughput tests
├── e2e/                    # End-to-end tests
│   └── test_workflows.py   # User workflow tests
└── fixtures/               # Test data
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest --cov=voicetranslate_pro --cov-report=html

# Run performance tests
pytest tests/performance/ --benchmark-only
```

For detailed testing documentation, see [Test Plan](docs/test-plan.md).

---

## 🤝 Contributing

We welcome contributions from the community!

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Run tests** (`pytest`)
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

### Contribution Guidelines

- Follow [PEP 8](https://pep8.org/) style guidelines
- Write tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Use conventional commit messages

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run linting
flake8 voicetranslate_pro/
black voicetranslate_pro/

# Run type checking
mypy voicetranslate_pro/
```

For detailed contribution guidelines, see [Contributing Guide](docs/contributing.md).

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: Application won't start

**Solution:**
```bash
# Check Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check for conflicting packages
pip check
```

#### Issue: No audio input detected

**Solution:**
- Check microphone permissions in system settings
- Verify microphone is selected in app settings
- Test microphone with other applications
- Try different audio input device

#### Issue: Translations are inaccurate

**Solution:**
- Speak clearly and at moderate pace
- Reduce background noise
- Check internet connection
- Try different translation engine in settings

#### Issue: High latency in translation

**Solution:**
- Check internet connection speed
- Close other bandwidth-intensive applications
- Enable "Low Latency Mode" in settings
- Consider using local models for offline translation

### Getting Help

- 📖 [Documentation](https://docs.voicetranslate.pro)
- 💬 [Discussions](https://github.com/yourusername/voicetranslate-pro/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/voicetranslate-pro/issues)
- 📧 Email: support@voicetranslate.pro

For detailed troubleshooting, see [Troubleshooting Guide](docs/troubleshooting.md).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [DeepL API](https://www.deepl.com/pro-api) - Machine translation
- [Coqui TTS](https://github.com/coqui-ai/TTS) - Text-to-speech
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [FastAPI](https://fastapi.tiangolo.com/) - API framework

---

## 📞 Contact

- **Website**: [https://voicetranslate.pro](https://voicetranslate.pro)
- **Email**: contact@voicetranslate.pro
- **Twitter**: [@VoiceTranslate](https://twitter.com/Voicetranslate)
- **LinkedIn**: [VoiceTranslate Pro](https://linkedin.com/company/voicetranslate-pro)

---

<p align="center">
  Made with ❤️ by the VoiceTranslate Pro Team
</p>

<p align="center">
  <a href="#top">⬆️ Back to Top</a>
</p>
