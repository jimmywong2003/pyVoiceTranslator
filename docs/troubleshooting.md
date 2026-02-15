# Troubleshooting Guide

## VoiceTranslate Pro - Problem Resolution Guide

This guide helps you diagnose and resolve common issues with VoiceTranslate Pro.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Audio Problems](#audio-problems)
4. [Translation Issues](#translation-issues)
5. [Performance Issues](#performance-issues)
6. [Network Issues](#network-issues)
7. [GUI Issues](#gui-issues)
8. [API Issues](#api-issues)
9. [Error Codes](#error-codes)
10. [Getting Help](#getting-help)

---

## Quick Diagnostics

Run the built-in diagnostic tool:

```bash
voicetranslate-pro --diagnose
```

This will check:
- System requirements
- Audio devices
- Network connectivity
- API keys
- Dependencies

### Diagnostic Output Example

```
✓ Python version: 3.9.7 (required: 3.9+)
✓ Operating System: Windows 11
✓ RAM: 16 GB (required: 4 GB)
✓ Audio devices: 3 detected
  - Microphone (Realtek Audio)
  - Headset Microphone
  - Line In
✓ Internet connection: 85 Mbps
✓ API connectivity: Connected
✓ GPU: NVIDIA RTX 3080 (CUDA 11.8)
✓ All checks passed!
```

---

## Installation Issues

### Issue: "Python version not supported"

**Symptoms:**
```
Error: Python 3.9 or higher is required
```

**Solutions:**

1. **Check Python version:**
   ```bash
   python --version
   python3 --version
   ```

2. **Install Python 3.9+:**
   - **Windows**: Download from [python.org](https://python.org)
   - **macOS**: `brew install python@3.9`
   - **Ubuntu**: `sudo apt-get install python3.9`

3. **Use pyenv (recommended for development):**
   ```bash
   # Install pyenv
   curl https://pyenv.run | bash
   
   # Install Python 3.9
   pyenv install 3.9.18
   pyenv global 3.9.18
   ```

### Issue: "Permission denied" during installation

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied
```

**Solutions:**

1. **Use virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install voicetranslate-pro
   ```

2. **Use --user flag:**
   ```bash
   pip install --user voicetranslate-pro
   ```

3. **Fix permissions (Linux/macOS):**
   ```bash
   sudo chown -R $USER:$USER /path/to/installation
   ```

### Issue: "PortAudio not found"

**Symptoms:**
```
OSError: PortAudio library not found
```

**Solutions:**

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
pip install --force-reinstall pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install --force-reinstall pyaudio
```

**Windows:**
```bash
# Download PortAudio from https://www.portaudio.com
# Or use pre-built wheel:
pip install pipwin
pipwin install pyaudio
```

### Issue: "CUDA not available" for GPU acceleration

**Symptoms:**
```
Warning: CUDA is not available, using CPU
```

**Solutions:**

1. **Check NVIDIA GPU:**
   ```bash
   nvidia-smi
   ```

2. **Install CUDA Toolkit:**
   - Download from [NVIDIA CUDA](https://developer.nvidia.com/cuda-downloads)
   - Follow installation instructions for your OS

3. **Install PyTorch with CUDA:**
   ```bash
   # For CUDA 11.8
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # For CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

4. **Verify CUDA is available:**
   ```python
   import torch
   print(torch.cuda.is_available())
   print(torch.cuda.get_device_name(0))
   ```

---

## Audio Problems

### Issue: No microphone detected

**Symptoms:**
- "No audio input device found" error
- Microphone not listed in settings

**Solutions:**

1. **Check system settings:**
   - **Windows**: Settings → Privacy → Microphone → Allow apps to access microphone
   - **macOS**: System Preferences → Security & Privacy → Microphone
   - **Linux**: Check ALSA/PulseAudio settings

2. **List available devices:**
   ```bash
   voicetranslate-pro --list-audio-devices
   ```

3. **Test microphone:**
   ```bash
   # Windows
   voicetranslate-pro --test-microphone
   
   # Or use system tools
   # macOS: QuickTime Player → File → New Audio Recording
   # Linux: arecord -d 5 test.wav && aplay test.wav
   ```

4. **Set default device:**
   ```bash
   voicetranslate-pro --set-input-device "Microphone Name"
   ```

5. **Restart audio service:**
   ```bash
   # Windows
   net stop audiosrv && net start audiosrv
   
   # Linux
   pulseaudio -k && pulseaudio --start
   ```

### Issue: Audio too quiet or too loud

**Symptoms:**
- Poor speech recognition accuracy
- Audio clipping or distortion

**Solutions:**

1. **Adjust microphone level:**
   - **Windows**: Sound Settings → Input → Device Properties → Volume
   - **macOS**: System Preferences → Sound → Input
   - **Linux**: pavucontrol or alsamixer

2. **Enable auto-gain control:**
   ```yaml
   # config.yaml
   audio:
     auto_gain_control: true
     target_level: -16  # dB
   ```

3. **Check microphone placement:**
   - Position 6-12 inches from mouth
   - Avoid breathing directly into microphone
   - Use pop filter if available

### Issue: Background noise interference

**Symptoms:**
- False transcriptions
- Poor recognition accuracy

**Solutions:**

1. **Enable noise cancellation:**
   ```yaml
   # config.yaml
   audio:
     noise_reduction: true
     noise_reduction_level: aggressive  # light, medium, aggressive
   ```

2. **Use directional microphone:**
   - Cardioid pattern microphones reject off-axis sound
   - Headset microphones are closer to mouth

3. **Improve environment:**
   - Close windows and doors
   - Turn off fans and air conditioning
   - Use acoustic treatment if possible

### Issue: Audio delay or latency

**Symptoms:**
- Noticeable delay between speech and translation
- Out-of-sync audio output

**Solutions:**

1. **Reduce buffer size:**
   ```yaml
   # config.yaml
   audio:
     buffer_size: 512  # Lower = less latency, higher CPU usage
   ```

2. **Use low-latency mode:**
   ```bash
   voicetranslate-pro --low-latency
   ```

3. **Check audio driver:**
   - Update to latest audio drivers
   - Use ASIO drivers on Windows for professional audio interfaces

4. **Disable unnecessary processing:**
   ```yaml
   # config.yaml
   audio:
     noise_reduction: false  # Disable if not needed
     normalization: false
   ```

---

## Translation Issues

### Issue: Translations are inaccurate

**Symptoms:**
- Incorrect or nonsensical translations
- Missing context in translations

**Solutions:**

1. **Speak clearly and at moderate pace:**
   - Avoid speaking too fast
   - Pause between sentences
   - Articulate words clearly

2. **Check language selection:**
   - Verify source language is correct
   - Use auto-detect if unsure

3. **Provide context:**
   ```python
   # When using API
   translator.translate(
       text="bank",
       source_lang="en",
       target_lang="zh",
       context="financial institution"  # or "river bank"
   )
   ```

4. **Switch translation engine:**
   ```yaml
   # config.yaml
   translation:
     primary_engine: deepl  # or google, azure
     fallback_engine: google
   ```

5. **Update language models:**
   ```bash
   voicetranslate-pro --update-models
   ```

### Issue: Language not supported

**Symptoms:**
- "Unsupported language" error
- Language not in dropdown list

**Solutions:**

1. **Check supported languages:**
   ```bash
   voicetranslate-pro --list-languages
   ```

2. **Use alternative language code:**
   - Try different variants (e.g., `zh-CN` vs `zh-TW`)
   - Check ISO 639-1 language codes

3. **Request language support:**
   - Open an issue on GitHub
   - Contact support@voicetranslate.pro

### Issue: Special characters not displayed correctly

**Symptoms:**
- Garbled text in translation output
- Missing characters

**Solutions:**

1. **Check font support:**
   - Install fonts for target language
   - Use Unicode-compatible fonts

2. **Set correct encoding:**
   ```python
   # When saving translations
   with open('translation.txt', 'w', encoding='utf-8') as f:
       f.write(translation)
   ```

3. **Update system locale:**
   ```bash
   # Linux
   export LANG=en_US.UTF-8
   export LC_ALL=en_US.UTF-8
   ```

---

## Performance Issues

### Issue: High CPU usage

**Symptoms:**
- System becomes slow
- Fan noise increases
- Battery drains quickly

**Solutions:**

1. **Use smaller models:**
   ```yaml
   # config.yaml
   asr:
     model: whisper-base  # instead of whisper-large
   ```

2. **Enable CPU throttling:**
   ```yaml
   # config.yaml
   performance:
     max_cpu_percent: 50
     priority: low
   ```

3. **Close other applications:**
   - Free up RAM and CPU resources
   - Disable unnecessary background processes

4. **Use GPU acceleration:**
   ```yaml
   # config.yaml
   gpu:
     enabled: true
     device: cuda:0
   ```

### Issue: High memory usage

**Symptoms:**
- Out of memory errors
- System swapping to disk

**Solutions:**

1. **Limit model cache:**
   ```yaml
   # config.yaml
   cache:
     max_size: 2GB
     ttl: 3600  # seconds
   ```

2. **Unload unused models:**
   ```python
   # Manually unload models
   translator.unload_model()
   ```

3. **Use streaming mode:**
   ```yaml
   # config.yaml
   translation:
     mode: streaming  # instead of batch
   ```

4. **Increase swap space (temporary fix):**
   ```bash
   # Linux
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### Issue: Slow translation speed

**Symptoms:**
- Long delays between speech and translation
- Choppy audio output

**Solutions:**

1. **Check internet connection:**
   ```bash
   speedtest-cli
   ```

2. **Use local models:**
   ```yaml
   # config.yaml
   offline:
     enabled: true
     models_path: ~/.voicetranslate-pro/models
   ```

3. **Reduce quality for speed:**
   ```yaml
   # config.yaml
   translation:
     quality: fast  # fast, balanced, quality
   ```

4. **Enable caching:**
   ```yaml
   # config.yaml
   cache:
     enabled: true
     type: redis  # or memory, disk
   ```

---

## Network Issues

### Issue: "Connection timeout" errors

**Symptoms:**
- Translation fails with timeout error
- Intermittent connectivity issues

**Solutions:**

1. **Check internet connection:**
   ```bash
   ping google.com
   curl -I https://api.voicetranslate.pro/health
   ```

2. **Increase timeout:**
   ```yaml
   # config.yaml
   network:
     timeout: 30  # seconds
     retries: 3
   ```

3. **Check firewall settings:**
   - Allow outbound connections on port 443
   - Whitelist api.voicetranslate.pro

4. **Use proxy if needed:**
   ```yaml
   # config.yaml
   network:
     proxy:
       enabled: true
       host: proxy.company.com
       port: 8080
   ```

### Issue: API rate limit exceeded

**Symptoms:**
- HTTP 429 error
- "Rate limit exceeded" message

**Solutions:**

1. **Check current usage:**
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://api.voicetranslate.pro/v1/usage
   ```

2. **Implement rate limiting:**
   ```python
   import time
   from ratelimit import limits, sleep_and_retry
   
   @sleep_and_retry
   @limits(calls=60, period=60)
   def translate_text(text):
       return api.translate(text)
   ```

3. **Upgrade plan:**
   - Visit [dashboard](https://dashboard.voicetranslate.pro) to upgrade

4. **Use caching:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def translate_text(text, source, target):
       return api.translate(text, source, target)
   ```

### Issue: SSL certificate errors

**Symptoms:**
- SSL verification failed
- Certificate validation errors

**Solutions:**

1. **Update certificates:**
   ```bash
   # macOS
   brew install ca-certificates
   
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # Windows
   # Update through Windows Update
   ```

2. **Verify system time:**
   ```bash
   # Incorrect system time can cause SSL errors
   date
   # Sync time if needed
   sudo ntpdate pool.ntp.org
   ```

3. **Temporarily disable verification (not recommended for production):**
   ```python
   import urllib3
   urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
   ```

---

## GUI Issues

### Issue: Application won't start

**Symptoms:**
- Nothing happens when clicking icon
- Error dialog appears

**Solutions:**

1. **Run from terminal to see errors:**
   ```bash
   voicetranslate-pro --verbose
   ```

2. **Check display settings:**
   ```bash
   # Check display resolution
   xdpyinfo | head -20  # Linux
   ```

3. **Reset configuration:**
   ```bash
   # Backup and reset config
   mv ~/.voicetranslate-pro/config.yaml ~/.voicetranslate-pro/config.yaml.backup
   voicetranslate-pro --reset-config
   ```

4. **Reinstall application:**
   ```bash
   pip uninstall voicetranslate-pro
   pip install voicetranslate-pro
   ```

### Issue: GUI elements not displaying correctly

**Symptoms:**
- Missing buttons or text
- Overlapping elements
- Incorrect colors

**Solutions:**

1. **Update graphics drivers:**
   - Download latest drivers from manufacturer

2. **Change theme:**
   ```bash
   voicetranslate-pro --theme light  # or dark
   ```

3. **Adjust DPI settings:**
   ```yaml
   # config.yaml
   gui:
     high_dpi_scaling: true
     font_scale: 1.0
   ```

4. **Clear GUI cache:**
   ```bash
   rm -rf ~/.voicetranslate-pro/cache/gui/
   ```

### Issue: Application crashes

**Symptoms:**
- Unexpected shutdown
- Error reports

**Solutions:**

1. **Check logs:**
   ```bash
   # View application logs
   cat ~/.voicetranslate-pro/logs/app.log
   
   # View error logs
   cat ~/.voicetranslate-pro/logs/error.log
   ```

2. **Update to latest version:**
   ```bash
   pip install --upgrade voicetranslate-pro
   ```

3. **Report crash:**
   ```bash
   voicetranslate-pro --report-crash
   ```

---

## API Issues

### Issue: "401 Unauthorized" error

**Symptoms:**
- API requests fail with 401 status
- "Invalid API key" message

**Solutions:**

1. **Verify API key:**
   ```bash
   echo $VOICETRANSLATE_API_KEY
   # or
   cat ~/.voicetranslate-pro/config.yaml | grep api_key
   ```

2. **Check key format:**
   - Should start with `sk_live_` or `sk_test_`
   - No extra spaces or quotes

3. **Regenerate key:**
   - Visit [dashboard](https://dashboard.voicetranslate.pro)
   - Generate new API key

### Issue: "422 Unprocessable Entity" error

**Symptoms:**
- Request format errors
- Validation failures

**Solutions:**

1. **Check request format:**
   ```python
   import json
   
   # Verify JSON is valid
   data = {
       "text": "Hello",
       "source_lang": "en",
       "target_lang": "zh"
   }
   print(json.dumps(data, indent=2))
   ```

2. **Validate parameters:**
   - Required fields must be present
   - Language codes must be valid
   - Text must not exceed limits

---

## Error Codes

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| E001 | Invalid API key | Check and regenerate API key |
| E002 | Rate limit exceeded | Wait or upgrade plan |
| E003 | Unsupported language | Check supported languages |
| E004 | Audio format error | Convert to supported format |
| E005 | Network timeout | Check connection, increase timeout |
| E006 | Model load failed | Restart application, check disk space |
| E007 | Out of memory | Close applications, reduce model size |
| E008 | GPU error | Check CUDA installation, use CPU |
| E009 | Permission denied | Check file permissions |
| E010 | Config error | Reset configuration |

### Viewing Error Details

```bash
# Get detailed error information
voicetranslate-pro --error-details E001

# View all errors
voicetranslate-pro --list-errors
```

---

## Getting Help

### Self-Help Resources

1. **Documentation**: [docs.voicetranslate.pro](https://docs.voicetranslate.pro)
2. **FAQ**: [docs.voicetranslate.pro/faq](https://docs.voicetranslate.pro/faq)
3. **GitHub Issues**: [github.com/voicetranslate-pro/issues](https://github.com/voicetranslate-pro/issues)
4. **Community Forum**: [community.voicetranslate.pro](https://community.voicetranslate.pro)

### Contact Support

**Email**: support@voicetranslate.pro  
**Response Time**: Within 24 hours (business days)

### Reporting Issues

When reporting issues, include:

1. **System information:**
   ```bash
   voicetranslate-pro --system-info
   ```

2. **Error logs:**
   ```bash
   cat ~/.voicetranslate-pro/logs/error.log
   ```

3. **Steps to reproduce**
4. **Expected vs actual behavior**
5. **Screenshots (if applicable)**

### Issue Template

```markdown
**Description**
Brief description of the issue

**Environment**
- OS: Windows 11 / macOS 14 / Ubuntu 22.04
- Version: 2.1.0
- Python: 3.9.7

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Logs**
```
Paste relevant log output here
```

**Screenshots**
If applicable
```

---

## Quick Reference Card

### Common Commands

```bash
# Diagnostics
voicetranslate-pro --diagnose

# List audio devices
voicetranslate-pro --list-audio-devices

# Test microphone
voicetranslate-pro --test-microphone

# Reset configuration
voicetranslate-pro --reset-config

# Update models
voicetranslate-pro --update-models

# View logs
voicetranslate-pro --logs

# System info
voicetranslate-pro --system-info
```

### Configuration File Location

| OS | Path |
|----|------|
| Windows | `%APPDATA%\VoiceTranslate Pro\config.yaml` |
| macOS | `~/.voicetranslate-pro/config.yaml` |
| Linux | `~/.config/voicetranslate-pro/config.yaml` |

### Log File Location

| OS | Path |
|----|------|
| Windows | `%APPDATA%\VoiceTranslate Pro\logs\` |
| macOS | `~/.voicetranslate-pro/logs/` |
| Linux | `~/.local/share/voicetranslate-pro/logs/` |
