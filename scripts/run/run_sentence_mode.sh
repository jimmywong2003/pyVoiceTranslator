#!/bin/bash
# Sentence Mode Launcher
# Optimized for sentence-by-sentence detection with clear boundaries

cd "$(dirname "$0")"
source venv/bin/activate

echo "📖 VoiceTranslate Pro - Sentence Mode"
echo "======================================"
echo ""
echo "Configuration:"
echo "  • Max Segment: 20s (for long sentences)"
echo "  • Silence Threshold: 600ms (waits for real pauses)"
echo "  • Min Speech: 500ms (filters short fragments)"
echo "  • Hallucination Filter: CJK-aware (10% diversity)"
echo ""
echo "Best for:"
echo "  • Dialogue with clear sentence boundaries"
echo "  • Narration and storytelling"
echo "  • Documentary content"
echo "  • News broadcasts"
echo ""
echo "Tips:"
echo "  • Speak in complete sentences"
echo "  • Pause between sentences (600ms+)"
echo "  • Avoid continuous run-on speech"
echo ""

# Show available devices
python -c "
import sounddevice as sd
print('🎤 Available Microphones:')
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        print(f'  [{i}] {d[\"name\"]}')
print()
"

# Copy sentence mode config
mkdir -p config
cp config/sentence_mode.json config/active_config.json

echo "Starting GUI with Sentence Mode..."
echo ""

# Run GUI
python src/gui/main.py "$@"
