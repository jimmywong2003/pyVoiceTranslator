# Meeting Mode Integration Guide

## Overview

Phase 4 Week 1 implementation is complete. This guide explains how to integrate the new Meeting Mode with the existing VoiceTranslate Pro application.

## New Components

### 1. Core Data Models (`src/core/meeting/`)

```python
from src.core.meeting import MeetingEntry, Speaker, MeetingSession

# Create a meeting entry
entry = MeetingEntry(
    entry_id=1,
    timestamp=datetime.now(),
    speaker=Speaker("Speaker 1", "Alice"),
    original_text="Hello world",
    translated_text="こんにちは世界",
    confidence=0.85,
    duration=2.5,
)

# Format as meeting minutes
minutes = entry.to_minutes_format()
# Output: "[10:30:45] Alice: Hello world\n  → こんにちは世界"
```

### 2. GUI Components (`src/gui/meeting/`)

```python
from src.gui.meeting import MeetingWindow, MeetingDisplay

# Create standalone meeting window
meeting_window = MeetingWindow()
meeting_window.show()

# Add transcription entry
meeting_window.add_transcription(
    text="Let's start the meeting",
    translated_text="会議を始めましょう",
    confidence=0.90,
    duration=3.0,
)
```

### 3. Export Formats

Supported export formats:
- **Markdown** (`.md`) - Formatted document with headers
- **Text** (`.txt`) - Plain text meeting minutes
- **JSON** (`.json`) - Structured data with metadata
- **CSV** (`.csv`) - Spreadsheet format for analysis

```python
from src.core.meeting import MeetingExporter, ExportFormat

exporter = MeetingExporter()
exporter.export(session, Path("meeting.md"), ExportFormat.MARKDOWN)
```

## Integration Points

### Option A: Separate Window (Recommended)

Add a "Meeting Mode" button to the main GUI that opens `MeetingWindow`:

```python
# In src/gui/main.py
from src.gui.meeting import MeetingWindow

class MainWindow:
    def __init__(self):
        # ... existing init ...
        self.meeting_window = None
    
    def open_meeting_mode(self):
        """Open meeting mode in separate window"""
        if not self.meeting_window:
            self.meeting_window = MeetingWindow()
        self.meeting_window.show()
        self.meeting_window.raise_()
```

### Option B: Tabbed Interface

Add Meeting Mode as a tab in the main window:

```python
from PySide6.QtWidgets import QTabWidget
from src.gui.meeting import MeetingDisplay

# Create tab widget
tabs = QTabWidget()
tabs.addTab(translation_widget, "Translation")
tabs.addTab(meeting_display, "Meeting Mode")
```

### Pipeline Integration

Connect the existing ASR pipeline to Meeting Mode:

```python
class MeetingModeIntegration:
    """Bridge between ASR pipeline and Meeting GUI"""
    
    def __init__(self, meeting_window, pipeline):
        self.window = meeting_window
        self.pipeline = pipeline
        
        # Connect pipeline signals
        self.pipeline.transcription_ready.connect(self.on_transcription)
    
    def on_transcription(self, result):
        """Handle new transcription from pipeline"""
        if self.window.is_recording():
            self.window.add_transcription(
                text=result.text,
                translated_text=result.translation,
                confidence=result.confidence,
                duration=result.duration,
            )
```

## Speaker Diarization Integration

The Meeting Mode uses turn-based speaker assignment (V1):

```python
# In MeetingWindow._on_start()
self._create_speakers(self.toolbar.get_speaker_count())

# In add_transcription()
speaker = self._speakers[self._current_speaker_idx]
self._current_speaker_idx = (self._current_speaker_idx + 1) % len(self._speakers)
```

Future V2 can use actual speaker embeddings by overriding `add_transcription()`:

```python
def add_transcription_with_diarization(self, text, embedding, ...):
    # Find speaker by voice embedding
    speaker_id = self.diarization.identify_speaker(embedding)
    speaker = self._speakers[speaker_id]
    # ... rest of entry creation
```

## Testing

Run component tests:

```bash
python src/gui/meeting/test_meeting.py
```

Run interactive demo:

```bash
python src/gui/meeting/demo.py
```

## UI Styling

Meeting Mode uses the Custom QSS theme (Phase 4 approved):

- Background: `#1E1E2E`
- Cards: `#252536`
- Accent: `#6C5DD3`
- Text: `#E8E8ED`
- Secondary text: `#8B8B9E`

## Migration from Translation Mode

Existing `TranslationEntry` continues to work alongside `MeetingEntry`:

| Feature | Translation Mode | Meeting Mode |
|---------|-----------------|--------------|
| Entry type | `TranslationEntry` | `MeetingEntry` |
| Display | `TranslationDisplay` | `MeetingDisplay` |
| Speaker info | None | Required |
| Export | TXT, SRT | MD, TXT, JSON, CSV |

Both modes can coexist in the same application without conflicts.

## Next Steps (Week 2-3)

1. **Integration**: Connect MeetingWindow to main application
2. **Pipeline**: Wire ASR output to MeetingMode
3. **Speaker Names**: Allow editing speaker names during meeting
4. **Search**: Add transcript search functionality
5. **Annotations**: Allow marking action items and decisions
