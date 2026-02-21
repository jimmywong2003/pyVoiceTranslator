#!/bin/bash
# Documentary Mode Launcher
# Optimized for news/documentary content with long sentences

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

echo "🎬 VoiceTranslate Pro - Documentary Mode"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  • Max Segment: 15s (for long sentences)"
echo "  • Hallucination Filter: Lenient (18% diversity)"
echo "  • Silence Threshold: 800ms"
echo "  • ASR Model: base (int8)"
echo ""
echo "Starting GUI..."
echo ""

# Run GUI with documentary settings
# The pipeline will auto-detect config/documentary_mode.json
python src/gui/main.py "$@"
