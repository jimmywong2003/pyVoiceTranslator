#!/bin/bash
# Japanese to English Translation Launcher
# Optimized settings for Japanese speech recognition

cd "$(dirname "$0")"
source venv/bin/activate

echo "🎌 VoiceTranslate Pro - Japanese → English"
echo "============================================"
echo ""
echo "Configuration:"
echo "  • Source: Japanese (ja)"
echo "  • Target: English (en)"
echo "  • ASR Model: base (recommended for Japanese)"
echo "  • Interview Mode: Enabled (less filtering)"
echo ""
echo "Tips for best results:"
echo "  1. Speak clearly at normal pace"
echo "  2. Keep microphone 10-15cm from mouth"
echo "  3. Reduce background noise"
echo "  4. Use base or small model (not tiny)"
echo ""

# Show available microphones
echo "🎤 Available Microphones:"
python -c "
import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        print(f'  [{i}] {d[\"name\"]}')
"
echo ""

# Use device 4 (MacBook Pro Microphone) or let user specify
DEVICE=${1:-4}
echo "Using device: $DEVICE"
echo ""

# Run with optimized settings for Japanese
python cli/demo_realtime_translation.py \
  --source ja \
  --target en \
  --asr-model base \
  --device $DEVICE
