"""
Meeting Mode Demo
=================

Quick demo script to showcase Meeting Mode functionality.
"""

import sys
import random
from pathlib import Path

# Add project root to path (handle running from any directory)
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.gui.meeting.window import MeetingWindow


def demo():
    """Run Meeting Mode demo with simulated entries"""
    app = QApplication(sys.argv)
    
    # Create window
    window = MeetingWindow()
    window.setWindowTitle("Meeting Mode Demo - VoiceTranslate Pro")
    
    # Demo conversation data
    demo_conversation = [
        ("Alice", "Good morning everyone. Let's start with the project status."),
        ("Bob", "The backend development is on track. We're 80% complete."),
        ("Carol", "I've reviewed the designs. They look great!"),
        ("David", "We need to discuss the timeline for the next release."),
        ("Alice", "What's the current blocker?"),
        ("Bob", "The API integration is taking longer than expected."),
        ("Carol", "I can help with that. I have experience with their API."),
        ("David", "That would be great. Let's pair on it tomorrow."),
        ("Alice", "Any other concerns?"),
        ("Bob", "The testing coverage is at 65%. We should improve that."),
        ("Carol", "I can write more tests once the API is integrated."),
        ("David", "Let's aim for 80% coverage by next week."),
        ("Alice", "Sounds good. Let's wrap up here."),
        ("Bob", "Thanks everyone. Have a great day!"),
    ]
    
    entry_index = [0]  # Use list for mutable reference in closure
    
    def add_next_entry():
        """Add next entry from demo conversation"""
        if not window.is_recording():
            return
        
        if entry_index[0] < len(demo_conversation):
            speaker, text = demo_conversation[entry_index[0]]
            
            # Add entry with simulated translation for some entries
            translated = None
            if entry_index[0] % 3 == 0:
                translated = f"[JA] {text[:20]}..."
            
            window.add_transcription(
                text=text,
                translated_text=translated,
                confidence=random.uniform(0.80, 0.95),
                duration=random.uniform(2.0, 4.0),
            )
            
            entry_index[0] += 1
        else:
            # Auto-stop after all entries
            window.toolbar.stop_btn.click()
    
    # Setup timer for simulated entries
    timer = QTimer()
    timer.timeout.connect(add_next_entry)
    
    def on_start():
        timer.start(2000)  # Add entry every 2 seconds
    
    def on_stop():
        timer.stop()
    
    window.meeting_started.connect(on_start)
    window.meeting_ended.connect(on_stop)
    
    # Show window
    window.show()
    
    print("=" * 60)
    print("Meeting Mode Demo")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Click 'Start' to begin the simulated meeting")
    print("2. Watch entries appear automatically every 2 seconds")
    print("3. Observe speaker rotation and timestamps")
    print("4. Click 'Export' to save the transcript")
    print("5. Click 'Stop' to end (auto-stops after all entries)")
    print("\n" + "=" * 60)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    demo()
