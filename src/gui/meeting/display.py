"""
Meeting Display Widget
======================

Scrollable transcript display with speaker labels and timestamps.
Designed for meeting minutes generation.
"""

from typing import List, Optional, Dict
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QScrollArea, QFrame, QSizePolicy, QApplication, QPushButton,
    QLineEdit, QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QTextCursor, QAction

from src.core.meeting.entry import MeetingEntry, Speaker, EntryType


# Speaker color palette (distinct colors for different speakers)
SPEAKER_COLORS = [
    "#6C5DD3",  # Purple (default)
    "#00B8D9",  # Cyan
    "#36B37E",  # Green
    "#FFAB00",  # Orange
    "#FF5630",  # Red
    "#6554C0",  # Indigo
    "#00875A",  # Teal
    "#F59E0B",  # Amber
]


class SpeakerBadge(QLabel):
    """
    Color-coded speaker identifier badge.
    
    Shows speaker name with colored background.
    """
    
    def __init__(self, speaker: Speaker, parent=None):
        super().__init__(parent)
        self.speaker = speaker
        self.setText(speaker.display_name)
        self.setFixedHeight(24)
        self.setContentsMargins(8, 0, 8, 0)
        self.setAlignment(Qt.AlignCenter)
        
        # Apply styling
        self._apply_style()
    
    def _apply_style(self):
        """Apply color styling based on speaker"""
        color = self.speaker.color
        # Calculate contrasting text color
        bg_color = QColor(color)
        luminance = (0.299 * bg_color.red() + 
                    0.587 * bg_color.green() + 
                    0.114 * bg_color.blue()) / 255
        text_color = "#FFFFFF" if luminance < 0.5 else "#000000"
        
        self.setStyleSheet(f"""
            SpeakerBadge {{
                background-color: {color};
                color: {text_color};
                border-radius: 12px;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 12px;
            }}
        """)


class MeetingEntryWidget(QFrame):
    """
    Individual meeting entry widget.
    
    Displays a single transcript entry with:
    - Speaker badge
    - Timestamp
    - Original text
    - Translated text (if available)
    - Action item marking
    - Context menu for annotations
    
    Signals:
        mark_action_item: Emitted when entry marked as action item
        add_note: Emitted when user adds a note
    """
    
    mark_action_item = Signal(MeetingEntry, bool)
    add_note = Signal(MeetingEntry, str)
    
    def __init__(self, entry: MeetingEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the widget layout"""
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            MeetingEntryWidget {
                background-color: #252536;
                border: 1px solid #3A3A4A;
                border-radius: 8px;
                margin: 4px 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header row: Speaker + Timestamp
        header = QHBoxLayout()
        header.setSpacing(12)
        
        # Speaker badge
        self.speaker_badge = SpeakerBadge(self.entry.speaker)
        header.addWidget(self.speaker_badge)
        
        # Timestamp
        time_str = self.entry.timestamp.strftime("%H:%M:%S")
        self.time_label = QLabel(time_str)
        self.time_label.setStyleSheet("""
            color: #8B8B9E;
            font-size: 12px;
        """)
        header.addWidget(self.time_label)
        
        # Confidence indicator (optional)
        if self.entry.confidence > 0:
            conf_text = f"{self.entry.confidence * 100:.0f}%"
            conf_color = self._get_confidence_color(self.entry.confidence)
            self.conf_label = QLabel(conf_text)
            self.conf_label.setStyleSheet(f"""
                color: {conf_color};
                font-size: 11px;
                font-weight: 500;
            """)
            header.addWidget(self.conf_label)
        
        header.addStretch()
        
        # Action item button
        self.action_btn = QPushButton("⚡" if self.entry.entry_type == EntryType.ACTION_ITEM else "○")
        self.action_btn.setFixedSize(24, 24)
        self.action_btn.setToolTip("Mark as action item")
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3A3A4A;
                border-radius: 12px;
                color: #8B8B9E;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FFAB0022;
                border-color: #FFAB00;
                color: #FFAB00;
            }
            QPushButton:checked {
                background-color: #FFAB00;
                border-color: #FFAB00;
                color: #1E1E2E;
            }
        """)
        self.action_btn.setCheckable(True)
        self.action_btn.setChecked(self.entry.entry_type == EntryType.ACTION_ITEM)
        self.action_btn.clicked.connect(self._on_action_toggle)
        header.addWidget(self.action_btn)
        
        # Note button
        has_note = bool(self.entry.metadata.get('note'))
        self.note_btn = QPushButton("📝" if has_note else "🗊")
        self.note_btn.setFixedSize(24, 24)
        self.note_btn.setToolTip("Add note" if not has_note else "View/edit note")
        self.note_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3A3A4A;
                border-radius: 12px;
                color: #8B8B9E;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6C5DD322;
                border-color: #6C5DD3;
                color: #6C5DD3;
            }
        """)
        self.note_btn.clicked.connect(self._on_add_note)
        header.addWidget(self.note_btn)
        
        layout.addLayout(header)
        
        # Original text
        self.text_label = QLabel(self.entry.original_text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_label.setStyleSheet("""
            color: #E8E8ED;
            font-size: 14px;
            line-height: 1.5;
        """)
        layout.addWidget(self.text_label)
        
        # Translated text (if available)
        if self.entry.translated_text:
            self.translation_frame = QFrame()
            self.translation_frame.setStyleSheet("""
                QFrame {
                    background-color: #1E1E2E;
                    border-left: 3px solid #6C5DD3;
                    border-radius: 0px 4px 4px 0px;
                    padding: 8px;
                    margin-top: 4px;
                }
            """)
            trans_layout = QVBoxLayout(self.translation_frame)
            trans_layout.setContentsMargins(12, 8, 8, 8)
            
            trans_label = QLabel(self.entry.translated_text)
            trans_label.setWordWrap(True)
            trans_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            trans_label.setStyleSheet("""
                color: #A5A5B8;
                font-size: 13px;
                font-style: italic;
            """)
            trans_layout.addWidget(trans_label)
            
            layout.addWidget(self.translation_frame)
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color based on confidence level"""
        if confidence >= 0.9:
            return "#36B37E"  # Green
        elif confidence >= 0.7:
            return "#FFAB00"  # Orange
        else:
            return "#FF5630"  # Red
    
    def _on_action_toggle(self, checked: bool):
        """Handle action item toggle"""
        self.entry.entry_type = EntryType.ACTION_ITEM if checked else EntryType.SPEECH
        self.action_btn.setText("⚡" if checked else "○")
        self.mark_action_item.emit(self.entry, checked)
        
        # Visual feedback
        if checked:
            self.setStyleSheet("""
                MeetingEntryWidget {
                    background-color: #252536;
                    border: 2px solid #FFAB00;
                    border-radius: 8px;
                    margin: 4px 8px;
                    padding: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                MeetingEntryWidget {
                    background-color: #252536;
                    border: 1px solid #3A3A4A;
                    border-radius: 8px;
                    margin: 4px 8px;
                    padding: 12px;
                }
            """)
    
    def _on_add_note(self):
        """Handle add note button"""
        from PySide6.QtWidgets import QInputDialog
        
        current_note = self.entry.metadata.get('note', '')
        text, ok = QInputDialog.getMultiLineText(
            self, "Add Note", "Enter note for this entry:", current_note
        )
        
        if ok:
            self.entry.metadata['note'] = text
            self.note_btn.setText("📝" if text else "🗊")
            self.note_btn.setToolTip(f"Note: {text[:50]}..." if text else "Add note")
            self.add_note.emit(self.entry, text)


class MeetingDisplay(QScrollArea):
    """
    Scrollable meeting transcript display.
    
    Features:
    - Auto-scroll to latest entry
    - Speaker color coding
    - Timestamps
    - Translation display
    - Entry selection
    
    Signals:
        entry_selected: Emitted when user clicks an entry
        entry_count_changed: Emitted when entry count changes
    """
    
    entry_selected = Signal(MeetingEntry)
    entry_count_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[MeetingEntry] = []
        self._entry_widgets: List[MeetingEntryWidget] = []
        self._speaker_colors: Dict[str, str] = {}
        self._auto_scroll = True
        self._max_entries = 500  # Limit to prevent memory issues
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the display UI"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1E1E2E;
            }
            QScrollBar:vertical {
                background-color: #252536;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #6C5DD3;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7D6EE4;
            }
        """)
        
        # Container widget
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1E1E2E;")
        self.setWidget(self.container)
        
        # Layout
        self.layout = QVBoxLayout(self.container)
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.addStretch()
    
    def add_entry(self, entry: MeetingEntry) -> None:
        """
        Add a meeting entry to the display.
        
        Args:
            entry: MeetingEntry to add
        """
        # Assign speaker color if not already assigned
        if entry.speaker.speaker_id not in self._speaker_colors:
            color_index = len(self._speaker_colors) % len(SPEAKER_COLORS)
            self._speaker_colors[entry.speaker.speaker_id] = SPEAKER_COLORS[color_index]
            entry.speaker.color = self._speaker_colors[entry.speaker.speaker_id]
        
        # Add to list
        self._entries.append(entry)
        
        # Create widget
        widget = MeetingEntryWidget(entry)
        widget.mousePressEvent = lambda e, ent=entry: self.entry_selected.emit(ent)
        
        # Insert before the stretch
        self.layout.insertWidget(self.layout.count() - 1, widget)
        self._entry_widgets.append(widget)
        
        # Enforce max entries limit
        if len(self._entries) > self._max_entries:
            self._remove_oldest_entry()
        
        # Emit signal
        self.entry_count_changed.emit(len(self._entries))
        
        # Auto-scroll
        if self._auto_scroll:
            QTimer.singleShot(10, self._scroll_to_bottom)
    
    def _remove_oldest_entry(self):
        """Remove oldest entry to maintain max limit"""
        if self._entries and self._entry_widgets:
            self._entries.pop(0)
            old_widget = self._entry_widgets.pop(0)
            old_widget.deleteLater()
    
    def _scroll_to_bottom(self):
        """Scroll to the bottom of the display"""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear(self):
        """Clear all entries"""
        for widget in self._entry_widgets:
            widget.deleteLater()
        self._entry_widgets.clear()
        self._entries.clear()
        self._speaker_colors.clear()
        self.entry_count_changed.emit(0)
    
    def get_entries(self) -> List[MeetingEntry]:
        """Get all entries"""
        return self._entries.copy()
    
    def set_auto_scroll(self, enabled: bool):
        """Enable/disable auto-scroll"""
        self._auto_scroll = enabled
    
    def get_speaker_stats(self) -> Dict[str, dict]:
        """Get statistics for each speaker"""
        stats: Dict[str, dict] = {}
        for entry in self._entries:
            sid = entry.speaker.speaker_id
            if sid not in stats:
                stats[sid] = {
                    "name": entry.speaker.display_name,
                    "color": entry.speaker.color,
                    "count": 0,
                    "duration": 0.0,
                }
            stats[sid]["count"] += 1
            stats[sid]["duration"] += entry.duration
        return stats
    
    def search(self, query: str, case_sensitive: bool = False) -> List[int]:
        """
        Search for entries containing query text.
        
        Args:
            query: Search text
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            List of entry indices that match
        """
        if not query:
            return []
        
        matches = []
        query_cmp = query if case_sensitive else query.lower()
        
        for i, entry in enumerate(self._entries):
            text_to_search = entry.original_text
            if not case_sensitive:
                text_to_search = text_to_search.lower()
            
            if query_cmp in text_to_search:
                matches.append(i)
                continue
            
            # Also search in translated text if available
            if entry.translated_text:
                trans_text = entry.translated_text if case_sensitive else entry.translated_text.lower()
                if query_cmp in trans_text:
                    matches.append(i)
                    continue
            
            # Search in notes
            note = entry.metadata.get('note', '')
            if note:
                note_text = note if case_sensitive else note.lower()
                if query_cmp in note_text:
                    matches.append(i)
        
        return matches
    
    def highlight_entry(self, index: int):
        """Scroll to and highlight a specific entry"""
        if 0 <= index < len(self._entry_widgets):
            widget = self._entry_widgets[index]
            self.ensureWidgetVisible(widget)
            
            # Visual highlight effect
            original_style = widget.styleSheet()
            widget.setStyleSheet(original_style.replace(
                "border: 1px solid #3A3A4A;",
                "border: 2px solid #6C5DD3;"
            ))
            
            # Remove highlight after 2 seconds
            QTimer.singleShot(2000, lambda: widget.setStyleSheet(original_style))
    
    def get_action_items(self) -> List[MeetingEntry]:
        """Get all entries marked as action items"""
        return [e for e in self._entries if e.entry_type == EntryType.ACTION_ITEM]
    
    def get_entries_with_notes(self) -> List[MeetingEntry]:
        """Get all entries that have notes"""
        return [e for e in self._entries if e.metadata.get('note')]


def demo():
    """Demo the MeetingDisplay widget"""
    import sys
    from datetime import datetime
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    app = QApplication(sys.argv)
    
    # Create main window
    window = QWidget()
    window.setWindowTitle("Meeting Display Demo")
    window.resize(600, 800)
    window.setStyleSheet("background-color: #1E1E2E;")
    
    layout = QVBoxLayout(window)
    
    # Create display
    display = MeetingDisplay()
    layout.addWidget(display)
    
    # Add demo entries
    speakers = [
        Speaker("Speaker 1", "Alice"),
        Speaker("Speaker 2", "Bob"),
        Speaker("Speaker 3", "Carol"),
    ]
    
    demo_texts = [
        ("Hello everyone, welcome to today's meeting.", None),
        ("Thanks Alice. Let's start with the project update.", None),
        ("Sure, I'll share my screen.", None),
        ("The current progress is on track.", "現在の進捗は順調です。"),
        ("Great to hear that!", "それは良いニュースです！"),
    ]
    
    for i, (text, translation) in enumerate(demo_texts):
        entry = MeetingEntry(
            entry_id=i + 1,
            timestamp=datetime.now(),
            speaker=speakers[i % len(speakers)],
            original_text=text,
            translated_text=translation,
            confidence=0.85 + (i % 10) / 100,
            duration=2.5,
        )
        display.add_entry(entry)
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    demo()
