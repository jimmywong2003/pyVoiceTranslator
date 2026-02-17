# Cross-Platform Compatibility Guide

## Voice Translation Application - Platform Support

This guide covers the cross-platform compatibility layer for the real-time voice translation application, supporting **macOS (Intel & Apple Silicon)** and **Windows 10/11**.

---

## Table of Contents

1. [Platform Overview](#platform-overview)
2. [Audio Capture Architecture](#audio-capture-architecture)
3. [ML Optimization](#ml-optimization)
4. [Environment Setup](#environment-setup)
5. [Building & Packaging](#building--packaging)
6. [Code Signing](#code-signing)
7. [Testing Strategy](#testing-strategy)
8. [Troubleshooting](#troubleshooting)

---

## Platform Overview

### Supported Platforms

| Platform | Architecture | Status | Notes |
|----------|-------------|--------|-------|
| macOS 11+ | Apple Silicon (M1/M2/M3) | ✅ Full Support | MPS acceleration, CoreAudio |
| macOS 11+ | Intel (x86_64) | ✅ Full Support | CoreAudio, Rosetta 2 compatible |
| Windows 10/11 | x86_64 | ✅ Full Support | WASAPI, CUDA/DirectML |

### Platform Detection

```python
from platform_utils import detect_platform, get_platform_info

# Detect current platform
platform_type = detect_platform()
# Returns: PlatformType.MACOS_APPLE_SILICON, MACOS_INTEL, or WINDOWS

# Get detailed info
info = get_platform_info()
print(f"Platform: {info.platform_type.value}")
print(f"Is Apple Silicon: {info.is_apple_silicon}")
print(f"Is Windows: {info.is_windows}")
```

---

## Audio Capture Architecture

### macOS (CoreAudio + BlackHole)

**Architecture:**
- **Microphone**: CoreAudio via `sounddevice` library
- **System Audio**: BlackHole virtual audio driver

**Setup:**
```bash
# Install BlackHole for system audio capture
brew install blackhole-2ch

# Or install BlackHole-16ch for multi-channel
brew install blackhole-16ch
```

**Configuration:**
1. Open Audio MIDI Setup (Applications > Utilities)
2. Create Multi-Output Device:
   - Click '+' → Create Multi-Output Device
   - Check both your speakers AND BlackHole
3. Set as default output in System Preferences → Sound

**Code Example:**
```python
from audio_platform import AudioConfig, create_audio_capture

# Configure audio
config = AudioConfig(
    sample_rate=16000,
    channels=1,
    chunk_size=1024
)

# Create microphone capture
mic_capture = create_audio_capture(config, capture_system_audio=False)

# Create system audio capture (requires BlackHole)
sys_capture = create_audio_capture(config, capture_system_audio=True)
```

### Windows (WASAPI + PyAudio)

**Architecture:**
- **Microphone**: WASAPI via `pyaudio` library
- **System Audio**: WASAPI loopback mode

**Setup:**
```bash
# PyAudio is included in requirements-windows.txt
# If installation fails, use:
pip install pipwin
pipwin install pyaudio
```

**Code Example:**
```python
from audio_platform import AudioConfig, create_audio_capture

config = AudioConfig(sample_rate=16000)

# Microphone capture
mic_capture = create_audio_capture(config, capture_system_audio=False)

# System audio capture (loopback)
sys_capture = create_audio_capture(config, capture_system_audio=True)
```

### Unified Audio Interface

```python
from audio_platform import UnifiedAudioCapture, AudioConfig

# Create unified interface
audio = UnifiedAudioCapture(AudioConfig())
audio.initialize(capture_microphone=True, capture_system=False)

# List all devices
devices = audio.list_all_devices()

# Start capture
def process_audio(data):
    # Process audio chunk
    pass

audio.start_microphone_capture(process_audio)
```

---

## ML Optimization

### Apple Silicon (M1/M2/M3) - MPS

**Features:**
- Metal Performance Shaders (MPS) backend
- ~20-30% speedup with `torch.compile`
- FP16 support for memory efficiency

**Setup:**
```python
from ml_platform import MLPlatformConfig, create_optimizer

config = MLPlatformConfig(device='auto', precision='fp32')
optimizer = create_optimizer(config)

# Optimize model
model = optimizer.optimize_model(your_model)
```

**Environment Variables:**
```bash
# Remove MPS memory limits
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
```

**Recommendations:**
- Use PyTorch 2.0+ for `torch.compile` support
- Consider CoreML conversion for production
- Enable gradient checkpointing for large models

### Windows - CUDA/DirectML

**Features:**
- CUDA support for NVIDIA GPUs
- DirectML for AMD/Intel GPUs
- Automatic Mixed Precision (AMP)

**Setup:**
```python
from ml_platform import MLPlatformConfig, create_optimizer

# For CUDA
config = MLPlatformConfig(device='cuda', precision='fp16')

# For DirectML (AMD/Intel)
config = MLPlatformConfig(device='directml', precision='fp32')

optimizer = create_optimizer(config)
model = optimizer.optimize_model(your_model)
```

**CUDA Installation:**
```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**DirectML Installation:**
```bash
pip install torch-directml
```

### Model-Specific Optimizations

**Whisper Models:**
```python
from ml_platform import WhisperOptimizer

# Optimize Whisper for platform
model = WhisperOptimizer.optimize_for_platform(
    model, 
    platform='macos_apple_silicon',
    config=ml_config
)
```

**Batch Size Recommendations:**

| Model | Apple Silicon | Intel | Windows CUDA |
|-------|--------------|-------|--------------|
| tiny | 8 | 4 | 16 |
| base | 4 | 2 | 8 |
| small | 2 | 1 | 4 |
| medium | 1 | 1 | 2 |
| large | 1 | 1 | 1 |

---

## Environment Setup

### macOS Apple Silicon (M1/M2/M3)

**Option 1: Conda (Recommended)**
```bash
# Create environment
conda env create -f environment-macos-arm64.yml
conda activate voice-translate-arm64

# Verify MPS
python -c "import torch; print(torch.backends.mps.is_available())"
```

**Option 2: Pip**
```bash
# Install ARM64 Python from python.org
pip install -r requirements-macos-arm64.txt
```

**Prerequisites:**
```bash
# Install Homebrew packages
brew install portaudio ffmpeg blackhole-2ch
```

### macOS Intel

```bash
conda env create -f environment-macos-arm64.yml
conda activate voice-translate-arm64
```

### Windows

**Option 1: Conda (Recommended)**
```bash
conda env create -f environment-windows.yml
conda activate voice-translate-win
```

**Option 2: Pip**
```bash
pip install -r requirements-windows.txt
```

**Prerequisites:**
- Visual C++ Redistributables
- FFmpeg (via chocolatey: `choco install ffmpeg`)

---

## Building & Packaging

### macOS

**Build Universal2 App (Intel + Apple Silicon):**
```bash
# Using py2app
python setup.py py2app

# Or using PyInstaller
pyinstaller config/voice-translate-macos.spec --target-arch universal2
```

**Output:**
- `dist/VoiceTranslate.app` - macOS app bundle

**Create DMG Installer:**
```bash
create-dmg \
  --volname "VoiceTranslate Installer" \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "VoiceTranslate.dmg" \
  "dist/VoiceTranslate.app"
```

### Windows

**Build Executable:**
```bash
pyinstaller config/voice-translate-windows.spec
```

**Output:**
- `dist/VoiceTranslate.exe` - Single executable
- `dist/VoiceTranslate/` - Folder distribution

**Create Installer (Inno Setup):**
```bash
iscc config/installer.iss
```

### Build Matrix

| Platform | Tool | Output | Size (approx) |
|----------|------|--------|---------------|
| macOS Universal2 | py2app | .app | 500MB |
| macOS Universal2 | PyInstaller | .app | 450MB |
| Windows | PyInstaller | .exe | 400MB |

---

## Code Signing

### macOS

**Requirements:**
- Apple Developer ID
- Developer ID Application certificate

**Sign App:**
```bash
# Sign the app bundle
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name" \
  dist/VoiceTranslate.app

# Verify signature
codesign --verify --verbose dist/VoiceTranslate.app

# Notarize (for distribution)
xcrun altool --notarize-app \
  --primary-bundle-id "com.yourcompany.voicetranslate" \
  --username "your@email.com" \
  --password "@keychain:AC_PASSWORD" \
  --file VoiceTranslate.dmg
```

**Entitlements:**
```xml
<!-- config/entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.device.microphone</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
</dict>
</plist>
```

### Windows

**Requirements:**
- Code signing certificate (DigiCert, Sectigo, etc.)
- Windows SDK (signtool)

**Sign Executable:**
```powershell
# Sign with certificate
signtool sign `
  /f certificate.pfx `
  /p password `
  /tr http://timestamp.digicert.com `
  /td sha256 `
  /fd sha256 `
  dist/VoiceTranslate.exe

# Verify signature
signtool verify /pa dist/VoiceTranslate.exe
```

---

## Testing Strategy

### Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run platform-specific tests
python -m pytest tests/test_platform.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Platform-Specific Tests

```python
# tests/test_platform.py
from platform_utils import detect_platform, PlatformType

def test_audio_capture():
    platform = detect_platform()
    
    if platform.value.startswith('macos'):
        test_macos_audio()
    elif platform == PlatformType.WINDOWS:
        test_windows_audio()
```

### CI/CD Testing

GitHub Actions runs tests on:
- macOS 13 (Intel)
- macOS 14 (Apple Silicon)
- Windows Latest

See `.github/workflows/build.yml`

---

## Troubleshooting

### macOS

**Issue: MPS not available**
```bash
# Check PyTorch installation
python -c "import torch; print(torch.__version__)"

# Reinstall with MPS support
pip install --upgrade torch torchvision torchaudio
```

**Issue: BlackHole not found**
```bash
# Verify installation
system_profiler SPAudioDataType | grep -i blackhole

# Reinstall
brew reinstall blackhole-2ch
```

**Issue: Microphone permission denied**
- Grant permission in System Preferences → Security & Privacy → Microphone

### Windows

**Issue: PyAudio installation fails**
```bash
# Use pipwin
pip install pipwin
pipwin install pyaudio

# Or download wheel manually
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
```

**Issue: CUDA not available**
```bash
# Check CUDA version
nvidia-smi

# Verify PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

**Issue: WASAPI loopback not working**
- Ensure Windows 10 version 1903+ or Windows 11
- Check audio drivers are up to date

### General

**Issue: Model loading is slow**
- Use smaller model (tiny/base)
- Enable FP16 precision
- Use SSD for model storage

**Issue: High CPU usage**
- Reduce sample rate (8000Hz for speech)
- Increase chunk size
- Use platform-specific optimizations

---

## Performance Benchmarks

### Whisper Model Inference (seconds per 30s audio)

| Platform | tiny | base | small | medium |
|----------|------|------|-------|--------|
| M1 Pro (MPS) | 0.5 | 1.2 | 3.5 | 10.2 |
| Intel i7 (CPU) | 1.2 | 3.0 | 9.0 | 25.0 |
| RTX 3060 (CUDA) | 0.3 | 0.8 | 2.5 | 7.0 |
| Ryzen 5 (CPU) | 1.5 | 3.5 | 11.0 | 30.0 |

---

## References

- [PyTorch MPS Documentation](https://pytorch.org/docs/stable/notes/mps.html)
- [BlackHole GitHub](https://github.com/ExistentialAudio/BlackHole)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [Apple Code Signing](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac)

---

## License

MIT License - See LICENSE file for details
