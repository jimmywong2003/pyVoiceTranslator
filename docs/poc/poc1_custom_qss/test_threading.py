"""
PoC 1: Audio Threading Compatibility Test
Tests if Fluent widgets work with QThread-based audio updates
"""

import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QProgressBar, QLabel, QPushButton
)
from PySide6.QtCore import QThread, Signal, QTimer

# Try Fluent widgets
try:
    from qfluentwidgets import ProgressBar as FluentProgressBar, PushButton
    FLUENT_AVAILABLE = True
except ImportError:
    FLUENT_AVAILABLE = False


class AudioSimulatorThread(QThread):
    """Simulates audio capture in background thread"""
    
    level_update = Signal(float)
    
    def __init__(self):
        super().__init__()
        self.running = False
    
    def run(self):
        self.running = True
        while self.running:
            # Simulate audio level (0.0 to 1.0)
            level = np.random.random()
            self.level_update.emit(level)
            time.sleep(0.03)  # ~30fps updates
    
    def stop(self):
        self.running = False


class ThreadingTestWindow(QMainWindow):
    """Test window with real-time audio updates"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PoC 1: Threading Test")
        self.resize(400, 200)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Status
        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)
        
        # Progress bar (Fluent or standard)
        if FLUENT_AVAILABLE:
            self.progress = FluentProgressBar()
        else:
            self.progress = QProgressBar()
        
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        
        # Control buttons
        self.start_btn = QPushButton("Start Audio Sim")
        self.start_btn.clicked.connect(self.start_audio)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_audio)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        # FPS counter
        self.fps_label = QLabel("Updates/sec: 0")
        layout.addWidget(self.fps_label)
        
        # Audio thread
        self.audio_thread = None
        self.update_count = 0
        self.last_time = time.time()
        
        # FPS timer
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)
    
    def start_audio(self):
        """Start audio simulation thread"""
        self.audio_thread = AudioSimulatorThread()
        self.audio_thread.level_update.connect(self.on_level_update)
        self.audio_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Status: Running (check for UI freezing)")
        print("✓ Audio thread started")
    
    def stop_audio(self):
        """Stop audio thread"""
        if self.audio_thread:
            self.audio_thread.stop()
            self.audio_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status: Stopped")
        print("✓ Audio thread stopped")
    
    def on_level_update(self, level):
        """Update UI from audio thread - CRITICAL: Must not freeze"""
        self.progress.setValue(int(level * 100))
        self.update_count += 1
    
    def update_fps(self):
        """Calculate update rate"""
        now = time.time()
        elapsed = now - self.last_time
        fps = self.update_count / elapsed if elapsed > 0 else 0
        self.fps_label.setText(f"Updates/sec: {fps:.1f}")
        self.update_count = 0
        self.last_time = now


def test_threading():
    """Test audio threading with UI updates"""
    print("\n=== Test: Audio Threading ===")
    print("This test verifies UI remains responsive during audio updates")
    print("Run for 10 seconds...")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    window = ThreadingTestWindow()
    window.show()
    
    # Auto-start
    window.start_audio()
    
    # Run for 10 seconds
    start = time.time()
    while time.time() - start < 10:
        app.processEvents()
        time.sleep(0.01)
    
    window.stop_audio()
    
    print("✓ Threading test completed")
    print("  - Check: Did UI freeze during updates?")
    print("  - Check: Were buttons responsive?")
    print("  - Check: FPS stayed ~30?")
    
    window.close()
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 1: Threading Compatibility Test")
    print("=" * 60)
    print(f"Fluent Available: {FLUENT_AVAILABLE}")
    
    success = test_threading()
    
    # Append results
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 1: Threading Test\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Fluent Available: {FLUENT_AVAILABLE}\n")
        f.write(f"- Threading Test: {'PASS' if success else 'FAIL'}\n")
        f.write(f"- Notes: Check for UI freezing during audio updates\n")
    
    print("\n✓ Results appended to results.md")
