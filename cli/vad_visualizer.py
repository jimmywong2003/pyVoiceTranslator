#!/usr/bin/env python3
"""
VAD Visualizer - Real-time Audio Level and Voice Detection Monitor

Helps verify VAD is working correctly by showing:
- Live audio level meter (VU meter style)
- VAD probability graph
- Speech state indicator (SILENCE/SPEECH)
- Trigger threshold line

Usage:
    python vad_visualizer.py [--device INDEX] [--threshold 0.7]
"""

import sys
import time
import logging
import numpy as np
from typing import Optional
from collections import deque
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QGroupBox,
    QSpinBox, QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient

# Add project paths
sys.path.insert(0, '.')
from src.audio import AudioManager, AudioConfig, AudioSource
from src.audio.vad.silero_vad import SileroVADProcessor, VADState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioLevelMeter(QWidget):
    """Custom VU-style audio level meter widget with speech detection highlight."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(80, 300)
        self.setMaximumWidth(100)
        self.level = 0.0  # 0.0 to 1.0
        self.peak = 0.0
        self.vad_threshold = 0.5
        self.is_speech = False
        self.speech_flash = 0
        
    def set_level(self, level: float, is_speech: bool = False):
        """Update audio level (0.0 to 1.0) and speech state."""
        self.level = max(0.0, min(1.0, level))
        self.peak = max(self.peak * 0.95, self.level)  # Decay peak
        
        # Flash effect when speech starts
        if is_speech and not self.is_speech:
            self.speech_flash = 15
        self.is_speech = is_speech
        if self.speech_flash > 0:
            self.speech_flash -= 1
        
        self.update()
    
    def set_vad_threshold(self, threshold: float):
        """Update VAD threshold line position."""
        self.vad_threshold = threshold
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background - flash bright when speech detected
        if self.speech_flash > 0:
            flash_alpha = int(100 * (self.speech_flash / 15.0))
            bg_color = QColor(0, 255, 0, flash_alpha)
        elif self.is_speech:
            bg_color = QColor("#0d2810")  # Slight green tint during speech
        else:
            bg_color = QColor("#1e1e1e")
        painter.fillRect(0, 0, width, height, bg_color)
        
        # Draw border - green when speech detected
        border_color = QColor("#00ff00") if self.is_speech else QColor("#3c3c3c")
        border_width = 3 if self.is_speech else 1
        painter.setPen(QPen(border_color, border_width))
        painter.drawRect(border_width//2, border_width//2, 
                        width - border_width, height - border_width)
        
        # Create gradient (green -> yellow -> red)
        gradient = QLinearGradient(0, height, 0, 0)
        if self.is_speech:
            # Brighter colors during speech
            gradient.setColorAt(0.0, QColor("#00ff00"))
            gradient.setColorAt(0.5, QColor("#ccff00"))
            gradient.setColorAt(0.75, QColor("#ffff00"))
            gradient.setColorAt(1.0, QColor("#ff4400"))
        else:
            gradient.setColorAt(0.0, QColor("#00aa00"))
            gradient.setColorAt(0.6, QColor("#aaaa00"))
            gradient.setColorAt(0.85, QColor("#aa6600"))
            gradient.setColorAt(1.0, QColor("#aa0000"))
        
        # Draw level bar with glow effect during speech
        bar_height = int(height * self.level)
        if bar_height > 0:
            x = 15
            bar_width = width - 30
            y = height - bar_height
            
            # Glow effect during speech
            if self.is_speech:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(0, 255, 0, 50))
                painter.drawRect(x - 4, y - 4, bar_width + 8, bar_height + 8)
            
            painter.fillRect(x, y, bar_width, bar_height, gradient)
        
        # Draw peak indicator
        peak_y = height - int(height * self.peak)
        peak_color = QColor("#ffffff") if not self.is_speech else QColor("#00ff00")
        painter.fillRect(15, peak_y - 2, width - 30, 4, peak_color)
        
        # Draw VAD threshold line with label
        threshold_y = height - int(height * self.vad_threshold)
        painter.setPen(QPen(QColor("#00aaff"), 2, Qt.DashLine))
        painter.drawLine(5, threshold_y, width - 5, threshold_y)
        
        # Threshold label
        painter.setPen(QColor("#00aaff"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(5, threshold_y - 3, "VAD")
        
        # Draw scale markers
        painter.setPen(QPen(QColor("#666666"), 1))
        for i in range(0, 11):
            y = height - int(height * i / 10)
            painter.drawLine(0, y, 10, y)
            painter.drawLine(width - 10, y, width, y)
            # Scale labels
            if i % 2 == 0:
                painter.setPen(QColor("#888888"))
                painter.setFont(QFont("Segoe UI", 7))
                painter.drawText(2, y + 3, f"{i}")
                painter.setPen(QPen(QColor("#666666"), 1))
        
        # Draw SPEECH label when active
        if self.is_speech:
            painter.setPen(QColor("#00ff00"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(10, 20, "🎤")
            
            # Draw level value
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(5, height - 10, f"{self.level:.2f}")


class VADGraph(QWidget):
    """Real-time VAD probability graph with clear speech indication."""
    
    def __init__(self, history_size: int = 200, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 180)
        self.history = deque([0.0] * history_size, maxlen=history_size)
        self.threshold = 0.5
        self.is_speech = False
        self.speech_flash = 0  # Flash counter for speech detection
        
    def add_value(self, prob: float, is_speech: bool):
        """Add new VAD probability value."""
        self.history.append(prob)
        # Flash effect when speech starts
        if is_speech and not self.is_speech:
            self.speech_flash = 10  # Flash for 10 frames
        self.is_speech = is_speech
        if self.speech_flash > 0:
            self.speech_flash -= 1
        self.update()
    
    def set_threshold(self, threshold: float):
        """Update threshold line."""
        self.threshold = threshold
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background - bright green flash when speech detected
        if self.speech_flash > 0:
            flash_intensity = self.speech_flash / 10.0
            r = int(45 + 100 * flash_intensity)
            g = int(200 + 55 * flash_intensity)
            b = int(48 + 20 * flash_intensity)
            bg_color = QColor(r, g, b)
        elif self.is_speech:
            bg_color = QColor("#1a3d1a")  # Dark green during speech
        else:
            bg_color = QColor("#1e1e1e")  # Normal dark
        painter.fillRect(0, 0, width, height, bg_color)
        
        # Draw grid
        painter.setPen(QPen(QColor("#3c3c3c"), 1))
        for i in range(0, 6):
            y = height - int(height * i / 5)
            painter.drawLine(0, y, width, y)
        
        # Draw threshold line
        threshold_y = height - int(height * self.threshold)
        painter.setPen(QPen(QColor("#00aaff"), 2, Qt.DashLine))
        painter.drawLine(0, threshold_y, width, threshold_y)
        
        # Draw VAD probability line
        if len(self.history) > 1:
            # Use bright color during speech
            line_color = QColor("#00ff00") if self.is_speech else QColor("#4ec9b0")
            painter.setPen(QPen(line_color, 3 if self.is_speech else 2))
            
            step = width / len(self.history)
            points = []
            for i, val in enumerate(self.history):
                x = int(i * step)
                y = height - int(height * val)
                points.append((x, y))
            
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], 
                               points[i+1][0], points[i+1][1])
        
        # Draw current value text with background
        if self.history:
            current = self.history[-1]
            text = f"{current:.2f}"
            
            # Draw text background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#000000"))
            painter.drawRoundedRect(8, 5, 50, 22, 3, 3)
            
            # Draw text
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            painter.drawText(12, 22, text)
            
            # Draw SPEECH indicator
            if self.is_speech:
                painter.setPen(QColor("#00ff00"))
                painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
                painter.drawText(width - 100, 25, "🎤 SPEECH")


class VADMonitorThread(QThread):
    """Thread to capture audio and process VAD."""
    
    audio_level = Signal(float, bool)  # level (0.0-1.0), is_speech
    vad_probability = Signal(float, bool)  # prob, is_speech
    speech_detected = Signal(float, float)  # duration, confidence
    state_changed = Signal(str)  # State name
    
    def __init__(self, device_index: Optional[int] = None, threshold: float = 0.5):
        super().__init__()
        self.device_index = device_index
        self.threshold = threshold
        self._is_running = False
        self._audio_manager: Optional[AudioManager] = None
        self._vad: Optional[SileroVADProcessor] = None
        
    def set_threshold(self, threshold: float):
        """Update VAD threshold."""
        self.threshold = threshold
        if self._vad:
            self._vad.threshold = threshold
    
    def run(self):
        """Run the VAD monitor."""
        self._is_running = True
        
        try:
            # Initialize audio
            audio_config = AudioConfig(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30
            )
            self._audio_manager = AudioManager(audio_config)
            
            # Initialize VAD
            self._vad = SileroVADProcessor(
                sample_rate=16000,
                threshold=self.threshold,
                min_speech_duration_ms=250,
                min_silence_duration_ms=100
            )
            
            # Start capture
            self._audio_manager.start_capture(
                AudioSource.MICROPHONE,
                self._process_audio,
                device_index=self.device_index
            )
            
            logger.info("VAD Monitor started")
            
            while self._is_running:
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"VAD Monitor error: {e}")
        finally:
            if self._audio_manager:
                self._audio_manager.stop_capture()
    
    def _process_audio(self, chunk: np.ndarray):
        """Process audio chunk."""
        if not self._is_running:
            return
        
        # Calculate audio level (RMS)
        rms = np.sqrt(np.mean(np.abs(chunk)))
        # Normalize to 0-1 range (assuming 16-bit audio typical range)
        # Typical speech is around 500-2000 RMS for 16-bit audio
        level = min(1.0, rms / 3000)
        
        # Process through VAD
        segment = self._vad.process_chunk(chunk)
        
        # Get VAD probability and state
        if hasattr(self._vad, '_last_prob'):
            prob = self._vad._last_prob
        else:
            # Estimate from state
            prob = 1.0 if self._vad.state == VADState.SPEECH else 0.0
        
        is_speech = self._vad.state == VADState.SPEECH
        
        # Emit audio level with speech state
        self.audio_level.emit(level, is_speech)
        self.vad_probability.emit(prob, is_speech)
        self.state_changed.emit(self._vad.state.value.upper())
        
        # Emit speech segment info
        if segment:
            self.speech_detected.emit(segment.duration, segment.confidence)
    
    def stop(self):
        """Stop the monitor."""
        self._is_running = False


class VADVisualizerWindow(QMainWindow):
    """Main window for VAD visualization."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VAD Visualizer - Voice Activity Detection Monitor")
        self.setMinimumSize(700, 500)
        
        self.monitor_thread: Optional[VADMonitorThread] = None
        self._setup_ui()
        self._setup_styles()
        
        # Update timer for UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_stats)
        self.update_timer.start(100)  # 100ms
        
        self.speech_count = 0
        self.total_speech_duration = 0.0
    
    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # === Left Panel: Visualizers ===
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # Audio Level Meter
        level_group = QGroupBox("Audio Level")
        level_layout = QVBoxLayout(level_group)
        self.level_meter = AudioLevelMeter()
        level_layout.addWidget(self.level_meter, alignment=Qt.AlignCenter)
        left_layout.addWidget(level_group)
        
        # VAD Graph
        graph_group = QGroupBox("VAD Probability History")
        graph_layout = QVBoxLayout(graph_group)
        self.vad_graph = VADGraph(history_size=200)
        graph_layout.addWidget(self.vad_graph)
        
        # State indicator
        self.state_label = QLabel("● SILENCE")
        self.state_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.state_label.setStyleSheet("color: #666666;")
        self.state_label.setAlignment(Qt.AlignCenter)
        graph_layout.addWidget(self.state_label)
        
        left_layout.addWidget(graph_group, stretch=1)
        layout.addWidget(left_panel, stretch=1)
        
        # === Right Panel: Controls & Stats ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        
        # Controls
        controls_group = QGroupBox("Settings")
        controls_layout = QVBoxLayout(controls_group)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Audio Device:"))
        self.device_combo = QComboBox()
        self._populate_devices()
        device_layout.addWidget(self.device_combo)
        controls_layout.addLayout(device_layout)
        
        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("VAD Threshold:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 0.9)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(0.5)
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self.threshold_spin)
        controls_layout.addLayout(threshold_layout)
        
        # Start/Stop button
        self.start_btn = QPushButton("▶ Start Monitoring")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._on_start_stop)
        controls_layout.addWidget(self.start_btn)
        
        right_layout.addWidget(controls_group)
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.speech_count_label = QLabel("Speech Segments: 0")
        self.speech_duration_label = QLabel("Total Duration: 0.0s")
        self.avg_duration_label = QLabel("Avg Duration: 0.0s")
        
        stats_layout.addWidget(self.speech_count_label)
        stats_layout.addWidget(self.speech_duration_label)
        stats_layout.addWidget(self.avg_duration_label)
        
        right_layout.addWidget(stats_group)
        
        # Help text
        help_group = QGroupBox("How to Verify VAD")
        help_layout = QVBoxLayout(help_group)
        help_text = QLabel(
            "<ol>"
            "<li>Click <b>Start Monitoring</b></li>"
            "<li>Speak into your microphone</li>"
            "<li>Watch the <b>Audio Level</b> meter - it should move when you speak</li>"
            "<li>The <b>VAD Probability</b> graph should rise above the blue threshold line</li>"
            "<li>The state should change from <span style='color:#666'>SILENCE</span> to "
            "<span style='color:#4ec9b0'>SPEECH</span></li>"
            "<li>Adjust threshold if needed - lower = more sensitive</li>"
            "</ol>"
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        right_layout.addWidget(help_group)
        
        right_layout.addStretch()
        layout.addWidget(right_panel)
    
    def _populate_devices(self):
        """Populate audio device combo box."""
        import sounddevice as sd
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                self.device_combo.addItem(f"{i}: {dev['name']}", i)
    
    def _setup_styles(self):
        """Setup application styles."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #252526;
            }
            QGroupBox {
                color: #cccccc;
                font-weight: bold;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
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
            QLabel {
                color: #cccccc;
            }
            QComboBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
                padding: 5px;
            }
        """)
    
    def _on_threshold_changed(self, value: float):
        """Handle threshold change."""
        self.level_meter.set_vad_threshold(value)
        self.vad_graph.set_threshold(value)
        if self.monitor_thread:
            self.monitor_thread.set_threshold(value)
    
    def _on_start_stop(self):
        """Handle start/stop button."""
        if self.monitor_thread and self.monitor_thread.isRunning():
            self._stop_monitoring()
        else:
            self._start_monitoring()
    
    def _start_monitoring(self):
        """Start VAD monitoring."""
        device_index = self.device_combo.currentData()
        threshold = self.threshold_spin.value()
        
        self.monitor_thread = VADMonitorThread(device_index, threshold)
        self.monitor_thread.audio_level.connect(self._on_audio_level)
        self.monitor_thread.vad_probability.connect(self._on_vad_prob)
        self.monitor_thread.speech_detected.connect(self._on_speech)
        self.monitor_thread.state_changed.connect(self._on_state_change)
        
        self.monitor_thread.start()
        
        self.start_btn.setText("⏹ Stop Monitoring")
        self.start_btn.setStyleSheet("background-color: #c75450;")
        self.device_combo.setEnabled(False)
    
    def _stop_monitoring(self):
        """Stop VAD monitoring."""
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        
        self.start_btn.setText("▶ Start Monitoring")
        self.start_btn.setStyleSheet("")
        self.device_combo.setEnabled(True)
        
        # Reset displays
        self.level_meter.set_level(0)
        self.state_label.setText("● STOPPED")
        self.state_label.setStyleSheet("color: #666666;")
    
    @Slot(float, bool)
    def _on_audio_level(self, level: float, is_speech: bool):
        """Update audio level meter."""
        self.level_meter.set_level(level, is_speech)
    
    @Slot(float, bool)
    def _on_vad_prob(self, prob: float, is_speech: bool):
        """Update VAD graph."""
        self.vad_graph.add_value(prob, is_speech)
    
    @Slot(str)
    def _on_state_change(self, state: str):
        """Update state indicator with high contrast."""
        if state == "SPEECH":
            self.state_label.setText("🎤 SPEECH DETECTED")
            self.state_label.setStyleSheet("""
                color: #00ff00;
                font-size: 20px;
                font-weight: bold;
                background-color: #1a3d1a;
                padding: 10px;
                border-radius: 5px;
                border: 2px solid #00ff00;
            """)
        else:
            self.state_label.setText("🔇 SILENCE")
            self.state_label.setStyleSheet("""
                color: #666666;
                font-size: 16px;
                font-weight: normal;
                background-color: transparent;
                padding: 10px;
                border-radius: 5px;
                border: 2px solid #3c3c3c;
            """)
    
    @Slot(float, float)
    def _on_speech(self, duration: float, confidence: float):
        """Handle speech detection."""
        self.speech_count += 1
        self.total_speech_duration += duration
    
    def _update_stats(self):
        """Update statistics display."""
        self.speech_count_label.setText(f"Speech Segments: {self.speech_count}")
        self.speech_duration_label.setText(f"Total Duration: {self.total_speech_duration:.1f}s")
        if self.speech_count > 0:
            avg = self.total_speech_duration / self.speech_count
            self.avg_duration_label.setText(f"Avg Duration: {avg:.2f}s")
    
    def closeEvent(self, event):
        """Handle window close."""
        self._stop_monitoring()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VAD Visualizer")
    app.setApplicationVersion("1.0")
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = VADVisualizerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
