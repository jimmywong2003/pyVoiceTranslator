#!/usr/bin/env python3
"""
VoiceTranslate Pro - PySide6 GUI Application
Phase 6: Real-time Voice Translation GUI

Usage:
    python voice_translate_gui.py
"""

import sys
import time
import logging
from typing import Optional
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox,
    QStatusBar, QProgressBar, QMessageBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

# Import pipeline components
from voice_translation.src.pipeline.orchestrator import (
    TranslationPipeline, PipelineConfig, TranslationOutput
)
from audio_module import AudioSource

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GUIConfig:
    """GUI configuration."""
    window_title: str = "VoiceTranslate Pro"
    window_width: int = 900
    window_height: int = 700
    update_interval_ms: int = 100


class TranslationWorker(QThread):
    """Worker thread for running translation pipeline."""
    
    # Signals
    output_ready = Signal(TranslationOutput)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    started_signal = Signal()
    stopped_signal = Signal()
    
    def __init__(self, config: PipelineConfig, device_index: Optional[int] = None):
        super().__init__()
        self.config = config
        self.device_index = device_index
        self.pipeline = TranslationPipeline(config)
        self._is_running = False
    
    def run(self):
        """Run the translation pipeline."""
        try:
            self._is_running = True
            self.status_changed.emit("Initializing...")
            
            if not self.pipeline.initialize():
                self.error_occurred.emit("Failed to initialize pipeline")
                return
            
            self.status_changed.emit("Running")
            self.started_signal.emit()
            
            success = self.pipeline.start(
                output_callback=self._on_output,
                audio_source=AudioSource.MICROPHONE,
                device_index=self.device_index
            )
            
            if not success:
                self.error_occurred.emit("Failed to start pipeline")
                return
            
            # Keep thread alive while running
            while self._is_running and self.pipeline.is_running:
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self._is_running = False
            self.stopped_signal.emit()
    
    def _on_output(self, output: TranslationOutput):
        """Handle translation output."""
        self.output_ready.emit(output)
    
    def stop(self):
        """Stop the pipeline."""
        self._is_running = False
        if self.pipeline:
            self.pipeline.stop()
        self.wait(5000)  # Wait up to 5 seconds


class TranslationDisplay(QTextEdit):
    """Custom text display for translation output."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
    
    def add_translation(self, source_text: str, translated_text: str, 
                       source_lang: str, target_lang: str, 
                       processing_time_ms: float, confidence: float):
        """Add a translation entry to the display."""
        timestamp = time.strftime("%H:%M:%S")
        
        html = f"""
        <div style="margin-bottom: 15px; padding: 10px; background-color: #2d2d2d; border-radius: 5px;">
            <div style="color: #858585; font-size: 11px; margin-bottom: 5px;">
                {timestamp} • {processing_time_ms:.0f}ms • confidence: {confidence:.2f}
            </div>
            <div style="color: #4ec9b0; margin-bottom: 5px;">
                <b>[{source_lang.upper()}]</b> {source_text}
            </div>
            <div style="color: #ce9178;">
                <b>[{target_lang.upper()}]</b> {translated_text}
            </div>
        </div>
        """
        
        self.append(html)
        
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_display(self):
        """Clear the display."""
        self.clear()


class VoiceTranslateMainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.config = GUIConfig()
        self.worker: Optional[TranslationWorker] = None
        
        self.setWindowTitle(self.config.window_title)
        self.setMinimumSize(self.config.window_width, self.config.window_height)
        
        self._setup_ui()
        self._setup_styles()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === Settings Panel ===
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout(settings_group)
        
        # Source language
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["Auto-detect", "Chinese (zh)", "English (en)", 
                                         "Japanese (ja)", "French (fr)"])
        self.source_lang_combo.setCurrentIndex(2)  # Default: English
        settings_layout.addWidget(QLabel("Source:"))
        settings_layout.addWidget(self.source_lang_combo)
        
        # Arrow
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        settings_layout.addWidget(arrow_label)
        
        # Target language
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["Chinese (zh)", "English (en)", 
                                         "Japanese (ja)", "French (fr)"])
        self.target_lang_combo.setCurrentIndex(0)  # Default: Chinese
        settings_layout.addWidget(QLabel("Target:"))
        settings_layout.addWidget(self.target_lang_combo)
        
        settings_layout.addSpacing(20)
        
        # ASR Model
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny (fast)", "base (balanced)", "small (accurate)"])
        settings_layout.addWidget(QLabel("ASR Model:"))
        settings_layout.addWidget(self.model_combo)
        
        settings_layout.addStretch()
        main_layout.addWidget(settings_group)
        
        # === Display Area ===
        display_group = QGroupBox("Live Translation")
        display_layout = QVBoxLayout(display_group)
        
        self.translation_display = TranslationDisplay()
        display_layout.addWidget(self.translation_display)
        
        main_layout.addWidget(display_group, stretch=1)
        
        # === Control Panel ===
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout(control_group)
        
        # Start/Stop button
        self.start_button = QPushButton("▶ Start Translation")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self._on_start_stop)
        control_layout.addWidget(self.start_button)
        
        # Clear button
        self.clear_button = QPushButton("🗑 Clear")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self._on_clear)
        control_layout.addWidget(self.clear_button)
        
        control_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("⏹ Stopped")
        self.status_label.setStyleSheet("color: #858585; font-weight: bold;")
        control_layout.addWidget(self.status_label)
        
        main_layout.addWidget(control_group)
        
        # === Status Bar ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.latency_label = QLabel("Latency: --")
        self.segments_label = QLabel("Segments: 0")
        self.status_bar.addWidget(self.latency_label)
        self.status_bar.addWidget(self.segments_label)
        self.status_bar.showMessage("Ready")
        
        # Timer for UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_stats)
        self.segments_count = 0
    
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
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QLabel {
                color: #cccccc;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
            }
            QStatusBar QLabel {
                color: white;
                padding: 0 10px;
            }
        """)
    
    @Slot()
    def _on_start_stop(self):
        """Handle start/stop button click."""
        if self.worker and self.worker.isRunning():
            self._stop_translation()
        else:
            self._start_translation()
    
    def _start_translation(self):
        """Start the translation pipeline."""
        # Get settings
        source_lang = self.source_lang_combo.currentText()
        target_lang = self.target_lang_combo.currentText()
        model_size = self.model_combo.currentText().split()[0]  # tiny/base/small
        
        # Parse language codes
        source_code = None if "Auto" in source_lang else source_lang[-3:-1]
        target_code = target_lang[-3:-1]
        
        # Create pipeline config
        config = PipelineConfig(
            asr_model_size=model_size,
            asr_language=source_code,
            source_language=source_code or "auto",
            target_language=target_code,
            enable_translation=True
        )
        
        # Create and start worker
        self.worker = TranslationWorker(config)
        self.worker.output_ready.connect(self._on_output)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.started_signal.connect(self._on_worker_started)
        self.worker.stopped_signal.connect(self._on_worker_stopped)
        
        self.worker.start()
        
        # Update UI
        self.start_button.setText("⏹ Stop")
        self.start_button.setStyleSheet("background-color: #c75450;")
        self._set_controls_enabled(False)
    
    def _stop_translation(self):
        """Stop the translation pipeline."""
        if self.worker:
            self.status_label.setText("⏹ Stopping...")
            self.worker.stop()
            self.worker = None
        
        self.update_timer.stop()
        self._on_worker_stopped()
    
    @Slot(TranslationOutput)
    def _on_output(self, output: TranslationOutput):
        """Handle translation output."""
        self.translation_display.add_translation(
            source_text=output.source_text,
            translated_text=output.translated_text or "(no translation)",
            source_lang=output.source_language,
            target_lang=output.target_language,
            processing_time_ms=output.processing_time_ms,
            confidence=output.confidence
        )
        self.segments_count += 1
        self.latency_label.setText(f"Latency: {output.processing_time_ms:.0f}ms")
    
    @Slot(str)
    def _on_status_changed(self, status: str):
        """Handle status changes."""
        self.status_label.setText(f"🟢 {status}")
        self.status_bar.showMessage(f"Status: {status}")
    
    @Slot(str)
    def _on_error(self, error: str):
        """Handle errors."""
        logger.error(f"Pipeline error: {error}")
        QMessageBox.critical(self, "Error", f"Translation pipeline error:\n{error}")
        self._stop_translation()
    
    @Slot()
    def _on_worker_started(self):
        """Handle worker started."""
        self.update_timer.start(self.config.update_interval_ms)
    
    @Slot()
    def _on_worker_stopped(self):
        """Handle worker stopped."""
        self.start_button.setText("▶ Start Translation")
        self.start_button.setStyleSheet("")
        self.status_label.setText("⏹ Stopped")
        self.status_label.setStyleSheet("color: #858585; font-weight: bold;")
        self._set_controls_enabled(True)
    
    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable controls during translation."""
        self.source_lang_combo.setEnabled(enabled)
        self.target_lang_combo.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
    
    @Slot()
    def _on_clear(self):
        """Clear the display."""
        self.translation_display.clear_display()
        self.segments_count = 0
        self.segments_label.setText("Segments: 0")
        self.latency_label.setText("Latency: --")
    
    @Slot()
    def _update_stats(self):
        """Update statistics display."""
        self.segments_label.setText(f"Segments: {self.segments_count}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("VoiceTranslate Pro")
    app.setApplicationVersion("0.5.0")
    
    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = VoiceTranslateMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
