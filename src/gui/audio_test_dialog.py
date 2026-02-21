"""
Audio Test Dialog
=================

Real-time microphone audio level test with visual meter.
"""

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

import sounddevice as sd


class AudioTestDialog(QDialog):
    """
    Dialog for testing microphone input with visual level meter.
    
    Features:
    - Device selection dropdown
    - Real-time audio level visualization
    - Peak level indicator
    - Start/Stop test controls
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎤 Audio Test")
        self.setMinimumSize(500, 300)
        
        self._stream = None
        self._is_testing = False
        self._peak_level = 0.0
        
        self._setup_ui()
        self._populate_devices()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
            }
            QLabel {
                color: #cccccc;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #094771;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #858585;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
                padding: 5px;
                min-width: 300px;
            }
            QProgressBar {
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #4ec9b0;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🎤 Microphone Audio Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Test your microphone input level before starting translation.")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("Microphone:")
        self.device_combo = QComboBox()
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo, 1)
        layout.addLayout(device_layout)
        
        # Level meter
        level_layout = QVBoxLayout()
        level_label = QLabel("Audio Level:")
        level_layout.addWidget(level_label)
        
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(True)
        self.level_bar.setFormat("%v%")
        level_layout.addWidget(self.level_bar)
        
        # Peak level
        self.peak_label = QLabel("Peak: 0.0 dB")
        self.peak_label.setAlignment(Qt.AlignRight)
        level_layout.addWidget(self.peak_label)
        
        layout.addLayout(level_layout)
        
        # Status
        self.status_label = QLabel("Click 'Start Test' to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #858585; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Test")
        self.start_btn.clicked.connect(self._on_start_stop)
        button_layout.addWidget(self.start_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Timer for UI updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_level)
        
        # Audio buffer
        self._audio_buffer = np.zeros(1024)
    
    def _populate_devices(self):
        """Populate microphone device dropdown"""
        try:
            devices = sd.query_devices()
            self._input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    name = device['name']
                    is_default = "⭐ " if i == sd.default.device[0] else ""
                    self.device_combo.addItem(f"{is_default}[{i}] {name}", i)
                    self._input_devices.append(i)
            
            if not self._input_devices:
                self.device_combo.addItem("❌ No input devices found", -1)
                self.start_btn.setEnabled(False)
        
        except Exception as e:
            self.device_combo.addItem(f"Error: {e}", -1)
            self.start_btn.setEnabled(False)
    
    def _on_start_stop(self):
        """Start or stop audio test"""
        if self._is_testing:
            self._stop_test()
        else:
            self._start_test()
    
    def _start_test(self):
        """Start audio capture"""
        device_id = self.device_combo.currentData()
        if device_id is None or device_id < 0:
            QMessageBox.warning(self, "Error", "No valid microphone selected")
            return
        
        try:
            self._stream = sd.InputStream(
                device=device_id,
                channels=1,
                samplerate=16000,
                blocksize=1024,
                callback=self._audio_callback
            )
            self._stream.start()
            
            self._is_testing = True
            self.start_btn.setText("⏹ Stop Test")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF5630;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FF6B4A;
                }
            """)
            self.status_label.setText("🎤 Listening... Speak into your microphone")
            self.status_label.setStyleSheet("color: #4ec9b0;")
            self._timer.start(50)  # Update UI every 50ms
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start audio: {e}")
    
    def _stop_test(self):
        """Stop audio capture"""
        self._timer.stop()
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        self._is_testing = False
        self.start_btn.setText("▶ Start Test")
        self.start_btn.setStyleSheet("")  # Reset to default
        self.status_label.setText("Click 'Start Test' to begin")
        self.status_label.setStyleSheet("color: #858585; font-style: italic;")
        self.level_bar.setValue(0)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Audio callback from sounddevice"""
        if status:
            print(f"Audio status: {status}")
        
        # Store audio data
        self._audio_buffer = indata.copy()
    
    def _update_level(self):
        """Update level meter UI"""
        # Calculate RMS level
        rms = np.sqrt(np.mean(self._audio_buffer ** 2))
        
        # Convert to dB
        if rms > 0:
            db = 20 * np.log10(rms)
        else:
            db = -60
        
        # Normalize to 0-100 for progress bar (-60dB to 0dB range)
        level = min(100, max(0, (db + 60) / 60 * 100))
        self.level_bar.setValue(int(level))
        
        # Update peak
        if db > self._peak_level:
            self._peak_level = db
            self.peak_label.setText(f"Peak: {db:.1f} dB")
        
        # Color coding based on level
        if level < 30:
            self.level_bar.setStyleSheet("""
                QProgressBar::chunk { background-color: #FF5630; }
            """)  # Red - too quiet
        elif level < 70:
            self.level_bar.setStyleSheet("""
                QProgressBar::chunk { background-color: #4ec9b0; }
            """)  # Green - good
        else:
            self.level_bar.setStyleSheet("""
                QProgressBar::chunk { background-color: #FFAB00; }
            """)  # Yellow - loud
    
    def closeEvent(self, event):
        """Clean up on close"""
        self._stop_test()
        event.accept()


def test_audio_dialog():
    """Test the audio dialog standalone"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = AudioTestDialog()
    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    test_audio_dialog()
