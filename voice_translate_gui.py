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
    QStatusBar, QProgressBar, QMessageBox, QSplitter, QFrame,
    QTabWidget, QFileDialog, QCheckBox, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QPen

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
    audio_level = Signal(float)  # Audio level 0.0-1.0
    
    def __init__(self, config: PipelineConfig, device_index: Optional[int] = None):
        super().__init__()
        self.config = config
        self.device_index = device_index
        self.pipeline = TranslationPipeline(config)
        self._is_running = False
        self._audio_manager = None
        self._vad = None
    
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
            
            # Set up audio monitoring for level indicator
            self._setup_audio_monitor()
            
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
                time.sleep(0.05)
                self._monitor_audio()
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self._is_running = False
            self.stopped_signal.emit()
    
    def _setup_audio_monitor(self):
        """Set up audio monitoring for level indicator."""
        try:
            from audio_module import AudioManager, AudioConfig
            audio_config = AudioConfig(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=50
            )
            self._audio_manager = AudioManager(audio_config)
        except Exception as e:
            logger.warning(f"Could not set up audio monitor: {e}")
    
    def _monitor_audio(self):
        """Monitor audio levels."""
        # This is a simplified approach - the actual audio capture is in the pipeline
        # We estimate level based on recent activity
        pass
    
    def update_audio_level(self, level: float):
        """Update audio level from external source."""
        self.audio_level.emit(level)
    
    def _on_output(self, output: TranslationOutput):
        """Handle translation output."""
        self.output_ready.emit(output)
    
    def stop(self):
        """Stop the pipeline."""
        self._is_running = False
        if self.pipeline:
            self.pipeline.stop()
        self.wait(5000)  # Wait up to 5 seconds


class AudioLevelIndicator(QWidget):
    """Simple audio level indicator bar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 24)
        self.setMaximumHeight(24)
        self.level = 0.0
        self.is_active = False
    
    def set_level(self, level: float):
        """Update audio level (0.0 to 1.0)."""
        self.level = max(0.0, min(1.0, level))
        self.is_active = level > 0.01
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background
        painter.fillRect(0, 0, width, height, QColor("#2d2d30"))
        
        if self.is_active:
            # Calculate color based on level (green -> yellow -> red)
            if self.level < 0.6:
                color = QColor("#4ec9b0")  # Green
            elif self.level < 0.85:
                color = QColor("#ffd700")  # Yellow
            else:
                color = QColor("#ff6b6b")  # Red
            
            # Draw level bar
            bar_width = int(width * self.level)
            painter.fillRect(0, 0, bar_width, height, color)
        
        # Draw border
        painter.setPen(QPen(QColor("#5a5a5a"), 1))
        painter.drawRect(0, 0, width - 1, height - 1)


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


class VideoTranslationWorker(QThread):
    """Worker thread for video translation."""
    
    progress = Signal(float, str)
    finished_signal = Signal(object)
    error_occurred = Signal(str)
    
    def __init__(self, video_path: str, source_lang: str, target_lang: str, 
                 asr_model: str = "base", export_srt: bool = False, export_vtt: bool = False):
        super().__init__()
        self.video_path = video_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.asr_model = asr_model
        self.export_srt = export_srt
        self.export_vtt = export_vtt
        self._is_cancelled = False
    
    def run(self):
        try:
            from voice_translation.src.asr.faster_whisper import FasterWhisperASR
            from voice_translation.src.translation.marian import MarianTranslator
            from voice_translation.src.pipeline.batch import BatchVideoTranslator
            
            # Initialize components
            self.progress.emit(0.05, "Initializing ASR...")
            asr = FasterWhisperASR(
                model_size=self.asr_model,
                device="cpu",
                compute_type="int8",
                language=self.source_lang
            )
            asr.initialize()
            
            self.progress.emit(0.1, "Initializing translator...")
            translator = MarianTranslator(
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                device="auto"
            )
            translator.initialize()
            
            # Create pipeline
            def progress_callback(p, msg):
                if self._is_cancelled:
                    raise InterruptedError("Cancelled by user")
                self.progress.emit(0.1 + 0.8 * p, msg)
            
            pipeline = BatchVideoTranslator(
                asr=asr,
                translator=translator,
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                progress_callback=progress_callback
            )
            
            # Process video
            result = pipeline.process(self.video_path)
            
            if self._is_cancelled:
                return
            
            self.finished_signal.emit(result)
            
        except InterruptedError:
            pass
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        self._is_cancelled = True


class VoiceTranslateMainWindow(QMainWindow):
    """Main application window with tabs for Real-time and Video translation."""
    
    def __init__(self):
        super().__init__()
        self.config = GUIConfig()
        self.worker: Optional[TranslationWorker] = None
        self.video_worker: Optional[VideoTranslationWorker] = None
        
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
        
        # Create tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # === Real-time Tab ===
        self._setup_realtime_tab()
        
        # === Video Tab ===
        self._setup_video_tab()
    
    def _setup_realtime_tab(self):
        """Setup the real-time translation tab."""
        realtime_widget = QWidget()
        layout = QVBoxLayout(realtime_widget)
        layout.setSpacing(15)
        
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
        self.model_combo.addItems(["base (balanced)", "tiny (fast)", "small (accurate)"])  # Changed default to base
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
        
        # === Audio Level Panel ===
        level_group = QGroupBox("Audio Input Level")
        level_layout = QHBoxLayout(level_group)
        
        self.audio_level_indicator = AudioLevelIndicator()
        level_layout.addWidget(self.audio_level_indicator)
        
        self.level_status_label = QLabel("No audio")
        self.level_status_label.setStyleSheet("color: #858585; font-size: 11px;")
        level_layout.addWidget(self.level_status_label)
        
        main_layout.addWidget(level_group)
        
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
        
        # Add realtime tab
        self.tabs.addTab(realtime_widget, "🎤 Real-time")
    
    def _setup_video_tab(self):
        """Setup the video translation tab."""
        video_widget = QWidget()
        layout = QVBoxLayout(video_widget)
        layout.setSpacing(15)
        
        # === File Selection ===
        file_group = QGroupBox("Video File")
        file_layout = QHBoxLayout(file_group)
        
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("Select a video file...")
        file_layout.addWidget(self.video_path_edit)
        
        browse_btn = QPushButton("📁 Browse...")
        browse_btn.clicked.connect(self._on_browse_video)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # === Settings ===
        settings_group = QGroupBox("Translation Settings")
        settings_layout = QHBoxLayout(settings_group)
        
        # Source language
        self.video_source_combo = QComboBox()
        self.video_source_combo.addItems(["Chinese (zh)", "English (en)", 
                                          "Japanese (ja)", "French (fr)"])
        self.video_source_combo.setCurrentIndex(1)  # Default: English
        settings_layout.addWidget(QLabel("Source:"))
        settings_layout.addWidget(self.video_source_combo)
        
        # Target language
        self.video_target_combo = QComboBox()
        self.video_target_combo.addItems(["Chinese (zh)", "English (en)", 
                                          "Japanese (ja)", "French (fr)"])
        settings_layout.addWidget(QLabel("Target:"))
        settings_layout.addWidget(self.video_target_combo)
        
        # ASR Model
        self.video_model_combo = QComboBox()
        self.video_model_combo.addItems(["base (balanced)", "tiny (fast)", "small (accurate)"])
        settings_layout.addWidget(QLabel("ASR Model:"))
        settings_layout.addWidget(self.video_model_combo)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # === Export Options ===
        export_group = QGroupBox("Export Options")
        export_layout = QHBoxLayout(export_group)
        
        self.export_srt_check = QCheckBox("Export SRT subtitles")
        self.export_srt_check.setChecked(True)
        export_layout.addWidget(self.export_srt_check)
        
        self.export_vtt_check = QCheckBox("Export VTT subtitles")
        export_layout.addWidget(self.export_vtt_check)
        
        export_layout.addStretch()
        layout.addWidget(export_group)
        
        # === Progress ===
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.video_progress = QProgressBar()
        self.video_progress.setRange(0, 100)
        self.video_progress.setValue(0)
        progress_layout.addWidget(self.video_progress)
        
        self.video_status = QLabel("Ready")
        progress_layout.addWidget(self.video_status)
        
        layout.addWidget(progress_group)
        
        # === Results ===
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        self.video_results = QTextEdit()
        self.video_results.setReadOnly(True)
        results_layout.addWidget(self.video_results)
        
        layout.addWidget(results_group, stretch=1)
        
        # === Controls ===
        control_layout = QHBoxLayout()
        
        self.video_start_btn = QPushButton("▶ Start Translation")
        self.video_start_btn.setMinimumHeight(40)
        self.video_start_btn.clicked.connect(self._on_video_start)
        control_layout.addWidget(self.video_start_btn)
        
        self.video_cancel_btn = QPushButton("⏹ Cancel")
        self.video_cancel_btn.setMinimumHeight(40)
        self.video_cancel_btn.clicked.connect(self._on_video_cancel)
        self.video_cancel_btn.setEnabled(False)
        control_layout.addWidget(self.video_cancel_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Add video tab
        self.tabs.addTab(video_widget, "🎬 Video")
    
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
            enable_translation=True,
            audio_device_index=4  # Default to MacBook Pro Microphone
        )
        
        # Create and start worker (use device from config)
        self.worker = TranslationWorker(config, device_index=config.audio_device_index)
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
    
    # === Video Translation Methods ===
    
    def _on_browse_video(self):
        """Open file dialog to select video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.webm);;All Files (*)"
        )
        if file_path:
            self.video_path_edit.setText(file_path)
    
    def _on_video_start(self):
        """Start video translation."""
        video_path = self.video_path_edit.text().strip()
        if not video_path:
            QMessageBox.warning(self, "Warning", "Please select a video file first.")
            return
        
        # Get settings
        source_lang = self.video_source_combo.currentText()[-3:-1]
        target_lang = self.video_target_combo.currentText()[-3:-1]
        model_size = self.video_model_combo.currentText().split()[0]
        export_srt = self.export_srt_check.isChecked()
        export_vtt = self.export_vtt_check.isChecked()
        
        # Create worker
        self.video_worker = VideoTranslationWorker(
            video_path=video_path,
            source_lang=source_lang,
            target_lang=target_lang,
            asr_model=model_size,
            export_srt=export_srt,
            export_vtt=export_vtt
        )
        
        self.video_worker.progress.connect(self._on_video_progress)
        self.video_worker.finished_signal.connect(self._on_video_finished)
        self.video_worker.error_occurred.connect(self._on_video_error)
        
        # Update UI
        self.video_start_btn.setEnabled(False)
        self.video_cancel_btn.setEnabled(True)
        self.video_progress.setValue(0)
        self.video_results.clear()
        
        self.video_worker.start()
    
    def _on_video_cancel(self):
        """Cancel video translation."""
        if self.video_worker:
            self.video_worker.cancel()
            self.video_status.setText("Cancelling...")
    
    @Slot(float, str)
    def _on_video_progress(self, progress: float, message: str):
        """Update video translation progress."""
        self.video_progress.setValue(int(progress * 100))
        self.video_status.setText(message)
    
    @Slot(object)
    def _on_video_finished(self, result):
        """Handle video translation completion."""
        self.video_start_btn.setEnabled(True)
        self.video_cancel_btn.setEnabled(False)
        self.video_progress.setValue(100)
        
        if result.is_success:
            self.video_status.setText("Complete!")
            
            # Display results
            html = f"""
            <h3>✅ Translation Complete</h3>
            <p><b>Duration:</b> {result.source_duration:.1f}s</p>
            <p><b>Processing Time:</b> {result.processing_time:.1f}s</p>
            <p><b>Confidence:</b> {result.confidence:.2f}</p>
            <hr>
            <p><b>Source ({result.source_language}):</b><br>{result.source_text[:500]}...</p>
            <hr>
            <p><b>Translation ({result.target_language}):</b><br>{result.translated_text[:500]}...</p>
            """
            self.video_results.setHtml(html)
            
            # Export subtitles
            from pathlib import Path
            video_path = Path(self.video_path_edit.text())
            exports = []
            
            if self.export_srt_check.isChecked():
                srt_file = video_path.parent / f"{video_path.stem}_{result.target_language}.srt"
                srt_file.write_text(result.to_srt(), encoding='utf-8')
                exports.append(f"SRT: {srt_file.name}")
            
            if self.export_vtt_check.isChecked():
                vtt_file = video_path.parent / f"{video_path.stem}_{result.target_language}.vtt"
                vtt_file.write_text(result.to_vtt(), encoding='utf-8')
                exports.append(f"VTT: {vtt_file.name}")
            
            if exports:
                html += f"<hr><p><b>Exported:</b><br>{'<br>'.join(exports)}</p>"
                self.video_results.setHtml(html)
        else:
            self.video_status.setText("Failed")
            self.video_results.setPlainText(f"Error: {result.errors}")
    
    @Slot(str)
    def _on_video_error(self, error: str):
        """Handle video translation error."""
        self.video_start_btn.setEnabled(True)
        self.video_cancel_btn.setEnabled(False)
        self.video_status.setText("Error")
        self.video_results.setPlainText(f"Error: {error}")
        QMessageBox.critical(self, "Error", f"Video translation failed:\n{error}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        if self.video_worker and self.video_worker.isRunning():
            self.video_worker.cancel()
            self.video_worker.wait(2000)
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
