#!/bin/bash
# Interview Mode Launcher
# Minimal filtering - best for documentary/interview content

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

echo "🎤 VoiceTranslate Pro - Interview Mode"
echo "====================================="
echo ""
echo "Configuration:"
echo "  • Max Segment: 15s"
echo "  • Hallucination Filter: LENIENT (12% diversity)"
echo "  • Filler Words: Kept (not removed)"
echo "  • Confidence Threshold: 0.20 (low)"
echo ""
echo "Best for:"
echo "  • Documentary narration"
echo "  • Interviews"
echo "  • Natural conversation"
echo ""
echo "Starting GUI..."
echo ""

# Copy interview config as default
mkdir -p config
cp config/interview_mode.json config/active_config.json

# Run GUI
python src/gui/main.py "$@"
