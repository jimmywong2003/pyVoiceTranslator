"""
Meeting Mode Window
===================

Standalone window for meeting transcription mode.
Provides a dedicated interface separate from translation mode.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSplitter, QMessageBox, QApplication,
    QScrollArea, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QCloseEvent

from src.core.meeting.entry import MeetingEntry, MeetingSession, Speaker
from src.core.meeting.export import MeetingExporter, ExportFormat
from .display import MeetingDisplay
from .toolbar import MeetingToolbar


class MeetingWindow(QMainWindow):
    """
    Standalone meeting mode window.
    
    Features:
    - Real-time transcript display
    - Speaker identification
    - Meeting title editing
    - Export to multiple formats
    - Statistics display
    
    Signals:
        meeting_started: Emitted when recording starts
        meeting_ended: Emitted when recording stops
        entry_added: Emitted when new entry added
    """
    
    meeting_started = Signal()
    meeting_ended = Signal()
    entry_added = Signal(MeetingEntry)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Meeting Mode - VoiceTranslate Pro")
        self.resize(900, 700)
        
        # Session state
        self._session: Optional[MeetingSession] = None
        self._is_recording = False
        self._entry_counter = 0
        self._speakers: List[Speaker] = []
        self._current_speaker_idx = 0
        
        # Components
        self._exporter = MeetingExporter()
        
        self._setup_ui()
        self._create_default_session()
    
    def _setup_ui(self):
        """Setup the window UI"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E2E;
            }
            QWidget {
                background-color: #1E1E2E;
            }
            QLabel {
                color: #E8E8ED;
            }
            QLineEdit {
                background-color: #252536;
                color: #E8E8ED;
                border: 1px solid #3A3A4A;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #6C5DD3;
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        self.toolbar = MeetingToolbar()
        self.toolbar.start_meeting.connect(self._on_start)
        self.toolbar.pause_meeting.connect(self._on_pause)
        self.toolbar.stop_meeting.connect(self._on_stop)
        self.toolbar.export_requested.connect(self._on_export)
        self.toolbar.speaker_count_changed.connect(self._on_speaker_count_changed)
        layout.addWidget(self.toolbar)
        
        # Header with title
        header = QWidget()
        header.setStyleSheet("background-color: #252536; padding: 12px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 12)
        
        title_label = QLabel("Meeting Title:")
        title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        header_layout.addWidget(title_label)
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter meeting title...")
        self.title_edit.setText("Untitled Meeting")
        header_layout.addWidget(self.title_edit, 1)
        
        # Stats label
        self.stats_label = QLabel("Entries: 0 | Duration: 00:00:00")
        self.stats_label.setStyleSheet("color: #8B8B9E; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        layout.addWidget(header)
        
        # Speaker names panel (editable)
        self.speaker_panel = QWidget()
        self.speaker_panel.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                border-bottom: 1px solid #3A3A4A;
            }
        """)
        self.speaker_layout = QHBoxLayout(self.speaker_panel)
        self.speaker_layout.setSpacing(8)
        self.speaker_layout.setContentsMargins(12, 8, 12, 8)
        self._speaker_name_edits: List[QLineEdit] = []
        layout.addWidget(self.speaker_panel)
        
        # Search bar
        self.search_panel = QWidget()
        self.search_panel.setStyleSheet("""
            QWidget {
                background-color: #252536;
                border-bottom: 1px solid #3A3A4A;
            }
        """)
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setSpacing(8)
        search_layout.setContentsMargins(12, 8, 12, 8)
        
        search_icon = QLabel("🔍")
        search_layout.addWidget(search_icon)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search transcript...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E2E;
                border: 1px solid #3A3A4A;
                border-radius: 4px;
                padding: 6px 12px;
                color: #E8E8ED;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6C5DD3;
            }
        """)
        self.search_edit.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_edit, 1)
        
        self.search_prev_btn = QPushButton("◀")
        self.search_prev_btn.setFixedSize(28, 28)
        self.search_prev_btn.setToolTip("Previous match")
        self.search_prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A4A;
                border: none;
                border-radius: 4px;
                color: #8B8B9E;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6C5DD3;
                color: white;
            }
        """)
        self.search_prev_btn.clicked.connect(self._on_search_prev)
        search_layout.addWidget(self.search_prev_btn)
        
        self.search_next_btn = QPushButton("▶")
        self.search_next_btn.setFixedSize(28, 28)
        self.search_next_btn.setToolTip("Next match")
        self.search_next_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A4A;
                border: none;
                border-radius: 4px;
                color: #8B8B9E;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6C5DD3;
                color: white;
            }
        """)
        self.search_next_btn.clicked.connect(self._on_search_next)
        search_layout.addWidget(self.search_next_btn)
        
        self.search_results_label = QLabel("")
        self.search_results_label.setStyleSheet("color: #8B8B9E; font-size: 12px;")
        search_layout.addWidget(self.search_results_label)
        
        search_layout.addStretch()
        
        # Quick filters
        self.action_items_btn = QPushButton("⚡ Action Items")
        self.action_items_btn.setCheckable(True)
        self.action_items_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3A3A4A;
                border-radius: 4px;
                padding: 4px 12px;
                color: #8B8B9E;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #FFAB0022;
                border-color: #FFAB00;
                color: #FFAB00;
            }
        """)
        self.action_items_btn.clicked.connect(self._on_toggle_action_items_filter)
        search_layout.addWidget(self.action_items_btn)
        
        self.notes_btn = QPushButton("📝 With Notes")
        self.notes_btn.setCheckable(True)
        self.notes_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3A3A4A;
                border-radius: 4px;
                padding: 4px 12px;
                color: #8B8B9E;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #6C5DD322;
                border-color: #6C5DD3;
                color: #6C5DD3;
            }
        """)
        self.notes_btn.clicked.connect(self._on_toggle_notes_filter)
        search_layout.addWidget(self.notes_btn)
        
        layout.addWidget(self.search_panel)
        
        # Search state
        self._search_matches: List[int] = []
        self._current_match_idx = -1
        
        # Meeting display
        self.display = MeetingDisplay()
        self.display.entry_count_changed.connect(self._update_stats)
        layout.addWidget(self.display, 1)
        
        # Status bar
        self.status_label = QLabel("Ready - Click Start to begin recording")
        self.status_label.setStyleSheet("""
            padding: 8px 12px;
            color: #8B8B9E;
            font-size: 12px;
            border-top: 1px solid #3A3A4A;
        """)
        layout.addWidget(self.status_label)
    
    def _create_default_session(self):
        """Create a default meeting session"""
        self._session = MeetingSession(
            session_id=str(uuid.uuid4())[:8],
            title="Untitled Meeting",
            created_at=datetime.now(),
        )
        self._create_speakers(4)  # Default 4 speakers
    
    def _create_speakers(self, count: int):
        """Create speaker objects and UI fields"""
        # Preserve existing names if possible
        existing_names = {}
        for s in self._speakers:
            existing_names[s.speaker_id] = s.name
        
        self._speakers = []
        for i in range(count):
            speaker_id = f"Speaker {i+1}"
            # Use existing name if available, otherwise default
            name = existing_names.get(speaker_id, speaker_id)
            self._speakers.append(Speaker(speaker_id, name))
        
        self._current_speaker_idx = 0
        self._update_speaker_panel()
    
    def _update_speaker_panel(self):
        """Update speaker name edit fields"""
        # Clear existing
        while self.speaker_layout.count():
            item = self.speaker_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._speaker_name_edits.clear()
        
        # Add label
        label = QLabel("Speakers:")
        label.setStyleSheet("color: #8B8B9E; font-size: 12px; font-weight: 600;")
        self.speaker_layout.addWidget(label)
        
        # Add edit field for each speaker
        for i, speaker in enumerate(self._speakers):
            # Speaker label with color indicator
            container = QFrame()
            container.setStyleSheet(f"""
                QFrame {{
                    background-color: {speaker.color}22;
                    border: 1px solid {speaker.color}44;
                    border-radius: 6px;
                    padding: 4px;
                }}
            """)
            container_layout = QHBoxLayout(container)
            container_layout.setSpacing(4)
            container_layout.setContentsMargins(8, 4, 8, 4)
            
            # Color dot
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {speaker.color}; font-size: 10px;")
            container_layout.addWidget(dot)
            
            # Name edit
            edit = QLineEdit()
            edit.setText(speaker.name)
            edit.setPlaceholderText(f"Speaker {i+1}")
            edit.setMaximumWidth(120)
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: transparent;
                    border: none;
                    color: #E8E8ED;
                    font-size: 12px;
                    padding: 2px 4px;
                }}
                QLineEdit:focus {{
                    background-color: #252536;
                    border: 1px solid {speaker.color};
                    border-radius: 4px;
                }}
            """)
            # Update speaker name on edit
            edit.editingFinished.connect(lambda idx=i, e=edit: self._on_speaker_name_changed(idx, e.text()))
            self._speaker_name_edits.append(edit)
            container_layout.addWidget(edit)
            
            self.speaker_layout.addWidget(container)
        
        self.speaker_layout.addStretch()
    
    def _on_speaker_name_changed(self, index: int, new_name: str):
        """Handle speaker name change"""
        if 0 <= index < len(self._speakers):
            old_name = self._speakers[index].name
            self._speakers[index].name = new_name.strip() or self._speakers[index].speaker_id
            
            # Update session speakers dict
            speaker_id = self._speakers[index].speaker_id
            if speaker_id in self._session.speakers:
                self._session.speakers[speaker_id].name = self._speakers[index].name
    
    def _on_search(self):
        """Handle search"""
        query = self.search_edit.text().strip()
        if not query:
            self._search_matches = []
            self._current_match_idx = -1
            self.search_results_label.setText("")
            return
        
        self._search_matches = self.display.search(query, case_sensitive=False)
        
        if self._search_matches:
            self._current_match_idx = 0
            self._update_search_results()
            self.display.highlight_entry(self._search_matches[0])
        else:
            self.search_results_label.setText("No matches")
            self._current_match_idx = -1
    
    def _on_search_prev(self):
        """Go to previous search match"""
        if not self._search_matches:
            return
        
        self._current_match_idx = (self._current_match_idx - 1) % len(self._search_matches)
        self._update_search_results()
        self.display.highlight_entry(self._search_matches[self._current_match_idx])
    
    def _on_search_next(self):
        """Go to next search match"""
        if not self._search_matches:
            return
        
        self._current_match_idx = (self._current_match_idx + 1) % len(self._search_matches)
        self._update_search_results()
        self.display.highlight_entry(self._search_matches[self._current_match_idx])
    
    def _update_search_results(self):
        """Update search results label"""
        if self._search_matches and self._current_match_idx >= 0:
            self.search_results_label.setText(
                f"{self._current_match_idx + 1} / {len(self._search_matches)}"
            )
        else:
            self.search_results_label.setText("")
    
    def _on_toggle_action_items_filter(self, checked: bool):
        """Toggle showing only action items"""
        # This would filter the display - simplified implementation
        if checked:
            action_items = self.display.get_action_items()
            self.status_label.setText(f"Showing {len(action_items)} action items")
        else:
            self.status_label.setText("Showing all entries")
    
    def _on_toggle_notes_filter(self, checked: bool):
        """Toggle showing only entries with notes"""
        if checked:
            entries_with_notes = self.display.get_entries_with_notes()
            self.status_label.setText(f"Showing {len(entries_with_notes)} entries with notes")
        else:
            self.status_label.setText("Showing all entries")
    
    def _on_start(self):
        """Handle meeting start"""
        self._is_recording = True
        self._entry_counter = 0
        
        # Update session title
        self._session.title = self.title_edit.text() or "Untitled Meeting"
        
        self.status_label.setText("● Recording... - Speak naturally, speakers will be assigned automatically")
        self.status_label.setStyleSheet("""
            padding: 8px 12px;
            color: #36B37E;
            font-size: 12px;
            border-top: 1px solid #3A3A4A;
        """)
        
        self.meeting_started.emit()
    
    def _on_pause(self):
        """Handle meeting pause/resume"""
        if self.toolbar._is_paused:
            self.status_label.setText("⏸ Paused - Click Resume to continue")
            self.status_label.setStyleSheet("""
                padding: 8px 12px;
                color: #FFAB00;
                font-size: 12px;
                border-top: 1px solid #3A3A4A;
            """)
        else:
            self.status_label.setText("● Recording...")
            self.status_label.setStyleSheet("""
                padding: 8px 12px;
                color: #36B37E;
                font-size: 12px;
                border-top: 1px solid #3A3A4A;
            """)
    
    def _on_stop(self):
        """Handle meeting stop"""
        self._is_recording = False
        
        self.status_label.setText(f"✓ Meeting ended - {len(self._session.entries)} entries recorded")
        self.status_label.setStyleSheet("""
            padding: 8px 12px;
            color: #6C5DD3;
            font-size: 12px;
            border-top: 1px solid #3A3A4A;
        """)
        
        self.meeting_ended.emit()
        
        # Auto-prompt for export if we have entries
        if self._session.entries:
            reply = QMessageBox.question(
                self,
                "Export Meeting",
                f"Meeting saved with {len(self._session.entries)} entries.\n\nExport now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._prompt_export()
    
    def _on_export(self, filepath: str, format_idx: int):
        """Handle export request"""
        if not self._session or not self._session.entries:
            QMessageBox.information(self, "Export", "No meeting data to export.")
            return
        
        path = Path(filepath)
        format_map = {
            0: ExportFormat.MARKDOWN,
            1: ExportFormat.TEXT,
            2: ExportFormat.JSON,
            3: ExportFormat.CSV,
        }
        export_format = format_map.get(format_idx, ExportFormat.MARKDOWN)
        
        success = self._exporter.export(self._session, path, export_format)
        
        if success:
            QMessageBox.information(self, "Export Complete", f"Meeting exported to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export meeting. Please try again.")
    
    def _prompt_export(self):
        """Prompt user for export location"""
        default_name = f"{self._session.title.replace(' ', '_')}.md"
        filepath, _ = QMessageBox.NoButton, None  # Placeholder for actual dialog
        
        # Use the toolbar's export mechanism
        self.toolbar.export_btn.click()
    
    def _on_speaker_count_changed(self, count: int):
        """Handle speaker count change"""
        self._create_speakers(count)
    
    def _update_stats(self, count: int):
        """Update statistics display"""
        duration = sum(e.duration for e in self._session.entries)
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        self.stats_label.setText(
            f"Entries: {count} | Duration: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )
    
    def add_transcription(
        self,
        text: str,
        translated_text: Optional[str] = None,
        confidence: float = 0.0,
        duration: float = 0.0,
    ) -> MeetingEntry:
        """
        Add a transcription entry to the meeting.
        
        Args:
            text: Original transcribed text
            translated_text: Translated text (optional)
            confidence: ASR confidence score
            duration: Audio duration in seconds
            
        Returns:
            Created MeetingEntry
        """
        if not self._is_recording:
            return None
        
        self._entry_counter += 1
        
        # Get current speaker (turn-based rotation)
        speaker = self._speakers[self._current_speaker_idx]
        self._current_speaker_idx = (self._current_speaker_idx + 1) % len(self._speakers)
        
        entry = MeetingEntry(
            entry_id=self._entry_counter,
            timestamp=datetime.now(),
            speaker=speaker,
            original_text=text,
            translated_text=translated_text,
            confidence=confidence,
            duration=duration,
        )
        
        # Add to session and display
        self._session.add_entry(entry)
        self.display.add_entry(entry)
        
        self.entry_added.emit(entry)
        return entry
    
    def get_session(self) -> Optional[MeetingSession]:
        """Get current meeting session"""
        return self._session
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._is_recording
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close"""
        if self._is_recording and self._session.entries:
            reply = QMessageBox.question(
                self,
                "Close Meeting",
                "Meeting is still recording. Close anyway?\n\nUnsaved data will be lost.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        event.accept()


def demo():
    """Demo the MeetingWindow"""
    import sys
    import random
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    app = QApplication(sys.argv)
    
    # Apply dark theme
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1E1E2E;
        }
    """)
    
    window = MeetingWindow()
    window.show()
    
    # Simulate adding entries after start
    def simulate_entries():
        if window.is_recording():
            texts = [
                "Let's start with the project overview.",
                "The timeline looks good to me.",
                "We need to address the budget concerns.",
                "I'll prepare the documentation.",
                "Can we schedule a follow-up next week?",
            ]
            text = random.choice(texts)
            window.add_transcription(
                text=text,
                translated_text=None,
                confidence=random.uniform(0.75, 0.95),
                duration=random.uniform(2.0, 5.0),
            )
    
    # Connect start to simulation
    timer = QTimer()
    timer.timeout.connect(simulate_entries)
    
    def on_start():
        timer.start(3000)  # Add entry every 3 seconds
    
    def on_stop():
        timer.stop()
    
    window.meeting_started.connect(on_start)
    window.meeting_ended.connect(on_stop)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    demo()
