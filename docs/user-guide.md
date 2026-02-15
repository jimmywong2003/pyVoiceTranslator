# User Guide

## VoiceTranslate Pro - Complete User Guide

This comprehensive guide covers all features and functionality of VoiceTranslate Pro.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Main Interface](#main-interface)
3. [Translation Modes](#translation-modes)
4. [Language Settings](#language-settings)
5. [Audio Configuration](#audio-configuration)
6. [Video Call Integration](#video-call-integration)
7. [Advanced Features](#advanced-features)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Settings Reference](#settings-reference)
10. [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### First Launch

When you launch VoiceTranslate Pro for the first time:

1. **Welcome Screen**: Introduction to key features
2. **Initial Setup**: Configure basic settings
3. **Audio Test**: Verify microphone is working
4. **Language Selection**: Set default languages
5. **Tutorial**: Interactive walkthrough (optional)

### Quick Start Guide

```
1. Select source language (language you speak)
2. Select target language (language to translate to)
3. Click "Start" or press Space
4. Speak clearly into your microphone
5. View translation in real-time
6. Click "Stop" or press Space to stop
```

---

## Main Interface

### Interface Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  VoiceTranslate Pro                              [_] [□] [X]    │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Source: [▼]  │  │ Target: [▼]  │  │ [⚙ Settings]         │  │
│  │ English ▼    │  │ Chinese ▼    │  │ [📹 Video Mode]      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🎤 Transcription                                       │   │
│  │  "Hello, how are you today?"                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🌐 Translation                                         │   │
│  │  "你好，你今天怎么样？"                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ▓▓▓▓▓▓▓░░░░░░░░░░░░ Audio Visualizer                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [⏹ Stop]  [🔄 Swap Languages]  [💾 Save]  [📋 Copy]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Status: Ready | Confidence: 98% | Latency: 245ms              │
└─────────────────────────────────────────────────────────────────┘
```

### Interface Components

#### 1. Language Selectors

- **Source Language**: Language you speak
- **Target Language**: Language to translate to
- **Swap Button**: Quickly swap languages
- **Auto-detect**: Automatically detect source language

#### 2. Transcription Area

- Shows recognized speech in source language
- Confidence indicator for each segment
- Click to edit if recognition is incorrect

#### 3. Translation Area

- Shows translated text
- Alternative translations (click to expand)
- Pronunciation guide (optional)

#### 4. Audio Visualizer

- Real-time audio level display
- Visual feedback for speech detection
- Noise level indicator

#### 5. Control Buttons

- **Start/Stop**: Begin or end translation
- **Save**: Save conversation to file
- **Copy**: Copy translation to clipboard
- **Settings**: Open settings panel

---

## Translation Modes

### 1. Standard Mode

**Use Case**: One-way translation

**How it works**:
1. You speak in source language
2. System translates to target language
3. Translation displayed and spoken aloud

**Settings**:
- Source language: Your language
- Target language: Listener's language
- Audio output: Enabled

### 2. Conversation Mode

**Use Case**: Two-way conversation between two people

**How it works**:
1. Person A speaks in Language 1
2. System translates to Language 2
3. Person B hears translation
4. Person B responds in Language 2
5. System translates to Language 1
6. Person A hears translation

**Setup**:
```
Person A Language: English
Person B Language: Japanese
Auto-detect speaker: Enabled
```

**Interface**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Conversation Mode                                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ Person A: English   │  │ Person B: Japanese  │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ "Hello!"           │  │ "こんにちは！"       │              │
│  │                    │  │                    │              │
│  │ "こんにちは！"      │◀─│ "Hello!"           │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
│  [Speaker: Person A ▓▓▓▓░░░░]                                  │
│                                                                 │
│  [⏹ End Conversation]                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Video Call Mode

**Use Case**: Translation during video conferences

**Supported Platforms**:
- Zoom
- Microsoft Teams
- Google Meet
- WebEx
- Skype
- Custom WebRTC

**Setup**:
1. Select "Video Call Mode"
2. Choose video source (camera or screen)
3. Select translation direction:
   - **Incoming**: Translate what others say
   - **Outgoing**: Translate what you say
   - **Bidirectional**: Translate both ways
4. Enable overlay to see translations on screen

**Configuration**:
```yaml
video_call:
  platform: zoom
  translation_direction: bidirectional
  overlay:
    enabled: true
    position: bottom
    opacity: 0.8
  subtitle_style:
    font_size: 24
    color: white
    background: black
```

### 4. Batch Translation Mode

**Use Case**: Translate recorded audio files

**Supported Formats**:
- MP3
- WAV
- M4A
- OGG
- FLAC
- MP4 (video with audio)

**How to use**:
1. Go to File → Batch Translate
2. Select audio/video files
3. Choose output format:
   - Transcript only (TXT, SRT)
   - Translated audio (MP3, WAV)
   - Both
4. Click "Process"
5. Download results

**Output Options**:
```
✓ Transcript (source language)
✓ Translation (target language)
✓ Subtitle file (SRT format)
✓ Dubbed audio
✓ Side-by-side comparison
```

### 5. Offline Mode

**Use Case**: Translation without internet connection

**Requirements**:
- Download language models in advance
- Sufficient storage space (2-5 GB per language)

**Setup**:
1. Go to Settings → Offline Mode
2. Download required language packs
3. Enable offline mode

**Limitations**:
- Fewer languages supported
- Lower accuracy than cloud models
- No real-time updates

---

## Language Settings

### Supported Languages

**Tier 1 (Full Support)**:
- English (en)
- Chinese - Simplified (zh-CN)
- Chinese - Traditional (zh-TW)
- Japanese (ja)
- French (fr)
- German (de)
- Spanish (es)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Korean (ko)
- Arabic (ar)
- Hindi (hi)

**Tier 2 (Good Support)**:
- Dutch, Polish, Turkish, Vietnamese, Thai, Indonesian, Malay

**Tier 3 (Basic Support)**:
- 30+ additional languages

### Language Detection

**Auto-detect**:
- Automatically identifies spoken language
- Supports 50+ languages
- Confidence threshold: 80%

**Manual Selection**:
- More accurate for known languages
- Faster processing
- Better for mixed-language content

### Regional Variants

| Language | Variants |
|----------|----------|
| English | US, UK, Australian, Indian |
| Chinese | Simplified, Traditional |
| Spanish | Spain, Mexico, Argentina |
| French | France, Canada, Belgium |
| Portuguese | Portugal, Brazil |
| Arabic | Modern Standard, Egyptian, Gulf |

---

## Audio Configuration

### Input Device Settings

**Selecting Microphone**:
1. Settings → Audio → Input Device
2. Choose from detected devices
3. Test with "Test Microphone" button

**Recommended Microphones**:
| Use Case | Recommendation | Price Range |
|----------|---------------|-------------|
| Casual | Built-in or basic USB | $0-30 |
| Professional | Blue Yeti, Audio-Technica AT2020 | $100-150 |
| Mobile | Lavalier mic with TRRS connector | $20-50 |
| Conference | Jabra Speak, Polycom | $200-500 |

### Audio Quality Settings

```yaml
audio:
  sample_rate: 16000  # Options: 8000, 16000, 22050, 44100
  bit_depth: 16       # Options: 16, 24, 32
  channels: 1         # Options: 1 (mono), 2 (stereo)
  
  # Processing
  noise_reduction: true
  noise_reduction_level: medium  # light, medium, aggressive
  auto_gain_control: true
  echo_cancellation: true
  
  # Buffer
  buffer_size: 1024   # Lower = less latency, higher CPU
```

### Output Device Settings

**Text-to-Speech Output**:
- Select output device (speakers/headphones)
- Adjust volume independently
- Test with "Test TTS" button

**Voice Selection**:
- Choose from available voices
- Preview voice samples
- Adjust speed and pitch

---

## Video Call Integration

### Zoom Integration

**Setup**:
1. Open Zoom settings
2. Go to Video → Camera
3. Select "VoiceTranslate Pro Virtual Camera"
4. In VoiceTranslate Pro, enable "Zoom Mode"

**Features**:
- Real-time subtitles
- Translated audio output
- Recording with translation

### Microsoft Teams Integration

**Setup**:
1. In Teams, click "..." during call
2. Select "Show device settings"
3. Choose VoiceTranslate Pro as microphone/camera

### Google Meet Integration

**Setup**:
1. Click settings (gear icon) in Meet
2. Audio → Microphone → VoiceTranslate Pro
3. Video → Camera → VoiceTranslate Pro Virtual Camera

### Custom Integration

**WebRTC Support**:
```javascript
// Example: Integrate with custom WebRTC application
const stream = await navigator.mediaDevices.getUserMedia({
  audio: {
    deviceId: 'voicetranslate-pro-virtual-mic'
  },
  video: {
    deviceId: 'voicetranslate-pro-virtual-camera'
  }
});
```

---

## Advanced Features

### 1. Custom Vocabulary

Add domain-specific terms for better recognition:

```yaml
custom_vocabulary:
  - term: "Kubernetes"
    pronunciation: "koo-ber-net-ees"
    language: "en"
  - term: "机器学习"
    pronunciation: "ji-qi-xue-xi"
    language: "zh"
```

### 2. Conversation History

**Features**:
- Automatic saving of all translations
- Search and filter
- Export to various formats
- Cloud sync (optional)

**Access**:
- Menu → History
- Keyboard shortcut: Ctrl+H

### 3. Pronunciation Guide

**Features**:
- Phonetic transcription
- Audio playback at slower speed
- Practice mode

**Usage**:
1. Right-click on translated text
2. Select "Pronunciation Guide"
3. Listen and practice

### 4. Batch Export

**Export Formats**:
- TXT (plain text)
- DOCX (Microsoft Word)
- PDF
- SRT (subtitles)
- JSON (structured data)
- CSV (spreadsheet)

### 5. API Integration

**For Developers**:
```python
from voicetranslate_pro import VoiceTranslator

translator = VoiceTranslator(api_key="your-key")

# Real-time translation
for translation in translator.stream(
    source_lang="en",
    target_lang="zh"
):
    print(translation.text)
```

---

## Keyboard Shortcuts

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Start/Stop translation |
| `Ctrl + T` | Toggle translation on/off |
| `Ctrl + R` | Record conversation |
| `Ctrl + S` | Save translation |
| `Ctrl + C` | Copy translation |
| `Ctrl + ,` | Open settings |
| `Ctrl + H` | Open history |
| `Ctrl + Q` | Quit application |
| `Esc` | Stop current operation |
| `F1` | Open help |

### Navigation Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Next field |
| `Shift + Tab` | Previous field |
| `Ctrl + 1` | Focus source language |
| `Ctrl + 2` | Focus target language |
| `Ctrl + L` | Swap languages |

### Mode Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + M` | Toggle mode (Standard/Conversation/Video) |
| `Ctrl + B` | Batch translation |
| `Ctrl + O` | Offline mode |

### Custom Shortcuts

Configure custom shortcuts in Settings → Shortcuts:

```yaml
shortcuts:
  start_translation: "Space"
  stop_translation: "Esc"
  swap_languages: "Ctrl+L"
  save_translation: "Ctrl+S"
  # Add custom shortcuts
  custom_action: "Ctrl+Shift+X"
```

---

## Settings Reference

### General Settings

```yaml
general:
  language: "en"           # Interface language
  theme: "dark"            # dark, light, auto
  startup:
    auto_start: false
    minimize_to_tray: true
  updates:
    check_on_startup: true
    auto_install: false
```

### Translation Settings

```yaml
translation:
  default_source: "en"
  default_target: "zh"
  auto_detect: true
  
  engines:
    primary: "deepl"
    fallback: "google"
    
  quality: "balanced"      # fast, balanced, quality
  formality: "default"     # formal, informal, default
  
  output:
    show_alternatives: true
    show_confidence: true
    auto_pronunciation: false
```

### Audio Settings

```yaml
audio:
  input:
    device: "default"
    sample_rate: 16000
    
  output:
    device: "default"
    volume: 80
    
  processing:
    noise_reduction: true
    noise_reduction_level: "medium"
    auto_gain_control: true
    echo_cancellation: true
    
  tts:
    voice: "auto"
    speed: 1.0
    pitch: 0
```

### Privacy Settings

```yaml
privacy:
  local_mode: false        # Process everything locally
  save_history: true
  cloud_sync: false
  analytics: false
  
  data_retention:
    history_days: 30
    auto_delete: true
```

### Advanced Settings

```yaml
advanced:
  asr:
    model: "whisper-base"
    language_detection: true
    
  performance:
    gpu_acceleration: true
    max_cpu_percent: 80
    
  network:
    timeout: 30
    retries: 3
    proxy:
      enabled: false
```

---

## Tips and Best Practices

### For Best Recognition Accuracy

1. **Use a good microphone**
   - External microphone preferred
   - Position 6-12 inches from mouth
   - Avoid built-in laptop mics in noisy environments

2. **Speak clearly**
   - Moderate pace (120-150 words per minute)
   - Articulate words
   - Pause between sentences

3. **Minimize background noise**
   - Close windows and doors
   - Turn off fans and AC
   - Use noise-canceling microphone

4. **Optimize environment**
   - Quiet room
   - Good internet connection
   - Close unnecessary applications

### For Best Translation Quality

1. **Choose appropriate mode**
   - Standard: One-way communication
   - Conversation: Two-way dialogue
   - Video: Conference calls

2. **Select correct languages**
   - Use auto-detect for mixed content
   - Manual selection for known languages
   - Consider regional variants

3. **Provide context**
   - Use custom vocabulary for technical terms
   - Select appropriate formality level
   - Enable domain-specific models

### Performance Optimization

1. **Enable GPU acceleration** (if available)
2. **Use appropriate model size**
   - Base model: Fast, good accuracy
   - Large model: Slower, best accuracy
3. **Enable caching** for repeated phrases
4. **Close unused applications**

### Battery Saving (Laptops)

1. **Use smaller ASR models**
2. **Disable GPU acceleration**
3. **Reduce audio quality**
4. **Enable power saving mode**

---

## Troubleshooting Common Issues

See [Troubleshooting Guide](troubleshooting.md) for detailed solutions.

### Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| No audio input | Check microphone permissions |
| Poor recognition | Speak slower, reduce noise |
| Slow translation | Check internet connection |
| App crashes | Update to latest version |
| High CPU usage | Use smaller model |

---

## Support and Resources

- **Documentation**: [docs.voicetranslate.pro](https://docs.voicetranslate.pro)
- **Video Tutorials**: [YouTube Channel](https://youtube.com/voicetranslate)
- **Community Forum**: [community.voicetranslate.pro](https://community.voicetranslate.pro)
- **Email Support**: support@voicetranslate.pro

---

Thank you for using VoiceTranslate Pro! 🎙️🌐
