# VoiceTranslate Pro - Setup Guide

> Step-by-step guide to set up the development environment for VoiceTranslate Pro.

## Prerequisites

- **Python 3.9+** installed
- **Virtual environment** created and activated
- Platform-specific package manager (Homebrew for macOS, winget for Windows, apt for Linux)

---

## Quick Start (Automated)

Run the setup script to validate and auto-install dependencies:

```bash
# Check current environment status
python setup_environment.py

# Auto-install all missing dependencies
python setup_environment.py --install-all

# Print manual checklist
python setup_environment.py --print-checklist
```

---

## Manual Setup Checklist

### Step 1: Python Environment ✅

You mentioned this is already done, but verify:

```bash
# Check Python version (should be 3.9+)
python --version

# Verify virtual environment is active
which python  # macOS/Linux
where python  # Windows

# Should show path inside venv, e.g.:
# /path/to/project/venv/bin/python  (macOS/Linux)
# C:\path\to\project\venv\Scripts\python.exe  (Windows)
```

### Step 2: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 3: Install System Dependencies

<details>
<summary><b>🍎 macOS (Apple Silicon & Intel)</b></summary>

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install audio and video dependencies
brew install portaudio ffmpeg
```

</details>

<details>
<summary><b>🪟 Windows 10/11</b></summary>

```powershell
# Using winget (recommended)
winget install FFmpeg

# Or download from https://ffmpeg.org/download.html
# Add to PATH after installation
```

**Note:** PyAudio on Windows may require manual wheel installation:
```bash
pip install pipwin
pipwin install pyaudio
```

</details>

<details>
<summary><b>🐧 Linux (Ubuntu/Debian)</b></summary>

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev ffmpeg
```

</details>

### Step 4: Install Python Dependencies

Since you already have requirements.txt installed, let's verify and add platform-specific packages:

<details>
<summary><b>🍎 macOS Apple Silicon (M1/M2/M3)</b></summary>

```bash
# Install base + ARM64 optimized packages
pip install -r voice_translation_app/requirements-macos-arm64.txt

# Or manually install PyTorch with MPS support:
pip install torch torchvision torchaudio
```

</details>

<details>
<summary><b>🍎 macOS Intel</b></summary>

```bash
pip install -r voice_translation_app/requirements.txt

# Install PyTorch (CPU version recommended for Intel Mac)
pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cpu
```

</details>

<details>
<summary><b>🪟 Windows</b></summary>

```bash
pip install -r voice_translation_app/requirements-windows.txt

# For CUDA 11.8 support:
pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu118
```

</details>

### Step 5: Verify Installation

```bash
# Run the setup validation script
python setup_environment.py

# Test audio device detection
python voice_translation_app/src/main.py --list-devices

# Check all dependencies
python voice_translation_app/src/main.py --check-deps
```

### Step 6: (Optional) Run Tests

```bash
# Run unit tests
python -m pytest voice_translation_app/tests/ -v

# Or run directly
python voice_translation_app/tests/test_platform.py
```

---

## Troubleshooting

### Issue: `sounddevice` import error

**Cause:** PortAudio not installed

**Fix:**
- macOS: `brew install portaudio`
- Linux: `sudo apt-get install portaudio19-dev`
- Windows: Should work with pip-installed PyAudio

### Issue: PyAudio installation fails

**Fix for Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

**Fix for macOS:**
```bash
brew install portaudio
pip install PyAudio
```

### Issue: FFmpeg not found

**Fix:**
- macOS: `brew install ffmpeg`
- Windows: `winget install FFmpeg`
- Linux: `sudo apt-get install ffmpeg`

### Issue: CUDA not available on Windows

**Check:** PyTorch installed with CUDA support?
```python
import torch
print(torch.cuda.is_available())  # Should print True
```

**Fix:** Reinstall PyTorch with CUDA:
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu118
```

### Issue: MPS not available on Apple Silicon

**Check:**
```python
import torch
print(torch.backends.mps.is_available())  # Should print True
```

**Fix:** Use native ARM64 PyTorch (not x86_64 through Rosetta):
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio
```

---

## Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
# Debug mode
DEBUG=true

# Model cache directory
MODEL_CACHE_DIR=~/.voice_translate/models

# Audio device index (use --list-devices to find)
DEFAULT_INPUT_DEVICE=0

# API keys (if using cloud translation)
# OPENAI_API_KEY=your_key_here
```

---

## Post-Setup Commands

| Command | Description |
|---------|-------------|
| `python voice_translation_app/src/main.py` | Launch the application |
| `python voice_translation_app/src/main.py --list-devices` | List audio devices |
| `python voice_translation_app/src/main.py --check-deps` | Verify dependencies |
| `python voice_translation_app/src/main.py --system-audio` | Capture system audio |
| `python -m pytest voice_translation_app/tests/ -v` | Run tests |
| `python setup_environment.py` | Validate environment |

---

## Directory Structure Reference

```
.
├── requirements.txt                      # Core audio module deps
├── voice_translation_app/
│   ├── requirements.txt                  # Base app deps
│   ├── requirements-macos-arm64.txt      # Apple Silicon
│   ├── requirements-windows.txt          # Windows
│   └── src/main.py                       # App entry point
└── setup_environment.py                  # This setup script
```

---

## Need Help?

1. Check the detailed documentation in `docs/installation.md`
2. Review `AGENTS.md` for architecture overview
3. Run `python setup_environment.py --print-checklist` for platform-specific steps
