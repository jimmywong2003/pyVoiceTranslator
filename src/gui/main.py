#!/usr/bin/env python3
"""
VoiceTranslate Pro - PySide6 GUI Application
Phase 6: Real-time Voice Translation GUI

Usage:
    python src/gui/main.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import time
import logging
from typing import Optional, List
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
from src.core.pipeline.orchestrator import (
    TranslationPipeline, PipelineConfig, TranslationOutput
)
from src.audio import AudioSource

# Setup timestamped logging (must be before other imports that use logger)
from src.core.utils.timestamped_logging import setup_timestamped_logging, log_segment_timing, log_latency_metric
setup_timestamped_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Meeting Mode (Phase 4)
try:
    from src.gui.meeting.window import MeetingWindow
    MEETING_MODE_AVAILABLE = True
except ImportError as e:
    MEETING_MODE_AVAILABLE = False
    logger.warning(f"Meeting Mode not available: {e}")

# Import Phase 5 utilities
try:
    from src.core.utils.debug_logger import DebugLogger, get_debug_logger
    from src.core.utils.performance_monitor import PerformanceMonitor
    from src.core.utils.update_checker import UpdateChecker, UpdateInfo
    PHASE5_AVAILABLE = True
except ImportError as e:
    PHASE5_AVAILABLE = False
    logger.warning(f"Phase 5 utilities not available: {e}")
    DebugLogger = None
    PerformanceMonitor = None
    UpdateChecker = None
    UpdateInfo = None


@dataclass
class GUIConfig:
    """GUI configuration."""
    window_title: str = "VoiceTranslate Pro v0.7.0"
    window_width: int = 900
    window_height: int = 700
    update_interval_ms: int = 100


class TranslationWorker(QThread):
    """Worker thread for running translation pipeline (Parallel version)."""
    
    # Signals
    output_ready = Signal(TranslationOutput)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    started_signal = Signal()
    stopped_signal = Signal()
    audio_level = Signal(float)  # Audio level 0.0-1.0
    
    def __init__(self, config: PipelineConfig, device_index: Optional[int] = None, use_parallel: bool = True):
        super().__init__()
        self.config = config
        self.device_index = device_index
        self.use_parallel = use_parallel
        
        # Use parallel pipeline for better performance (2 ASR workers + overlap)
        if use_parallel:
            try:
                from src.core.pipeline.orchestrator_parallel import ParallelTranslationPipeline
                self.pipeline = ParallelTranslationPipeline(config)
                logger.info("Using ParallelTranslationPipeline (2 ASR workers, overlap enabled)")
            except ImportError:
                logger.warning("Parallel pipeline not available, falling back to sequential")
                self.pipeline = TranslationPipeline(config)
                self.use_parallel = False
        else:
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
                audio_source=self.config.audio_source,
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
            from src.audio import AudioManager, AudioConfig
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
        """Stop the pipeline gracefully but quickly."""
        logger.info("Stopping translation worker...")
        self._is_running = False
        
        # Stop pipeline with shorter timeout (don't process final segment)
        if self.pipeline:
            try:
                self.pipeline.stop(timeout=2.0, process_final=False)
            except Exception as e:
                logger.warning(f"Error stopping pipeline: {e}")
        
        # Stop audio monitor if running
        if self._audio_manager:
            try:
                self._audio_manager.stop_capture()
            except Exception as e:
                logger.warning(f"Error stopping audio monitor: {e}")
        
        # Wait for thread to finish with timeout
        if not self.wait(3000):  # Wait up to 3 seconds
            logger.warning("Worker thread did not stop gracefully, forcing termination")
            self.terminate()  # Force terminate if still running
            self.wait(1000)
        
        logger.info("Translation worker stopped")


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


@dataclass
class TranslationEntry:
    """Store a translation entry for export."""
    entry_id: int
    timestamp_str: str
    timestamp_seconds: float
    delta_from_previous: float  # Time delta from previous entry in seconds
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    processing_time_ms: float
    confidence: float
    is_partial: bool
    unix_timestamp: float  # Unix timestamp for precise timing


class TranslationDisplay(QTextEdit):
    """
    Enhanced text display for translation output.
    
    Features:
    - Better formatting for long sentences
    - Visual separation between source and translation
    - Smart text truncation for very long content
    - Improved typography and readability
    - Export to text and subtitle formats
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self._entry_count = 0
        self._max_entries = 100  # Keep last 100 entries
        self._entries: List[TranslationEntry] = []  # Store entries for export
        self._session_start_time = time.time()  # For subtitle timing
        self._last_entry_time: Optional[float] = None  # For delta calculation
        self._show_timestamps = True  # Toggle for timestamp display
        
        # Improved styling with better typography
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        
        # Set default font for better Unicode support
        font = QFont("SF Pro Text", 14)
        font.setStyleHint(QFont.SansSerif)
        self.setFont(font)
    
    def _format_long_text(self, text: str, max_chars: int = 200) -> str:
        """
        Format long text with smart truncation.
        
        Args:
            text: Original text
            max_chars: Maximum characters before truncation
            
        Returns:
            Formatted HTML string
        """
        if len(text) <= max_chars:
            return self._escape_html(text)
        
        # For long text, show first part with indicator
        truncated = text[:max_chars]
        remaining = len(text) - max_chars
        
        # Try to break at sentence boundary
        sentence_end = max(
            truncated.rfind('. '), 
            truncated.rfind('! '),
            truncated.rfind('? '),
            truncated.rfind('。'),
            truncated.rfind('！'),
            truncated.rfind('？')
        )
        
        if sentence_end > max_chars * 0.6:  # If we can break at sentence
            display_text = truncated[:sentence_end + 1]
            remaining = len(text) - len(display_text)
        else:
            # Break at word boundary
            word_break = truncated.rfind(' ')
            if word_break > max_chars * 0.8:
                display_text = truncated[:word_break]
                remaining = len(text) - len(display_text)
            else:
                display_text = truncated
        
        return f'{self._escape_html(display_text)}<span style="color: #6e6e6e;">... ({remaining} more chars)</span>'
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))
    
    def _create_entry_html(self, entry_id: int, timestamp: str, 
                          delta_from_previous: float,
                          source_text: str, translated_text: str,
                          source_lang: str, target_lang: str,
                          processing_time_ms: float, confidence: float,
                          is_partial: bool = False) -> str:
        """Create HTML for a translation entry with delta time."""
        
        # Format texts
        source_formatted = self._format_long_text(source_text, max_chars=300)
        translation_formatted = self._format_long_text(translated_text, max_chars=300)
        
        # Word counts
        source_words = len(source_text.split())
        translation_words = len(translated_text.split())
        
        # Partial indicator
        partial_badge = '<span style="background-color: #d4a017; color: #000; padding: 1px 4px; border-radius: 3px; font-size: 9px; margin-left: 5px;">PARTIAL</span>' if is_partial else ''
        
        # Format delta time
        if delta_from_previous == 0.0:
            delta_str = "start"
        elif delta_from_previous >= 60:
            # Show minutes:seconds format for long deltas
            mins = int(delta_from_previous // 60)
            secs = int(delta_from_previous % 60)
            delta_str = f"+{mins}m{secs}s"
        else:
            delta_str = f"+{delta_from_previous:.2f}s"
        
        html = f'''
        <div id="entry_{entry_id}" style="margin-bottom: 12px; padding: 12px; background-color: #252526; border-radius: 6px; border-left: 3px solid #0e639c;">
            <!-- Header with timestamp, delta, and metadata -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #3c3c3c;">
                <span style="color: #858585; font-size: 11px; font-family: monospace;">
                    {timestamp} <span style="color: #5c5c5c;">|</span> <span style="color: #4ec9b0;">{delta_str}</span> {partial_badge}
                </span>
                <span style="color: #6e6e6e; font-size: 10px;">
                    {processing_time_ms:.0f}ms • {confidence:.0%} confidence
                </span>
            </div>
            
            <!-- Source Text Section -->
            <div style="margin-bottom: 10px;">
                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                    <span style="background-color: #4ec9b0; color: #1e1e1e; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; margin-right: 8px;">
                        {source_lang.upper()}
                    </span>
                    <span style="color: #6e6e6e; font-size: 10px;">
                        {source_words} words • {len(source_text)} chars
                    </span>
                </div>
                <div style="color: #d4d4d4; font-size: 14px; line-height: 1.6; padding: 6px 8px; background-color: #1e1e1e; border-radius: 4px; word-wrap: break-word;">
                    {source_formatted}
                </div>
            </div>
            
            <!-- Translation Section -->
            <div>
                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                    <span style="background-color: #ce9178; color: #1e1e1e; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; margin-right: 8px;">
                        {target_lang.upper()}
                    </span>
                    <span style="color: #6e6e6e; font-size: 10px;">
                        {translation_words} words • {len(translated_text)} chars
                    </span>
                </div>
                <div style="color: #dcdcaa; font-size: 14px; line-height: 1.6; padding: 6px 8px; background-color: #1e1e1e; border-radius: 4px; word-wrap: break-word; border-left: 2px solid #ce9178;">
                    {translation_formatted}
                </div>
            </div>
        </div>
        '''
        return html
    
    def add_translation(self, source_text: str, translated_text: str, 
                       source_lang: str, target_lang: str, 
                       processing_time_ms: float, confidence: float,
                       is_partial: bool = False):
        """
        Add a translation entry to the display.
        
        Args:
            source_text: Original recognized text
            translated_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            processing_time_ms: Processing time in milliseconds
            confidence: Confidence score (0-1)
            is_partial: Whether this is a partial segment from a longer sentence
        """
        unix_now = time.time()
        timestamp_str = time.strftime("%H:%M:%S")
        timestamp_seconds = unix_now - self._session_start_time
        
        # Calculate delta from previous entry
        if self._last_entry_time is None:
            delta_from_previous = 0.0
        else:
            delta_from_previous = unix_now - self._last_entry_time
        self._last_entry_time = unix_now
        
        self._entry_count += 1
        
        # Store entry for export
        entry = TranslationEntry(
            entry_id=self._entry_count,
            timestamp_str=timestamp_str,
            timestamp_seconds=timestamp_seconds,
            delta_from_previous=delta_from_previous,
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            processing_time_ms=processing_time_ms,
            confidence=confidence,
            is_partial=is_partial,
            unix_timestamp=unix_now
        )
        self._entries.append(entry)
        
        # Create the entry HTML
        html = self._create_entry_html(
            entry_id=self._entry_count,
            timestamp=timestamp_str,
            delta_from_previous=delta_from_previous,
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            processing_time_ms=processing_time_ms,
            confidence=confidence,
            is_partial=is_partial
        )
        
        self.append(html)
        
        # Limit entries to prevent memory issues
        self._cleanup_old_entries()
        
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _cleanup_old_entries(self):
        """Remove old entries if we exceed the maximum."""
        if len(self._entries) > self._max_entries:
            # Remove oldest entries
            remove_count = len(self._entries) - self._max_entries
            self._entries = self._entries[remove_count:]
    
    def clear_display(self):
        """Clear the display."""
        self.clear()
        self._entries.clear()
        self._entry_count = 0
        self._session_start_time = time.time()
        self._last_entry_time = None
    
    # ==================== Export Methods ====================
    
    def export_as_txt(self, filepath: str, include_source: bool = True, 
                     include_translation: bool = True) -> bool:
        """
        Export translations as plain text file.
        
        Args:
            filepath: Path to save the file
            include_source: Include source text
            include_translation: Include translated text
            
        Returns:
            True if successful
        """
        try:
            lines = []
            lines.append(f"Translation Session - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("=" * 60)
            lines.append("")
            
            for entry in self._entries:
                # Format delta time for display
                if entry.delta_from_previous == 0.0:
                    delta_str = "start"
                elif entry.delta_from_previous >= 60:
                    mins = int(entry.delta_from_previous // 60)
                    secs = int(entry.delta_from_previous % 60)
                    delta_str = f"+{mins}m{secs}s"
                else:
                    delta_str = f"+{entry.delta_from_previous:.2f}s"
                
                lines.append(f"[{entry.timestamp_str}] [{delta_str}] Entry #{entry.entry_id}")
                
                if include_source:
                    lines.append(f"Source ({entry.source_lang}): {entry.source_text}")
                
                if include_translation:
                    lines.append(f"Translation ({entry.target_lang}): {entry.translated_text}")
                
                if entry.is_partial:
                    lines.append("[PARTIAL SEGMENT]")
                
                lines.append("")
            
            lines.append("=" * 60)
            lines.append(f"Total entries: {len(self._entries)}")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            logger.info(f"Exported {len(self._entries)} entries to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export TXT: {e}")
            return False
    
    def export_as_srt(self, filepath: str, use_translation: bool = True) -> bool:
        """
        Export translations as SRT subtitle file.
        
        Args:
            filepath: Path to save the file
            use_translation: If True, export translations; otherwise export source text
            
        Returns:
            True if successful
        """
        try:
            srt_lines = []
            
            for i, entry in enumerate(self._entries, 1):
                # Calculate timestamps
                start_time = entry.timestamp_seconds
                # Estimate end time based on text length (avg 3 chars/sec)
                text = entry.translated_text if use_translation else entry.source_text
                duration = max(2.0, len(text) / 8.0)  # Min 2 seconds
                end_time = start_time + duration
                
                # Format timestamps (HH:MM:SS,mmm)
                start_str = self._format_srt_time(start_time)
                end_str = self._format_srt_time(end_time)
                
                srt_lines.append(str(i))
                srt_lines.append(f"{start_str} --> {end_str}")
                srt_lines.append(text)
                srt_lines.append("")  # Empty line between entries
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
            
            logger.info(f"Exported {len(self._entries)} subtitles to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export SRT: {e}")
            return False
    
    def export_as_vtt(self, filepath: str, use_translation: bool = True) -> bool:
        """
        Export translations as WebVTT subtitle file.
        
        Args:
            filepath: Path to save the file
            use_translation: If True, export translations; otherwise export source text
            
        Returns:
            True if successful
        """
        try:
            vtt_lines = ["WEBVTT", ""]
            
            for entry in self._entries:
                # Calculate timestamps
                start_time = entry.timestamp_seconds
                text = entry.translated_text if use_translation else entry.source_text
                duration = max(2.0, len(text) / 8.0)
                end_time = start_time + duration
                
                # Format timestamps (HH:MM:SS.mmm)
                start_str = self._format_vtt_time(start_time)
                end_str = self._format_vtt_time(end_time)
                
                vtt_lines.append(f"{start_str} --> {end_str}")
                vtt_lines.append(text)
                vtt_lines.append("")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(vtt_lines))
            
            logger.info(f"Exported {len(self._entries)} subtitles to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export VTT: {e}")
            return False
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for WebVTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def get_entries_count(self) -> int:
        """Get the number of stored entries."""
        return len(self._entries)
    
    def has_entries(self) -> bool:
        """Check if there are entries to export."""
        return len(self._entries) > 0


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
            from src.core.asr.faster_whisper import FasterWhisperASR
            from src.core.translation.marian import MarianTranslator
            from src.core.pipeline.batch import BatchVideoTranslator
            
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
        
        # Meeting Mode (Phase 4)
        self.meeting_window: Optional['MeetingWindow'] = None
        self._meeting_mode_enabled = MEETING_MODE_AVAILABLE
        
        # Phase 5 utilities
        self._phase5_enabled = PHASE5_AVAILABLE
        self._debug_logger: Optional['DebugLogger'] = None
        self._perf_monitor: Optional['PerformanceMonitor'] = None
        self._update_checker: Optional['UpdateChecker'] = None
        
        self.setWindowTitle(self.config.window_title)
        self.setMinimumSize(self.config.window_width, self.config.window_height)
        
        self._setup_ui()
        self._setup_styles()
        self._setup_menus()
        
        # Initialize Phase 5 features
        if self._phase5_enabled:
            self._init_phase5()
    
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
        settings_layout = QVBoxLayout(settings_group)  # Changed to vertical for better visibility
        
        # Row 1: Language and Model
        row1_layout = QHBoxLayout()
        
        # Source language
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["Auto-detect", "Chinese (zh)", "English (en)", 
                                         "Japanese (ja)", "French (fr)"])
        self.source_lang_combo.setCurrentIndex(2)  # Default: English
        row1_layout.addWidget(QLabel("Source:"))
        row1_layout.addWidget(self.source_lang_combo)
        
        # Arrow
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        row1_layout.addWidget(arrow_label)
        
        # Target language
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["Chinese (zh)", "English (en)", 
                                         "Japanese (ja)", "French (fr)"])
        self.target_lang_combo.setCurrentIndex(0)  # Default: Chinese
        row1_layout.addWidget(QLabel("Target:"))
        row1_layout.addWidget(self.target_lang_combo)
        
        row1_layout.addSpacing(20)
        
        # ASR Model
        self.model_combo = QComboBox()
        self.model_combo.addItems(["base (balanced)", "tiny (fast)", "small (accurate)"])
        row1_layout.addWidget(QLabel("ASR Model:"))
        row1_layout.addWidget(self.model_combo)
        
        row1_layout.addStretch()
        settings_layout.addLayout(row1_layout)
        
        # Row 2: Audio Source (prominent placement)
        row2_layout = QHBoxLayout()
        
        # Audio Source with icon and better visibility
        audio_source_label = QLabel("🎙️ Audio Input Source:")
        audio_source_label.setStyleSheet("font-weight: bold; color: #4ec9b0;")
        row2_layout.addWidget(audio_source_label)
        
        self.audio_source_combo = QComboBox()
        self.audio_source_combo.addItems(["🎤 Microphone", "🔊 System Audio"])
        self.audio_source_combo.setMinimumWidth(200)  # Make it wider
        self.audio_source_combo.setToolTip(
            "Microphone: Capture from your microphone\n"
            "System Audio: Capture computer's output audio (requires BlackHole on macOS)\n\n"
            "To use System Audio:\n"
            "1. Install BlackHole: brew install blackhole-2ch\n"
            "2. Set BlackHole as output in System Settings → Sound"
        )
        row2_layout.addWidget(self.audio_source_combo)
        
        # Microphone device selector (shown only when Microphone is selected)
        self.mic_device_combo = QComboBox()
        self.mic_device_combo.setMinimumWidth(250)
        self.mic_device_combo.setToolTip("Select specific microphone device")
        row2_layout.addWidget(self.mic_device_combo)
        
        # Add status indicator for system audio
        self.audio_source_status = QLabel("")
        self.audio_source_status.setStyleSheet("color: #858585; font-size: 11px;")
        row2_layout.addWidget(self.audio_source_status)
        
        # Populate microphone devices
        self._populate_mic_devices()
        
        row2_layout.addStretch()
        settings_layout.addLayout(row2_layout)
        
        # Update status when selection changes
        self.audio_source_combo.currentIndexChanged.connect(self._on_audio_source_changed)
        
        # Initial update
        self._on_audio_source_changed(0)
        
        layout.addWidget(settings_group)
        
        # === Display Area ===
        display_group = QGroupBox("Live Translation")
        display_layout = QVBoxLayout(display_group)
        
        self.translation_display = TranslationDisplay()
        display_layout.addWidget(self.translation_display)
        
        layout.addWidget(display_group, stretch=1)
        
        # === Audio Level Panel ===
        level_group = QGroupBox("Audio Input Level")
        level_layout = QHBoxLayout(level_group)
        
        self.audio_level_indicator = AudioLevelIndicator()
        level_layout.addWidget(self.audio_level_indicator)
        
        self.level_status_label = QLabel("No audio")
        self.level_status_label.setStyleSheet("color: #858585; font-size: 11px;")
        level_layout.addWidget(self.level_status_label)
        
        layout.addWidget(level_group)
        
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
        
        # Meeting Mode button (Phase 4)
        if self._meeting_mode_enabled:
            self.meeting_button = QPushButton("📋 Meeting Mode")
            self.meeting_button.setMinimumHeight(40)
            self.meeting_button.setStyleSheet("""
                QPushButton {
                    background-color: #6C5DD3;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7D6EE4;
                }
                QPushButton:pressed {
                    background-color: #5B4CC2;
                }
            """)
            self.meeting_button.clicked.connect(self._on_open_meeting_mode)
            control_layout.addWidget(self.meeting_button)
        
        # Settings button (Phase 5) - accessible way to open settings menu
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setMinimumHeight(40)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """)
        self.settings_btn.clicked.connect(self._on_open_settings_menu)
        control_layout.addWidget(self.settings_btn)
        
        control_layout.addStretch()
        
        # Export buttons
        self.export_txt_btn = QPushButton("📄 Export TXT")
        self.export_txt_btn.setMinimumHeight(40)
        self.export_txt_btn.clicked.connect(self._on_export_txt)
        self.export_txt_btn.setToolTip("Export as plain text file")
        control_layout.addWidget(self.export_txt_btn)
        
        self.export_srt_btn = QPushButton("🎬 Export SRT")
        self.export_srt_btn.setMinimumHeight(40)
        self.export_srt_btn.clicked.connect(self._on_export_srt)
        self.export_srt_btn.setToolTip("Export as SRT subtitle file")
        control_layout.addWidget(self.export_srt_btn)
        
        # Status indicator
        self.status_label = QLabel("⏹ Stopped")
        self.status_label.setStyleSheet("color: #858585; font-weight: bold;")
        control_layout.addWidget(self.status_label)
        
        layout.addWidget(control_group)
        
        # === Status Bar ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.latency_label = QLabel("Latency: --")
        self.segments_label = QLabel("Segments: 0")
        self.status_bar.addWidget(self.latency_label)
        self.status_bar.addWidget(self.segments_label)
        
        # Phase 5: Performance labels
        self.cpu_label = QLabel("")
        self.memory_label = QLabel("")
        self.status_bar.addWidget(self.cpu_label)
        self.status_bar.addWidget(self.memory_label)
        
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
    
    def _setup_menus(self):
        """Setup menu bar (Phase 5)."""
        from PySide6.QtWidgets import QMenuBar, QMenu
        
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Export actions
        export_txt_action = file_menu.addAction("📄 Export as TXT...")
        export_txt_action.triggered.connect(self._on_export_txt)
        
        export_srt_action = file_menu.addAction("🎬 Export as SRT...")
        export_srt_action.triggered.connect(self._on_export_srt)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Tools menu (Phase 5)
        tools_menu = menubar.addMenu("Tools")
        
        # Meeting Mode
        if self._meeting_mode_enabled:
            meeting_action = tools_menu.addAction("📋 Meeting Mode")
            meeting_action.triggered.connect(self._on_open_meeting_mode)
            tools_menu.addSeparator()
        
        # Debug logging toggle (Phase 5)
        if self._phase5_enabled:
            self.debug_log_action = tools_menu.addAction("🐛 Debug Logging")
            self.debug_log_action.setCheckable(True)
            self.debug_log_action.setChecked(False)
            self.debug_log_action.triggered.connect(self._on_toggle_debug_logging)
            
            self.privacy_mode_action = tools_menu.addAction("🔒 Privacy Mode")
            self.privacy_mode_action.setCheckable(True)
            self.privacy_mode_action.setChecked(False)
            self.privacy_mode_action.triggered.connect(self._on_toggle_privacy_mode)
            
            tools_menu.addSeparator()
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        # Audio Test (NEW)
        audio_test_action = settings_menu.addAction("🎤 Audio Test...")
        audio_test_action.triggered.connect(self._on_audio_test)
        
        settings_menu.addSeparator()
        
        # Performance monitoring (Phase 5)
        if self._phase5_enabled:
            self.perf_monitor_action = settings_menu.addAction("📊 Performance Monitor")
            self.perf_monitor_action.setCheckable(True)
            self.perf_monitor_action.setChecked(True)
            self.perf_monitor_action.triggered.connect(self._on_toggle_perf_monitor)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        # Check for updates (Phase 5)
        if self._phase5_enabled:
            check_update_action = help_menu.addAction("🔄 Check for Updates")
            check_update_action.triggered.connect(self._on_check_updates)
            help_menu.addSeparator()
        
        about_action = help_menu.addAction("About VoiceTranslate Pro")
        about_action.triggered.connect(self._on_about)
    
    def _init_phase5(self):
        """Initialize Phase 5 utilities."""
        # Initialize debug logger
        try:
            self._debug_logger = get_debug_logger(app_version="2.0.0")
            logger.info("Debug logger initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize debug logger: {e}")
        
        # Initialize performance monitor
        try:
            self._perf_monitor = PerformanceMonitor(
                cpu_threshold=80.0,
                memory_threshold=85.0
            )
            self._perf_monitor.metrics_updated.connect(self._on_perf_metrics)
            self._perf_monitor.start_monitoring(interval_ms=2000)
            logger.info("Performance monitor started")
        except Exception as e:
            logger.warning(f"Failed to initialize performance monitor: {e}")
        
        # Initialize update checker
        try:
            self._update_checker = UpdateChecker(current_version="2.0.0")
            self._update_checker.update_available.connect(self._on_update_available)
            self._update_checker.check_failed.connect(self._on_update_check_failed)
        except Exception as e:
            logger.warning(f"Failed to initialize update checker: {e}")
    
    def _on_toggle_debug_logging(self, checked: bool):
        """Toggle debug logging."""
        if not self._debug_logger:
            return
        
        if checked:
            success = self._debug_logger.enable(level="DEBUG")
            if success:
                self.status_bar.showMessage("Debug logging enabled", 3000)
            else:
                QMessageBox.warning(self, "Debug Logging", "Failed to enable debug logging")
                self.debug_log_action.setChecked(False)
        else:
            self._debug_logger.disable()
            self.status_bar.showMessage("Debug logging disabled", 3000)
    
    def _on_toggle_privacy_mode(self, checked: bool):
        """Toggle privacy mode."""
        if self._debug_logger:
            self._debug_logger.set_privacy_mode(checked)
            status = "enabled" if checked else "disabled"
            self.status_bar.showMessage(f"Privacy mode {status}", 3000)
    
    def _on_toggle_perf_monitor(self, checked: bool):
        """Toggle performance monitor."""
        if not self._perf_monitor:
            return
        
        if checked:
            self._perf_monitor.start_monitoring()
            self.status_bar.showMessage("Performance monitor enabled", 3000)
        else:
            self._perf_monitor.stop_monitoring()
            # Clear performance labels
            self.cpu_label.setText("")
            self.memory_label.setText("")
            self.status_bar.showMessage("Performance monitor disabled", 3000)
    
    def _on_perf_metrics(self, metrics):
        """Handle performance metrics update."""
        if hasattr(self, 'cpu_label'):
            self.cpu_label.setText(f"CPU: {metrics.cpu_percent:.0f}%")
            self.memory_label.setText(f"RAM: {metrics.memory_percent:.0f}%")
    
    def _on_check_updates(self):
        """Check for updates."""
        if not self._update_checker:
            QMessageBox.information(self, "Update Check", "Update checker not available")
            return
        
        self.status_bar.showMessage("Checking for updates...")
        self._update_checker.check_for_updates()
    
    def _on_update_available(self, update_info):
        """Handle update available."""
        reply = QMessageBox.question(
            self,
            "Update Available",
            f"Version {update_info.version} is available!\n\n"
            f"Release Notes:\n{update_info.release_notes}\n\n"
            f"Would you like to download it?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._update_checker.open_download_page(update_info.download_url)
    
    def _on_update_check_failed(self, message: str):
        """Handle update check failure."""
        self.status_bar.showMessage(f"Update check: {message}", 5000)
    
    def _on_audio_test(self):
        """Open audio test dialog."""
        try:
            from src.gui.audio_test_dialog import AudioTestDialog
            dialog = AudioTestDialog(self)
            dialog.exec()
        except ImportError as e:
            logger.warning(f"Audio test dialog import failed: {e}")
            QMessageBox.information(
                self,
                "Audio Test",
                "Audio test dialog not available.\n\n"
                "Use CLI instead:\n"
                "python tests/manual/test_microphone.py"
            )
    
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About VoiceTranslate Pro",
            "<h2>VoiceTranslate Pro v2.0.0</h2>"
            "<p>Real-time voice translation application</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>🎤 Real-time speech recognition</li>"
            "<li>🔄 Instant translation</li>"
            "<li>📋 Meeting mode with speaker identification</li>"
            "<li>🎬 Video translation</li>"
            "</ul>"
            "<p>Built with PySide6, faster-whisper, and MarianMT</p>"
        )
    
    def _on_open_settings_menu(self):
        """Open settings popup menu."""
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        # Meeting Mode
        if self._meeting_mode_enabled:
            meeting_action = menu.addAction("📋 Open Meeting Mode")
            meeting_action.triggered.connect(self._on_open_meeting_mode)
            menu.addSeparator()
        
        # Audio Test (NEW)
        audio_test_action = menu.addAction("🎤 Audio Test...")
        audio_test_action.triggered.connect(self._on_audio_test)
        menu.addSeparator()
        
        # Phase 5 features
        if self._phase5_enabled:
            debug_action = menu.addAction("🐛 Debug Logging")
            debug_action.setCheckable(True)
            debug_action.setChecked(self._debug_logger is not None and hasattr(self, 'debug_log_action') and self.debug_log_action.isChecked())
            debug_action.triggered.connect(self._on_toggle_debug_logging)
            
            privacy_action = menu.addAction("🔒 Privacy Mode")
            privacy_action.setCheckable(True)
            privacy_action.setChecked(self._debug_logger is not None and hasattr(self, 'privacy_mode_action') and self.privacy_mode_action.isChecked())
            privacy_action.triggered.connect(self._on_toggle_privacy_mode)
            
            perf_action = menu.addAction("📊 Performance Monitor")
            perf_action.setCheckable(True)
            perf_action.setChecked(self._perf_monitor is not None)
            perf_action.triggered.connect(self._on_toggle_perf_monitor)
            
            menu.addSeparator()
            
            update_action = menu.addAction("🔄 Check for Updates")
            update_action.triggered.connect(self._on_check_updates)
        else:
            # Show placeholder if Phase 5 not available
            unavailable = menu.addAction("⚠️ Advanced features require: loguru, packaging")
            unavailable.setEnabled(False)
        
        menu.addSeparator()
        
        about_action = menu.addAction("ℹ️ About")
        about_action.triggered.connect(self._on_about)
        
        # Show menu at button position
        menu.exec(self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomLeft()))
    
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
        
        # Get audio source selection
        audio_source = (
            AudioSource.SYSTEM_AUDIO 
            if self.audio_source_combo.currentIndex() == 1 
            else AudioSource.MICROPHONE
        )
        
        # Check system audio availability
        if audio_source == AudioSource.SYSTEM_AUDIO:
            import platform
            from src.audio import AudioManager, AudioConfig
            
            manager = AudioManager(AudioConfig())
            sys_devices = manager.list_devices(AudioSource.SYSTEM_AUDIO)
            
            if not sys_devices:
                system = platform.system()
                msg = "System audio capture is not available.\n\n"
                if system == "Darwin":
                    msg += "Please install BlackHole:\n  brew install blackhole-2ch\n\n"
                    msg += "Then set BlackHole as your output device in System Settings."
                elif system == "Windows":
                    msg += "Please enable Stereo Mix or install VB-Cable."
                else:
                    msg += "System audio capture is not supported on this platform."
                
                QMessageBox.warning(self, "System Audio Not Available", msg)
                return
        
        # Get microphone device index if using microphone
        mic_device_index = None
        if audio_source == AudioSource.MICROPHONE:
            mic_device_index = self.mic_device_combo.currentData()
            if mic_device_index is None or mic_device_index < 0:
                mic_device_index = None  # Use default
        
        # Create pipeline config
        config = PipelineConfig(
            asr_model_size=model_size,
            asr_language=source_code,
            source_language=source_code or "auto",
            target_language=target_code,
            enable_translation=True,
            audio_device_index=mic_device_index,
            audio_source=audio_source
        )
        
        # Create and start worker
        self.worker = TranslationWorker(config, device_index=mic_device_index)
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
        """Stop the translation pipeline gracefully."""
        self.status_label.setText("⏹ Stopping...")
        self.status_bar.showMessage("Stopping translation...")
        
        # Stop update timer first
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # Stop worker thread
        if self.worker:
            try:
                if self.worker.isRunning():
                    self.worker.stop()
                self.worker = None
            except Exception as e:
                logger.warning(f"Error stopping worker: {e}")
                self.worker = None
        
        # Ensure UI is reset
        QTimer.singleShot(100, self._on_worker_stopped)
        
        logger.info("Translation stopped by user")
    
    @Slot(TranslationOutput)
    def _on_output(self, output: TranslationOutput):
        """Handle translation output."""
        self.translation_display.add_translation(
            source_text=output.source_text,
            translated_text=output.translated_text or "(no translation)",
            source_lang=output.source_language,
            target_lang=output.target_language,
            processing_time_ms=output.processing_time_ms,
            confidence=output.confidence,
            is_partial=output.is_partial
        )
        self.segments_count += 1
        self.latency_label.setText(f"Latency: {output.processing_time_ms:.0f}ms")
        
        # Also send to Meeting Mode if active (Phase 4)
        if self.meeting_window and self.meeting_window.is_recording():
            # Only add non-partial results to meeting minutes
            if not output.is_partial:
                self.meeting_window.add_transcription(
                    text=output.source_text,
                    translated_text=output.translated_text,
                    confidence=output.confidence,
                    duration=output.processing_time_ms / 1000.0,  # Convert ms to seconds
                )
    
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
    
    def _on_open_meeting_mode(self):
        """Open Meeting Mode window (Phase 4)."""
        if not self._meeting_mode_enabled:
            QMessageBox.information(self, "Meeting Mode", "Meeting Mode is not available.")
            return
        
        if not self.meeting_window:
            self.meeting_window = MeetingWindow()
            self.meeting_window.setAttribute(Qt.WA_DeleteOnClose, False)
        
        self.meeting_window.show()
        self.meeting_window.raise_()
        self.meeting_window.activateWindow()
        
        logger.info("Meeting Mode window opened")
    
    def _populate_mic_devices(self):
        """Populate microphone device dropdown."""
        self.mic_device_combo.clear()
        
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            default_idx = sd.default.device[0]  # Default input device
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:  # Input device
                    name = device['name']
                    is_default = "⭐ " if i == default_idx else ""
                    self.mic_device_combo.addItem(f"{is_default}[{i}] {name}", i)
            
            # Select default device
            default_combo_idx = self.mic_device_combo.findData(default_idx)
            if default_combo_idx >= 0:
                self.mic_device_combo.setCurrentIndex(default_combo_idx)
                
        except Exception as e:
            logger.error(f"Failed to populate mic devices: {e}")
            self.mic_device_combo.addItem("⚠️ Error loading devices", -1)
    
    def _on_audio_source_changed(self, index: int):
        """Handle audio source selection change."""
        if index == 1:  # System Audio selected
            # Hide mic device selector
            self.mic_device_combo.setVisible(False)
            
            # Check if system audio is available
            from src.audio import AudioManager, AudioConfig, AudioSource
            
            try:
                manager = AudioManager(AudioConfig())
                sys_devices = manager.list_devices(AudioSource.SYSTEM_AUDIO)
                
                if sys_devices:
                    device_names = [d['name'] for d in sys_devices]
                    self.audio_source_status.setText(
                        f"✅ Available: {', '.join(device_names[:2])}"
                    )
                    self.audio_source_status.setStyleSheet("color: #4ec9b0; font-size: 11px;")
                else:
                    self.audio_source_status.setText(
                        "⚠️ BlackHole not detected - install with: brew install blackhole-2ch"
                    )
                    self.audio_source_status.setStyleSheet("color: #ce9178; font-size: 11px;")
            except Exception as e:
                self.audio_source_status.setText(f"❌ Error checking: {str(e)[:50]}")
                self.audio_source_status.setStyleSheet("color: #c75450; font-size: 11px;")
        else:
            # Microphone selected - show device selector
            self.mic_device_combo.setVisible(True)
            self._populate_mic_devices()  # Refresh device list
            
            # Show selected device info
            current_idx = self.mic_device_combo.currentData()
            current_text = self.mic_device_combo.currentText()
            self.audio_source_status.setText(f"✅ {current_text[:40]}...")
            self.audio_source_status.setStyleSheet("color: #4ec9b0; font-size: 11px;")
    
    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable controls during translation."""
        self.source_lang_combo.setEnabled(enabled)
        self.target_lang_combo.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.audio_source_combo.setEnabled(enabled)
        self.mic_device_combo.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
    
    @Slot()
    def _on_clear(self):
        """Clear the display."""
        self.translation_display.clear_display()
        self.segments_count = 0
        self.segments_label.setText("Segments: 0")
        self.latency_label.setText("Latency: --")
    
    @Slot()
    def _on_export_txt(self):
        """Export translations as TXT file."""
        if not self.translation_display.has_entries():
            QMessageBox.information(self, "Export", "No translations to export yet.")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export as Text File",
            f"translations_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filepath:
            success = self.translation_display.export_as_txt(
                filepath,
                include_source=True,
                include_translation=True
            )
            if success:
                QMessageBox.information(
                    self, 
                    "Export Successful", 
                    f"Exported {self.translation_display.get_entries_count()} entries to:\n{filepath}"
                )
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export translations.")
    
    @Slot()
    def _on_export_srt(self):
        """Export translations as SRT subtitle file."""
        if not self.translation_display.has_entries():
            QMessageBox.information(self, "Export", "No translations to export yet.")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export as SRT Subtitles",
            f"translations_{time.strftime('%Y%m%d_%H%M%S')}.srt",
            "Subtitle Files (*.srt);;All Files (*)"
        )
        
        if filepath:
            # Ask whether to export source or translation
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Export Options")
            msg_box.setText("Which text do you want to export?")
            msg_box.addButton("Translations", QMessageBox.AcceptRole)
            msg_box.addButton("Source Text", QMessageBox.RejectRole)
            msg_box.addButton("Cancel", QMessageBox.DestructiveRole)
            
            result = msg_box.exec()
            
            if result == 2:  # Cancel
                return
            
            use_translation = (result == 0)  # Translations button
            
            success = self.translation_display.export_as_srt(filepath, use_translation)
            if success:
                text_type = "translations" if use_translation else "source text"
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Exported {self.translation_display.get_entries_count()} {text_type} to:\n{filepath}"
                )
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export subtitles.")
    
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
