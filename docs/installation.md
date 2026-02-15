# Installation Guide

## VoiceTranslate Pro - Complete Installation Instructions

This guide provides detailed installation instructions for VoiceTranslate Pro on Windows, macOS, and Linux systems.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Windows Installation](#windows-installation)
3. [macOS Installation](#macos-installation)
4. [Linux Installation](#linux-installation)
5. [Development Installation](#development-installation)
6. [Configuration](#configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Windows 10/11, macOS 10.15+, Ubuntu 20.04+ |
| Processor | Intel Core i3 / AMD Ryzen 3 (or equivalent) |
| RAM | 4 GB |
| Storage | 2 GB free space |
| Internet | Broadband connection (10 Mbps+) |
| Microphone | Built-in or external |
| Display | 1280x720 resolution |

### Recommended Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Windows 11, macOS 12+, Ubuntu 22.04+ |
| Processor | Intel Core i5 / AMD Ryzen 5 (or equivalent) |
| RAM | 8 GB or more |
| Storage | 5 GB free space (SSD recommended) |
| Internet | High-speed connection (50 Mbps+) |
| Microphone | High-quality external microphone |
| GPU | NVIDIA GPU with CUDA support (optional) |
| Display | 1920x1080 resolution or higher |

### GPU Acceleration (Optional)

For enhanced performance, especially with local speech recognition models:

- **NVIDIA GPU**: CUDA 11.8+ compatible
- **AMD GPU**: ROCm support (Linux only)
- **Apple Silicon**: M1/M2/M3 (macOS)

---

## Windows Installation

### Method 1: Installer (Recommended)

#### Step 1: Download the Installer

```powershell
# Using PowerShell
Invoke-WebRequest -Uri "https://github.com/yourusername/voicetranslate-pro/releases/latest/download/VoiceTranslatePro-Setup.exe" -OutFile "VoiceTranslatePro-Setup.exe"
```

Or download directly from the [releases page](https://github.com/yourusername/voicetranslate-pro/releases).

#### Step 2: Run the Installer

1. Double-click `VoiceTranslatePro-Setup.exe`
2. If Windows SmartScreen appears, click "More info" → "Run anyway"
3. Follow the installation wizard:
   - Accept the license agreement
   - Choose installation location (default: `C:\Program Files\VoiceTranslate Pro`)
   - Select components to install
   - Create desktop shortcut (optional)

#### Step 3: Complete Installation

```powershell
# Verify installation
& "C:\Program Files\VoiceTranslate Pro\voicetranslate-pro.exe" --version
```

### Method 2: Windows Package Manager (winget)

```powershell
# Install using winget
winget install VoiceTranslatePro

# Verify installation
voicetranslate-pro --version
```

### Method 3: Chocolatey

```powershell
# Install Chocolatey if not already installed
# Then install VoiceTranslate Pro
choco install voicetranslate-pro

# Verify installation
voicetranslate-pro --version
```

### Method 4: Python pip (Advanced)

```powershell
# Ensure Python 3.9+ is installed
python --version

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install VoiceTranslate Pro
pip install voicetranslate-pro

# Run the application
python -m voicetranslate_pro
```

### Windows-Specific Configuration

#### Microphone Permissions

1. Open Windows Settings → Privacy → Microphone
2. Enable "Allow apps to access your microphone"
3. Ensure VoiceTranslate Pro is in the allowed apps list

#### Audio Device Setup

```powershell
# List available audio devices
python -m voicetranslate_pro --list-audio-devices

# Set default input device
python -m voicetranslate_pro --set-input-device "Microphone Name"
```

---

## macOS Installation

### Method 1: Homebrew (Recommended)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install VoiceTranslate Pro
brew install --cask voicetranslate-pro

# Verify installation
voicetranslate-pro --version
```

### Method 2: DMG Installer

#### Step 1: Download the DMG

```bash
# Download using curl
curl -L -o VoiceTranslatePro.dmg "https://github.com/yourusername/voicetranslate-pro/releases/latest/download/VoiceTranslatePro.dmg"
```

#### Step 2: Mount and Install

```bash
# Mount the DMG
hdiutil attach VoiceTranslatePro.dmg

# Copy to Applications
cp -R "/Volumes/VoiceTranslate Pro/VoiceTranslate Pro.app" /Applications/

# Unmount the DMG
hdiutil detach "/Volumes/VoiceTranslate Pro"
```

#### Step 3: First Launch

1. Open Finder → Applications
2. Right-click "VoiceTranslate Pro" → "Open"
3. If Gatekeeper warning appears, click "Open" in System Preferences → Security & Privacy

### Method 3: MacPorts

```bash
# Install MacPorts if not already installed
# Then install VoiceTranslate Pro
sudo port install voicetranslate-pro

# Verify installation
voicetranslate-pro --version
```

### Method 4: Python pip (Advanced)

```bash
# Ensure Python 3.9+ is installed
python3 --version

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install VoiceTranslate Pro
pip install voicetranslate-pro

# Run the application
python -m voicetranslate_pro
```

### macOS-Specific Configuration

#### Microphone Permissions

1. Open System Preferences → Security & Privacy → Privacy → Microphone
2. Check the box next to "VoiceTranslate Pro"

#### Accessibility Permissions (for global shortcuts)

1. Open System Preferences → Security & Privacy → Privacy → Accessibility
2. Click the lock to make changes
3. Add "VoiceTranslate Pro" to the list

#### Apple Silicon (M1/M2/M3) Optimization

```bash
# Install Rosetta 2 if not already installed
softwareupdate --install-rosetta --agree-to-license

# For optimal performance on Apple Silicon
pip install voicetranslate-pro[apple-silicon]
```

---

## Linux Installation

### Ubuntu/Debian

#### Method 1: DEB Package

```bash
# Download the DEB package
wget https://github.com/yourusername/voicetranslate-pro/releases/latest/download/voicetranslate-pro.deb

# Install the package
sudo dpkg -i voicetranslate-pro.deb

# Fix any dependency issues
sudo apt-get install -f

# Verify installation
voicetranslate-pro --version
```

#### Method 2: APT Repository

```bash
# Add the repository
echo "deb https://apt.voicetranslate.pro stable main" | sudo tee /etc/apt/sources.list.d/voicetranslate-pro.list

# Add the GPG key
wget -qO - https://apt.voicetranslate.pro/gpg.key | sudo apt-key add -

# Update and install
sudo apt-get update
sudo apt-get install voicetranslate-pro

# Verify installation
voicetranslate-pro --version
```

#### Method 3: Snap

```bash
# Install using snap
sudo snap install voicetranslate-pro

# Connect required interfaces
sudo snap connect voicetranslate-pro:audio-record
sudo snap connect voicetranslate-pro:network

# Verify installation
voicetranslate-pro --version
```

### Fedora/RHEL/CentOS

```bash
# Download the RPM package
wget https://github.com/yourusername/voicetranslate-pro/releases/latest/download/voicetranslate-pro.rpm

# Install the package
sudo rpm -i voicetranslate-pro.rpm

# Or using dnf
sudo dnf install voicetranslate-pro.rpm

# Verify installation
voicetranslate-pro --version
```

### Arch Linux

```bash
# Using yay (AUR helper)
yay -S voicetranslate-pro

# Or manually from AUR
git clone https://aur.archlinux.org/voicetranslate-pro.git
cd voicetranslate-pro
makepkg -si

# Verify installation
voicetranslate-pro --version
```

### Linux-Specific Configuration

#### Audio Permissions

```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Log out and log back in for changes to take effect
```

#### ALSA/PulseAudio Configuration

```bash
# List audio devices
arecord -l

# Test microphone
arecord -d 5 test.wav && aplay test.wav

# Configure default device in ~/.asoundrc
cat > ~/.asoundrc << EOF
pcm.!default {
    type hw
    card 0
    device 0
}
EOF
```

---

## Development Installation

### Prerequisites

- Python 3.9 or higher
- Git
- C++ compiler (for some dependencies)
- CUDA toolkit (optional, for GPU acceleration)

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/voicetranslate-pro.git
cd voicetranslate-pro

# Checkout specific version (optional)
git checkout v1.0.0
```

#### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

#### 3. Install Dependencies

```bash
# Install base dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install with all optional features
pip install -e ".[all]"

# Or install specific features
pip install -e ".[gpu,apple-silicon,docs]"
```

#### 4. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually (optional)
pre-commit run --all-files
```

#### 5. Verify Installation

```bash
# Run tests
pytest tests/unit/ -v

# Run the application
python -m voicetranslate_pro

# Check version
python -m voicetranslate_pro --version
```

### Development Dependencies

```bash
# Core development tools
pip install pytest pytest-cov black flake8 mypy

# Documentation tools
pip install sphinx sphinx-rtd-theme

# Performance testing
pip install pytest-benchmark

# GUI testing
pip install pytest-qt
```

---

## Configuration

### Initial Setup

#### 1. API Keys Configuration

Create a configuration file at `~/.voicetranslate-pro/config.yaml`:

```yaml
# API Configuration
api:
  deepl:
    api_key: "your-deepl-api-key"
    enabled: true
  
  google:
    api_key: "your-google-api-key"
    enabled: true
  
  elevenlabs:
    api_key: "your-elevenlabs-api-key"
    enabled: true

# Audio Configuration
audio:
  input_device: "default"
  output_device: "default"
  sample_rate: 16000
  chunk_size: 1024

# Translation Configuration
translation:
  default_source: "en"
  default_target: "zh"
  auto_detect: true
  
# GUI Configuration
gui:
  theme: "dark"
  language: "en"
  font_size: 12
```

#### 2. Environment Variables

```bash
# Set API keys as environment variables
export DEEPL_API_KEY="your-deepl-api-key"
export GOOGLE_API_KEY="your-google-api-key"
export ELEVENLABS_API_KEY="your-elevenlabs-api-key"

# Set configuration path
export VOICETRANSLATE_CONFIG="/path/to/config.yaml"
```

#### 3. First Run Setup

```bash
# Run initial setup wizard
voicetranslate-pro --setup

# This will:
# - Detect audio devices
# - Test microphone
# - Configure API keys
# - Set default languages
# - Test internet connection
```

### Advanced Configuration

#### GPU Configuration

```yaml
# config.yaml
gpu:
  enabled: true
  device: "cuda:0"  # or "auto" for automatic selection
  memory_fraction: 0.8
  
asr:
  model: "whisper-large-v3"
  device: "cuda"
  compute_type: "float16"
```

#### Offline Mode Configuration

```yaml
# config.yaml
offline:
  enabled: true
  models_path: "~/.voicetranslate-pro/models"
  
asr:
  model: "whisper-base"  # Smaller model for local use
  device: "cpu"
  
translation:
  engine: "local"  # Use local translation model
  model: "opus-mt"
```

---

## Verification

### Basic Verification

```bash
# Check version
voicetranslate-pro --version

# Check system requirements
voicetranslate-pro --check-system

# List audio devices
voicetranslate-pro --list-audio-devices

# Test microphone
voicetranslate-pro --test-microphone

# Test internet connection
voicetranslate-pro --test-connection
```

### Full System Test

```bash
# Run comprehensive test suite
voicetranslate-pro --test-all

# Expected output:
# ✓ Python version: 3.9.7
# ✓ Audio devices detected: 3
# ✓ Microphone test: PASSED
# ✓ Internet connection: PASSED
# ✓ API connectivity: PASSED
# ✓ GPU available: YES (NVIDIA RTX 3080)
# ✓ All tests passed!
```

### GUI Test

```bash
# Launch GUI
voicetranslate-pro --gui

# Or simply
voicetranslate-pro
```

---

## Troubleshooting

### Common Installation Issues

#### Issue: "Python version not supported"

**Solution:**
```bash
# Check Python version
python --version  # Should be 3.9+

# Install Python 3.9+
# Windows: Download from python.org
# macOS: brew install python@3.9
# Ubuntu: sudo apt-get install python3.9
```

#### Issue: "Permission denied" (Linux/macOS)

**Solution:**
```bash
# Fix permissions
sudo chown -R $USER:$USER /path/to/installation

# Or use --user flag
pip install --user voicetranslate-pro
```

#### Issue: "PortAudio not found"

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# macOS
brew install portaudio

# Fedora
sudo dnf install portaudio-devel

# Then reinstall
pip install --force-reinstall pyaudio
```

#### Issue: "CUDA not available"

**Solution:**
```bash
# Check CUDA installation
nvidia-smi

# Install CUDA toolkit
# Download from https://developer.nvidia.com/cuda-downloads

# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Issue: "Microphone not detected"

**Solution:**
```bash
# List audio devices
voicetranslate-pro --list-audio-devices

# Test with arecord (Linux)
arecord -l

# Check system settings
# Windows: Settings → Privacy → Microphone
# macOS: System Preferences → Security & Privacy → Microphone
```

### Getting Help

If you encounter issues not covered here:

1. Check the [FAQ](faq.md)
2. Search [existing issues](https://github.com/yourusername/voicetranslate-pro/issues)
3. Join our [Discord community](https://discord.gg/voicetranslate)
4. Email support: support@voicetranslate.pro

---

## Uninstallation

### Windows

```powershell
# Using Settings app
# Settings → Apps → VoiceTranslate Pro → Uninstall

# Or using PowerShell
Get-Package -Name "VoiceTranslate Pro" | Uninstall-Package
```

### macOS

```bash
# Remove application
rm -rf /Applications/VoiceTranslate\ Pro.app

# Remove configuration
rm -rf ~/.voicetranslate-pro

# Remove using Homebrew
brew uninstall --cask voicetranslate-pro
```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get remove voicetranslate-pro
sudo apt-get autoremove

# Fedora
sudo dnf remove voicetranslate-pro

# Snap
sudo snap remove voicetranslate-pro
```

### Python pip

```bash
# Uninstall package
pip uninstall voicetranslate-pro

# Remove virtual environment
rm -rf venv/

# Remove configuration
rm -rf ~/.voicetranslate-pro
```

---

## Next Steps

After successful installation:

1. Read the [User Guide](user-guide.md)
2. Explore [Configuration Options](configuration.md)
3. Review [API Documentation](api-reference.md)
4. Join the [Community](https://community.voicetranslate.pro)
