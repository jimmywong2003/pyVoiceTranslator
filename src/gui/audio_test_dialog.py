"""
Audio Test Dialog
=================

Real-time microphone audio level test with visual meter and loopback recording.
"""

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, Slot
from PySide6.QtGui import QFont

import sounddevice as sd


class RecordingThread(QThread):
    """Thread for recording audio without blocking UI."""
    
    finished = Signal(np.ndarray)
    progress = Signal(int)
    
    def __init__(self, device_id, duration=3, sample_rate=16000):
        super().__init__()
        self.device_id = device_id
        self.duration = duration
        self.sample_rate = sample_rate
        self._is_recording = False
        self._buffer = []
    
    def run(self):
        """Record audio for specified duration."""
        self._is_recording = True
        self._buffer = []
        
        def callback(indata, frames, time_info, status):
            if self._is_recording:
                self._buffer.append(indata.copy())
        
        try:
            with sd.InputStream(
                device=self.device_id,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=1024,
                callback=callback
            ):
                # Record for duration
                for i in range(self.duration * 10):  # Update every 100ms
                    if not self._is_recording:
                        break
                    self.progress.emit(int((i / (self.duration * 10)) * 100))
                    self.msleep(100)
                
                self.progress.emit(100)
        except Exception as e:
            print(f"Recording error: {e}")
            self.finished.emit(np.array([]))
            return
        
        # Concatenate buffer
        if self._buffer:
            recording = np.concatenate(self._buffer, axis=0)
            self.finished.emit(recording)
        else:
            self.finished.emit(np.array([]))
    
    def stop(self):
        """Stop recording early."""
        self._is_recording = False


class AudioTestDialog(QDialog):
    """
    Dialog for testing microphone input with visual level meter and loopback.
    
    Features:
    - Device selection dropdown
    - Real-time audio level visualization
    - Peak level indicator
    - Start/Stop test controls
    - Record and playback loopback test
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎤 Audio Test")
        self.setMinimumSize(500, 400)
        
        self._stream = None
        self._is_testing = False
        self._peak_level = 0.0
        self._recording = None
        self._recording_thread = None
        self._is_recording = False
        
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
            QGroupBox {
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🎤 Microphone Audio Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Test your microphone with real-time level meter or loopback recording.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("Microphone:")
        self.device_combo = QComboBox()
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo, 1)
        layout.addLayout(device_layout)
        
        # ============ Live Level Meter Section ============
        level_group = QGroupBox("📊 Live Level Meter")
        level_layout = QVBoxLayout(level_group)
        
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
        
        # Live test button
        self.live_btn = QPushButton("▶ Start Live Test")
        self.live_btn.clicked.connect(self._on_live_test)
        level_layout.addWidget(self.live_btn)
        
        layout.addWidget(level_group)
        
        # ============ Loopback Test Section ============
        loopback_group = QGroupBox("🔄 Loopback Test (Record & Playback)")
        loopback_layout = QVBoxLayout(loopback_group)
        
        loopback_desc = QLabel("Record 3 seconds of audio, then play it back to confirm your microphone works.")
        loopback_desc.setWordWrap(True)
        loopback_desc.setStyleSheet("color: #858585; font-size: 11px;")
        loopback_layout.addWidget(loopback_desc)
        
        # Recording progress
        self.record_progress = QProgressBar()
        self.record_progress.setRange(0, 100)
        self.record_progress.setValue(0)
        self.record_progress.setTextVisible(True)
        self.record_progress.setFormat("Recording: %p%")
        self.record_progress.setVisible(False)
        loopback_layout.addWidget(self.record_progress)
        
        # Recording status
        self.record_status = QLabel("Ready to record")
        self.record_status.setAlignment(Qt.AlignCenter)
        self.record_status.setStyleSheet("color: #858585; font-style: italic;")
        loopback_layout.addWidget(self.record_status)
        
        # Record/Play buttons
        loopback_btn_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("⏺ Record (3s)")
        self.record_btn.clicked.connect(self._on_record)
        loopback_btn_layout.addWidget(self.record_btn)
        
        self.play_btn = QPushButton("▶ Play Back")
        self.play_btn.clicked.connect(self._on_playback)
        self.play_btn.setEnabled(False)
        loopback_btn_layout.addWidget(self.play_btn)
        
        loopback_layout.addLayout(loopback_btn_layout)
        
        layout.addWidget(loopback_group)
        
        # Status
        self.status_label = QLabel("Select a test to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #858585; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
        
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
                self.live_btn.setEnabled(False)
                self.record_btn.setEnabled(False)
        
        except Exception as e:
            self.device_combo.addItem(f"Error: {e}", -1)
            self.live_btn.setEnabled(False)
            self.record_btn.setEnabled(False)
    
    def _on_live_test(self):
        """Start or stop live audio test"""
        if self._is_testing:
            self._stop_live_test()
        else:
            self._start_live_test()
    
    def _start_live_test(self):
        """Start live audio capture"""
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
            self.live_btn.setText("⏹ Stop Live Test")
            self.live_btn.setStyleSheet("""
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
            self.status_label.setText("🎤 Live test active - Speak into your microphone")
            self.status_label.setStyleSheet("color: #4ec9b0;")
            self._timer.start(50)  # Update UI every 50ms
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start audio: {e}")
    
    def _stop_live_test(self):
        """Stop live audio capture"""
        self._timer.stop()
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        self._is_testing = False
        self.live_btn.setText("▶ Start Live Test")
        self.live_btn.setStyleSheet("")  # Reset to default
        self.status_label.setText("Select a test to begin")
        self.status_label.setStyleSheet("color: #858585; font-style: italic;")
        self.level_bar.setValue(0)
        self.peak_label.setText("Peak: 0.0 dB")
    
    def _on_record(self):
        """Start recording for loopback test."""
        if self._is_recording:
            self._stop_recording()
            return
        
        device_id = self.device_combo.currentData()
        if device_id is None or device_id < 0:
            QMessageBox.warning(self, "Error", "No valid microphone selected")
            return
        
        # Stop live test if running
        if self._is_testing:
            self._stop_live_test()
        
        # Disable buttons during recording
        self.record_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.live_btn.setEnabled(False)
        
        # Show progress
        self.record_progress.setVisible(True)
        self.record_progress.setValue(0)
        self.record_status.setText("🔴 Recording... Speak now!")
        self.record_status.setStyleSheet("color: #FF5630; font-weight: bold;")
        self.status_label.setText("Recording 3 seconds of audio...")
        
        # Start recording thread
        self._is_recording = True
        self._recording_thread = RecordingThread(device_id, duration=3)
        self._recording_thread.progress.connect(self._on_record_progress)
        self._recording_thread.finished.connect(self._on_record_finished)
        self._recording_thread.start()
    
    def _on_record_progress(self, percent):
        """Update recording progress bar."""
        self.record_progress.setValue(percent)
    
    def _on_record_finished(self, recording):
        """Handle recording completion."""
        self._is_recording = False
        self._recording = recording
        
        # Enable buttons
        self.record_btn.setEnabled(True)
        self.live_btn.setEnabled(True)
        
        if len(recording) > 0:
            self.play_btn.setEnabled(True)
            self.record_status.setText("✅ Recording complete! Click 'Play Back' to hear.")
            self.record_status.setStyleSheet("color: #4ec9b0;")
            self.status_label.setText(f"Recorded {len(recording)/16000:.1f} seconds of audio")
            self.record_btn.setText("⏺ Record Again (3s)")
        else:
            self.record_status.setText("❌ Recording failed. Please try again.")
            self.record_status.setStyleSheet("color: #FF5630;")
            self.status_label.setText("Recording failed")
        
        self.record_progress.setVisible(False)
    
    def _stop_recording(self):
        """Stop recording early."""
        if self._recording_thread:
            self._recording_thread.stop()
            self._recording_thread.wait()
    
    def _on_playback(self):
        """Play back the recorded audio."""
        if self._recording is None or len(self._recording) == 0:
            QMessageBox.warning(self, "Error", "No recording to play")
            return
        
        try:
            self.status_label.setText("🔊 Playing back recording...")
            self.play_btn.setEnabled(False)
            self.record_btn.setEnabled(False)
            
            # Play audio in a separate thread to not block UI
            import threading
            def play_audio():
                try:
                    sd.play(self._recording, samplerate=16000)
                    sd.wait()  # Wait until playback is done
                    # Re-enable buttons on main thread
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(
                        self, "on_playback_finished",
                        Qt.QueuedConnection
                    )
                except Exception as e:
                    print(f"Playback error: {e}")
                    QMetaObject.invokeMethod(
                        self, "on_playback_finished",
                        Qt.QueuedConnection
                    )
            
            threading.Thread(target=play_audio, daemon=True).start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to play audio: {e}")
            self.on_playback_finished()
    
    @Slot()
    def on_playback_finished(self):
        """Called when playback finishes."""
        self.play_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.status_label.setText("✅ Playback complete! Can you hear yourself?")
        self.status_label.setStyleSheet("color: #4ec9b0;")
    
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
        self._stop_live_test()
        if self._recording_thread and self._recording_thread.isRunning():
            self._recording_thread.stop()
            self._recording_thread.wait()
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
