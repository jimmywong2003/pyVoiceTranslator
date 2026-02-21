#!/bin/bash
# Run VoiceTranslate with Microphone Selection

cd "$(dirname "$0")"
source venv/bin/activate

echo "🎤 VoiceTranslate Pro - Microphone Mode"
echo "========================================"
echo ""

# Show available devices
echo "Available Microphones:"
python -c "
import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        print(f'  [{i}] {d[\"name\"]}')
"

echo ""
read -p "Select microphone device number: " DEVICE

echo ""
echo "Starting with device $DEVICE..."
python cli/demo_realtime_translation.py --device $DEVICE --source en --target zh
