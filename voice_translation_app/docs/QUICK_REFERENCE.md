# Cross-Platform Development Quick Reference

## Platform Detection

```python
from platform_utils import detect_platform, get_platform_info, PlatformType

# Quick detection
platform = detect_platform()

# Check platform type
if platform == PlatformType.MACOS_APPLE_SILICON:
    # Apple Silicon specific code
    pass
elif platform == PlatformType.WINDOWS:
    # Windows specific code
    pass

# Get detailed info
info = get_platform_info()
print(f"Is Apple Silicon: {info.is_apple_silicon}")
print(f"Is Windows: {info.is_windows}")
```

## Platform Decorators

```python
from platform_utils import macos_only, windows_only, apple_silicon_only

@macos_only
def macos_specific_function():
    """Only runs on macOS"""
    pass

@windows_only
def windows_specific_function():
    """Only runs on Windows"""
    pass

@apple_silicon_only
def apple_silicon_specific_function():
    """Only runs on Apple Silicon"""
    pass
```

## Audio Capture

```python
from audio_platform import AudioConfig, create_audio_capture, UnifiedAudioCapture

# Basic configuration
config = AudioConfig(
    sample_rate=16000,
    channels=1,
    chunk_size=1024
)

# Method 1: Factory function
mic = create_audio_capture(config, capture_system_audio=False)
sys_audio = create_audio_capture(config, capture_system_audio=True)

# Method 2: Unified interface
audio = UnifiedAudioCapture(config)
audio.initialize(capture_microphone=True, capture_system=True)

# List devices
devices = audio.list_all_devices()

# Start capture with callback
import numpy as np

def process_audio(data: np.ndarray):
    print(f"Received {len(data)} samples")

audio.start_microphone_capture(process_audio)
audio.stop_all()
```

## ML Optimization

```python
from ml_platform import MLPlatformConfig, create_optimizer

# Configuration
config = MLPlatformConfig(
    device='auto',      # auto, cpu, cuda, mps, directml
    precision='fp32',   # fp32, fp16, int8
    batch_size=1
)

# Create optimizer
optimizer = create_optimizer(config)

# Optimize model
model = optimizer.optimize_model(your_model)

# Get device info
info = optimizer.get_device_info()
print(f"Device: {info['device']}")
```

## Platform Paths

```python
from platform_utils import PlatformPaths

paths = PlatformPaths("VoiceTranslate")

# Get directories
config_dir = paths.get_config_dir()
cache_dir = paths.get_cache_dir()
log_dir = paths.get_log_dir()
models_dir = paths.get_models_dir()

# Create all directories
paths.ensure_dirs()
```

## Dependency Checking

```python
from platform_utils import DependencyChecker

checker = DependencyChecker()
results = checker.check_all()

if results['all_ok']:
    print("All dependencies satisfied")
else:
    print(f"Missing: {results['missing']}")
    print(f"Warnings: {results['warnings']}")
```

## Environment Setup

```python
from platform_utils import setup_environment, get_optimal_thread_count

# Setup optimal environment
setup_environment()

# Get optimal thread count
threads = get_optimal_thread_count()
```

## Build Commands

### macOS

```bash
# Conda environment
conda env create -f environment-macos-arm64.yml
conda activate voice-translate-arm64

# Build with py2app
python setup.py py2app

# Build with PyInstaller
pyinstaller config/voice-translate-macos.spec --target-arch universal2

# Create DMG
create-dmg --volname "VoiceTranslate" \
    --app-drop-link 600 185 \
    "VoiceTranslate.dmg" \
    "dist/VoiceTranslate.app"

# Code sign
codesign --deep --force --sign "Developer ID" dist/VoiceTranslate.app
```

### Windows

```bash
# Conda environment
conda env create -f environment-windows.yml
conda activate voice-translate-win

# Build with PyInstaller
pyinstaller config/voice-translate-windows.spec

# Sign executable
signtool sign /f cert.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 dist/VoiceTranslate.exe
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run platform tests only
python -m pytest tests/test_platform.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test
python -m pytest tests/test_platform.py::TestPlatformDetection -v
```

## Common Issues

### macOS

```bash
# MPS not available
python -c "import torch; print(torch.backends.mps.is_available())"

# BlackHole not found
brew reinstall blackhole-2ch
system_profiler SPAudioDataType | grep -i blackhole

# Permission denied
# Grant in System Preferences > Security & Privacy > Microphone
```

### Windows

```bash
# PyAudio install fails
pip install pipwin
pipwin install pyaudio

# CUDA not available
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

## CI/CD Variables

### GitHub Actions Secrets

- `MACOS_CERTIFICATE` - Base64-encoded Developer ID certificate
- `MACOS_CERTIFICATE_PWD` - Certificate password
- `WINDOWS_CERTIFICATE` - Base64-encoded code signing certificate
- `WINDOWS_CERTIFICATE_PWD` - Certificate password

## File Extensions

```python
from platform_utils import get_executable_extension, get_library_extension

exe_ext = get_executable_extension()  # '' on macOS, '.exe' on Windows
lib_ext = get_library_extension()     # '.dylib' on macOS, '.dll' on Windows
```

## Audio Settings by Platform

```python
from platform_utils import AudioPlatformHelper

helper = AudioPlatformHelper()

# Get recommended settings
sample_rate = helper.get_recommended_sample_rate()  # 16000
buffer_size = helper.get_recommended_buffer_size()  # 512 (Apple Silicon), 1024 (Windows)

# Check permissions
has_permission = helper.check_audio_permissions()
```

## Model Batch Sizes

```python
from ml_platform import get_optimal_batch_size

# Get optimal batch size for platform and model
batch_size = get_optimal_batch_size('macos_apple_silicon', 'base')  # 4
batch_size = get_optimal_batch_size('windows', 'small')             # 4
```
