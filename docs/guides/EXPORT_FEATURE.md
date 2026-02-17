# Export Feature Documentation

## Overview

The GUI now supports exporting translation results in multiple formats:
1. **Plain Text (TXT)** - Full transcript with metadata
2. **SRT Subtitles** - Standard subtitle format for video players
3. **VTT Subtitles** - WebVTT format for web video

---

## Features

### 1. Plain Text Export (.txt)

**Contents:**
- Session timestamp
- All translation entries with timestamps
- Source text and translations
- Word/character counts
- Partial segment indicators

**Format:**
```
Translation Session - 2026-02-17 14:30:00
============================================================

[12:34:56] Entry #1
Source (en): Hello world, this is a test of the translation system.
Translation (zh): 你好世界，这是翻译系统的测试。

[12:35:02] Entry #2
Source (en): How are you today?
Translation (zh): 你今天好吗？

============================================================
Total entries: 2
```

### 2. SRT Subtitle Export (.srt)

**Features:**
- Standard SRT format compatible with all video players
- Automatic timestamp calculation
- Duration based on text length (min 2 seconds)
- Choice of source text or translation

**Format:**
```srt
1
00:00:05,000 --> 00:00:08,500
Hello world, this is a test.

2
00:00:08,500 --> 00:00:12,000
How are you today?
```

### 3. WebVTT Export (.vtt)

**Features:**
- WebVTT format for HTML5 video
- Similar timing to SRT
- Better styling support for web

**Format:**
```vtt
WEBVTT

00:00:05.000 --> 00:00:08.500
Hello world, this is a test.

00:00:08.500 --> 00:00:12.000
How are you today?
```

---

## GUI Integration

### New Buttons

| Button | Function |
|--------|----------|
| **📄 Export TXT** | Export all translations as plain text file |
| **🎬 Export SRT** | Export as SRT subtitle file |

### Usage

1. **Run translation** - Start the translation pipeline
2. **Accumulate results** - Let translations build up in the display
3. **Click Export** - Choose TXT or SRT export
4. **Select location** - Choose where to save the file
5. **For SRT** - Choose whether to export source text or translations

---

## Technical Details

### Data Storage

Each translation entry is stored with:
```python
@dataclass
class TranslationEntry:
    entry_id: int              # Sequential entry number
    timestamp_str: str         # Display time (HH:MM:SS)
    timestamp_seconds: float   # Seconds since session start
    source_text: str          # Original ASR text
    translated_text: str      # Translated text
    source_lang: str          # Source language code
    target_lang: str          # Target language code
    processing_time_ms: float # Processing duration
    confidence: float         # ASR confidence
    is_partial: bool          # Whether segment was split
```

### Timing Calculation

Subtitle timing is calculated as:
```python
# Base time is when speech was detected
tart_time = entry.timestamp_seconds

# Duration based on text length (avg reading speed)
# Assumes ~8 characters per second
duration = max(2.0, len(text) / 8.0)

end_time = start_time + duration
```

This ensures:
- Minimum 2 seconds per subtitle
- Longer text gets more time
- Natural reading pace

### File Naming

Default filenames include timestamp:
```
translations_20260217_143000.txt
translations_20260217_143000.srt
```

---

## Code Structure

### TranslationDisplay Class

```python
class TranslationDisplay(QTextEdit):
    def export_as_txt(filepath, include_source, include_translation) -> bool
    def export_as_srt(filepath, use_translation) -> bool
    def export_as_vtt(filepath, use_translation) -> bool
    def has_entries() -> bool
    def get_entries_count() -> int
```

### Export Handlers

```python
def _on_export_txt(self):
    """Handle TXT export button click"""
    # Check if entries exist
    # Show save dialog
    # Call export_as_txt
    # Show success/error message

def _on_export_srt(self):
    """Handle SRT export button click"""
    # Check if entries exist
    # Show save dialog
    # Ask source vs translation
    # Call export_as_srt
    # Show success/error message
```

---

## Example Workflows

### Workflow 1: Meeting Transcription

1. Set audio source to "System Audio"
2. Start translation during video call
3. Let it run for the entire meeting
4. Click "📄 Export TXT"
5. Save as `meeting_2026_02_17.txt`
6. Review full transcript with timestamps

### Workflow 2: Video Subtitling

1. Play video with system audio
2. Start translation with "🔊 System Audio"
3. Let it process the entire video
4. Click "🎬 Export SRT"
5. Choose "Translations" when prompted
6. Save as `video_subtitles.srt`
7. Load SRT into video player

### Workflow 3: Bilingual Document

1. Record audio or use microphone
2. Speak naturally for several minutes
3. Click "📄 Export TXT"
4. Get both source and translation
5. Use for bilingual document creation

---

## Future Enhancements

### Planned Features

1. **Auto-export**
   - Automatically save after each segment
   - Real-time file updates

2. **Custom Templates**
   - User-defined export formats
   - Variable substitution ({{timestamp}}, {{text}}, etc.)

3. **Batch Export**
   - Export multiple sessions
   - Merge multiple translation files

4. **Format Options**
   - CSV export for spreadsheet analysis
   - JSON export for API integration
   - Word document export

5. **Cloud Sync**
   - Direct upload to Google Drive
   - Dropbox integration
   - Cloud storage backup

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No translations to export" | Run translation first, accumulate some results |
| Garbled text in SRT | Ensure UTF-8 encoding is used (default) |
| Wrong timing in subtitles | Timing is relative to session start, not video |
| Missing partial segments | All segments are exported, partial flag is noted |

### Encoding

All exports use **UTF-8** encoding to support:
- Chinese characters
- Emoji
- Special punctuation
- Multiple languages

---

## API Reference

### Export Methods

```python
# Export as plain text
success = translation_display.export_as_txt(
    filepath="output.txt",
    include_source=True,
    include_translation=True
)

# Export as SRT subtitles
success = translation_display.export_as_srt(
    filepath="output.srt",
    use_translation=True  # False for source text
)

# Export as WebVTT
success = translation_display.export_as_vtt(
    filepath="output.vtt",
    use_translation=True
)

# Check if entries exist
has_data = translation_display.has_entries()

# Get entry count
count = translation_display.get_entries_count()
```

---

## Integration with Video Players

### VLC Media Player

1. Play your video
2. Subtitle → Add Subtitle File
3. Select the exported `.srt` file

### MPV

```bash
mpv video.mp4 --sub-file=translations.srt
```

### Web Player (HTML5)

```html
<video controls>
  <source src="video.mp4" type="video/mp4">
  <track kind="subtitles" src="translations.vtt" 
         srclang="zh" label="Chinese" default>
</video>
```

---

## Summary

The export feature provides:
- ✅ **TXT Export** - Full transcripts with metadata
- ✅ **SRT Export** - Standard subtitles for video
- ✅ **VTT Export** - Web-ready subtitle format
- ✅ **Timestamps** - Accurate timing information
- ✅ **Bilingual Support** - Export source, translation, or both
- ✅ **Easy GUI Access** - Two-click export process
