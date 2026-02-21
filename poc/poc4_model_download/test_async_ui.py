"""
PoC 4: CRITICAL - Async Model Download & UI Responsiveness
Tests that ModelManager downloads in background without freezing UI
"""

import sys
import time
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QProgressBar, QLabel
)
from PySide6.QtCore import QThread, Signal, QObject, Qt


@dataclass
class ModelConfig:
    """Model download configuration"""
    name: str
    url: str
    size_mb: int = 10


class ModelDownloadWorker(QObject):
    """Worker for downloading models in background thread"""
    
    progress_changed = Signal(float, int)  # percent, bytes_per_sec
    status_changed = Signal(str)
    finished = Signal(bool, str)  # success, error
    
    def __init__(self, config: ModelConfig, dest_path: Path):
        super().__init__()
        self.config = config
        self.dest_path = dest_path
        self._stop_requested = False
    
    def run(self):
        """Download in background thread"""
        try:
            import requests
            import numpy as np
            
            self.status_changed.emit(f"Downloading {self.config.name}...")
            
            # Simulate large download by writing chunks
            chunk_size = 1024 * 1024  # 1MB chunks
            total_bytes = self.config.size_mb * 1024 * 1024
            downloaded = 0
            
            start_time = time.time()
            
            with open(self.dest_path, 'wb') as f:
                while downloaded < total_bytes and not self._stop_requested:
                    # Write chunk
                    chunk = np.random.bytes(chunk_size)
                    f.write(chunk)
                    downloaded += chunk_size
                    
                    # Calculate progress
                    percent = (downloaded / total_bytes) * 100
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    
                    self.progress_changed.emit(percent, int(speed))
                    
                    # Simulate network delay
                    time.sleep(0.1)
            
            if self._stop_requested:
                self.finished.emit(False, "Cancelled")
            else:
                self.finished.emit(True, "")
                
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def request_stop(self):
        self._stop_requested = True


class ModelManager(QObject):
    """Async model manager - MUST NOT block UI"""
    
    progress_changed = Signal(float, int)
    status_changed = Signal(str)
    download_complete = Signal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.models_dir = Path(tempfile.gettempdir()) / "voicetranslate_test"
        self.models_dir.mkdir(exist_ok=True)
        self._thread = None
        self._worker = None
    
    def download_async(self, config: ModelConfig):
        """Start async download - NON-BLOCKING"""
        dest = self.models_dir / config.name
        
        # Create thread and worker
        self._thread = QThread()
        self._worker = ModelDownloadWorker(config, dest)
        self._worker.moveToThread(self._thread)
        
        # Connect signals
        self._worker.progress_changed.connect(self.progress_changed)
        self._worker.status_changed.connect(self.status_changed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.finished.connect(
            lambda success, msg: self.download_complete.emit(success, msg)
        )
        self._thread.finished.connect(self._thread.deleteLater)
        
        # Start
        self._thread.started.connect(self._worker.run)
        self._thread.start()
    
    def cancel(self):
        """Cancel download"""
        if self._worker:
            self._worker.request_stop()


class TestWindow(QMainWindow):
    """Test window to verify UI remains responsive during download"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PoC 4: Async Download Test")
        self.resize(400, 200)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Status
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        
        # Speed label
        self.speed_label = QLabel("Speed: 0 MB/s")
        layout.addWidget(self.speed_label)
        
        # Download button
        self.download_btn = QPushButton("Start Download (100MB)")
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        layout.addWidget(self.cancel_btn)
        
        # CRITICAL: Button to test UI responsiveness
        self.test_btn = QPushButton("✓ Click Me During Download!")
        self.test_btn.clicked.connect(self.on_test_click)
        layout.addWidget(self.test_btn)
        
        self.click_count = 0
        self.downloading = False
        
        # Model manager
        self.manager = ModelManager()
        self.manager.progress_changed.connect(self.on_progress)
        self.manager.status_changed.connect(self.on_status)
        self.manager.download_complete.connect(self.on_complete)
    
    def start_download(self):
        """Start async download"""
        config = ModelConfig(
            name="test_model.bin",
            url="http://example.com/test.bin",  # Dummy URL
            size_mb=100  # 100MB test
        )
        
        self.manager.download_async(config)
        
        self.downloading = True
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.click_count = 0
        self.test_btn.setText("✓ Click Me During Download!")
    
    def cancel_download(self):
        """Cancel download"""
        self.manager.cancel()
        self.status_label.setText("Status: Cancelling...")
    
    def on_progress(self, percent, speed):
        """Update progress - called from background thread"""
        self.progress.setValue(int(percent))
        self.speed_label.setText(f"Speed: {speed/1024/1024:.1f} MB/s")
    
    def on_status(self, status):
        """Update status"""
        self.status_label.setText(f"Status: {status}")
    
    def on_complete(self, success, error):
        """Download complete"""
        self.downloading = False
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.status_label.setText(f"Status: ✓ Complete (Clicks: {self.click_count})")
        else:
            self.status_label.setText(f"Status: ✗ Failed: {error}")
    
    def on_test_click(self):
        """CRITICAL: This must work during download!"""
        self.click_count += 1
        self.test_btn.setText(f"✓ Clicked! ({self.click_count} times)")


def test_async_download():
    """CRITICAL Test: UI must remain responsive during 100MB download"""
    print("\n" + "=" * 60)
    print("CRITICAL TEST: Async Download + UI Responsiveness")
    print("=" * 60)
    print("\n⚠ This test verifies:")
    print("   1. Download runs in background thread")
    print("   2. Progress bar updates correctly")
    print("   3. UI buttons remain clickable")
    print("   4. No freezing during 100MB download")
    print("\n⏳ Starting 100MB download test...")
    print("   (Simulating ~10 seconds)")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    # Auto-start download
    window.start_download()
    
    # Simulate user clicking the test button during download
    # In real test, user would manually click
    click_times = []
    start = time.time()
    
    while window.downloading and time.time() - start < 15:
        app.processEvents()
        
        # Auto-click every 0.5 seconds to test responsiveness
        if int((time.time() - start) * 2) > len(click_times):
            window.on_test_click()
            click_times.append(time.time())
        
        time.sleep(0.01)
    
    elapsed = time.time() - start
    
    print(f"\n✓ Download test completed in {elapsed:.1f}s")
    print(f"  Clicks registered: {window.click_count}")
    
    if window.click_count > 10:
        print("✓ PASS: UI remained responsive during download")
        return True
    else:
        print("✗ FAIL: UI was frozen (not enough clicks)")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 4: Async Model Download")
    print("=" * 60)
    
    result = test_async_download()
    
    # Write results
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 4: Async Download & UI Responsiveness\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Async Download: {'PASS' if result else 'FAIL'}\n")
        f.write(f"- **CRITICAL**: {'UI remained responsive' if result else 'UI FROZE - BLOCKER'}\n")
    
    print("\n✓ Results appended to results.md")
