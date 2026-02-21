"""
Meeting Toolbar
===============

Toolbar controls for meeting mode.
"""

from typing import Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QSpinBox, QFileDialog
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon

from src.core.meeting.export import ExportFormat


class MeetingToolbar(QWidget):
    """
    Toolbar for meeting mode controls.
    
    Signals:
        start_meeting: Emitted when start button clicked
        pause_meeting: Emitted when pause button clicked
        stop_meeting: Emitted when stop button clicked
        export_requested: Emitted when export button clicked
        speaker_count_changed: Emitted when speaker count changes
    """
    
    start_meeting = Signal()
    pause_meeting = Signal()
    stop_meeting = Signal()
    export_requested = Signal(str, int)  # filepath, format
    speaker_count_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._is_paused = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup toolbar UI"""
        self.setStyleSheet("""
            MeetingToolbar {
                background-color: #252536;
                border-bottom: 1px solid #3A3A4A;
                padding: 8px;
            }
            QPushButton {
                background-color: #6C5DD3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7D6EE4;
            }
            QPushButton:pressed {
                background-color: #5B4CC2;
            }
            QPushButton:disabled {
                background-color: #3A3A4A;
                color: #6B6B7B;
            }
            QPushButton#stopButton {
                background-color: #FF5630;
            }
            QPushButton#stopButton:hover {
                background-color: #FF6B4A;
            }
            QPushButton#exportButton {
                background-color: #36B37E;
            }
            QPushButton#exportButton:hover {
                background-color: #47C48F;
            }
            QLabel {
                color: #E8E8ED;
                font-size: 13px;
            }
            QComboBox, QSpinBox {
                background-color: #1E1E2E;
                color: #E8E8ED;
                border: 1px solid #3A3A4A;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #252536;
                color: #E8E8ED;
                selection-background-color: #6C5DD3;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Control buttons
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setToolTip("Start recording meeting")
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setToolTip("Pause recording")
        self.pause_btn.clicked.connect(self._on_pause)
        self.pause_btn.setEnabled(False)
        layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setToolTip("Stop and save meeting")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        # Separator
        layout.addSpacing(20)
        
        # Speaker count selector
        speaker_label = QLabel("Speakers:")
        layout.addWidget(speaker_label)
        
        self.speaker_spin = QSpinBox()
        self.speaker_spin.setRange(2, 8)
        self.speaker_spin.setValue(4)
        self.speaker_spin.valueChanged.connect(self.speaker_count_changed.emit)
        layout.addWidget(self.speaker_spin)
        
        # Stretch
        layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("📥 Export")
        self.export_btn.setObjectName("exportButton")
        self.export_btn.setToolTip("Export meeting transcript")
        self.export_btn.clicked.connect(self._on_export)
        layout.addWidget(self.export_btn)
    
    def _on_start(self):
        """Handle start button click"""
        self._is_recording = True
        self._is_paused = False
        self._update_button_states()
        self.start_meeting.emit()
    
    def _on_pause(self):
        """Handle pause button click"""
        self._is_paused = not self._is_paused
        self._update_button_states()
        self.pause_meeting.emit()
    
    def _on_stop(self):
        """Handle stop button click"""
        self._is_recording = False
        self._is_paused = False
        self._update_button_states()
        self.stop_meeting.emit()
    
    def _on_export(self):
        """Handle export button click"""
        # Open file dialog
        formats = [
            ("Markdown files", "*.md"),
            ("Text files", "*.txt"),
            ("JSON files", "*.json"),
            ("CSV files", "*.csv"),
        ]
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Meeting Transcript",
            "",
            ";;".join([f"{name} ({ext})" for name, ext in formats])
        )
        
        if filepath:
            # Determine format from extension
            ext_map = {
                ".md": 0,    # MARKDOWN
                ".txt": 1,   # TEXT
                ".json": 2,  # JSON
                ".csv": 3,   # CSV
            }
            ext = filepath.lower()[filepath.rfind("."):]
            format_idx = ext_map.get(ext, 0)
            
            self.export_requested.emit(filepath, format_idx)
    
    def _update_button_states(self):
        """Update button states based on recording state"""
        if self._is_recording:
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            
            if self._is_paused:
                self.pause_btn.setText("▶ Resume")
                self.start_btn.setText("⏸ Paused")
            else:
                self.pause_btn.setText("⏸ Pause")
                self.start_btn.setText("● Recording...")
        else:
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.start_btn.setText("▶ Start")
            self.pause_btn.setText("⏸ Pause")
    
    def set_recording_state(self, recording: bool, paused: bool = False):
        """Set recording state programmatically"""
        self._is_recording = recording
        self._is_paused = paused
        self._update_button_states()
    
    def get_speaker_count(self) -> int:
        """Get selected speaker count"""
        return self.speaker_spin.value()
