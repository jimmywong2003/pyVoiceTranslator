"""
Meeting Export Module
=====================

Export meeting sessions to various formats.
"""

from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

from .entry import MeetingSession, MeetingEntry


class ExportFormat(Enum):
    """Supported export formats"""
    MARKDOWN = auto()
    TEXT = auto()
    JSON = auto()
    CSV = auto()


class MeetingExporter:
    """
    Export meeting sessions to various formats.
    
    Usage:
        exporter = MeetingExporter()
        exporter.export(session, "meeting.md", ExportFormat.MARKDOWN)
    """
    
    def __init__(self):
        self._handlers = {
            ExportFormat.MARKDOWN: self._export_markdown,
            ExportFormat.TEXT: self._export_text,
            ExportFormat.JSON: self._export_json,
            ExportFormat.CSV: self._export_csv,
        }
    
    def export(
        self,
        session: MeetingSession,
        filepath: Path,
        format: ExportFormat,
        include_translation: bool = True,
    ) -> bool:
        """
        Export meeting session to file.
        
        Args:
            session: Meeting session to export
            filepath: Output file path
            format: Export format
            include_translation: Include translations if available
            
        Returns:
            True if successful
        """
        try:
            handler = self._handlers.get(format)
            if not handler:
                raise ValueError(f"Unsupported format: {format}")
            
            content = handler(session, include_translation)
            
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def _export_markdown(self, session: MeetingSession, include_translation: bool) -> str:
        """Export to Markdown format"""
        lines = [
            f"# {session.title}",
            "",
            f"**Date:** {session.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Entries:** {len(session.entries)}",
            "",
            "## Participants",
            "",
        ]
        
        for speaker in session.speakers.values():
            lines.append(f"- {speaker.display_name}")
        
        lines.extend(["", "## Transcript", ""])
        
        for entry in session.entries:
            time_str = entry.timestamp.strftime("%H:%M:%S")
            lines.append(f"### [{time_str}] {entry.speaker.display_name}")
            lines.append("")
            lines.append(entry.original_text)
            
            if include_translation and entry.translated_text:
                lines.append("")
                lines.append(f"> Translation: {entry.translated_text}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_text(self, session: MeetingSession, include_translation: bool) -> str:
        """Export to plain text format"""
        lines = [
            f"MEETING: {session.title}",
            f"Date: {session.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"{'=' * 60}",
            "",
            "PARTICIPANTS:",
        ]
        
        for speaker in session.speakers.values():
            lines.append(f"  - {speaker.display_name}")
        
        lines.extend(["", f"{'=' * 60}", "TRANSCRIPT:", ""])
        
        for entry in session.entries:
            time_str = entry.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{time_str}] {entry.speaker.display_name}:")
            lines.append(f"  {entry.original_text}")
            
            if include_translation and entry.translated_text:
                lines.append(f"  → {entry.translated_text}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_json(self, session: MeetingSession, include_translation: bool) -> str:
        """Export to JSON format"""
        data = {
            "session_id": session.session_id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "stats": session.get_speaker_stats(),
            "speakers": {
                sid: {
                    "speaker_id": s.speaker_id,
                    "name": s.name,
                    "color": s.color,
                }
                for sid, s in session.speakers.items()
            },
            "entries": [
                entry.to_dict() for entry in session.entries
            ],
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _export_csv(self, session: MeetingSession, include_translation: bool) -> str:
        """Export to CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        headers = ["Entry ID", "Timestamp", "Speaker", "Original Text"]
        if include_translation:
            headers.append("Translated Text")
        headers.extend(["Confidence", "Duration"])
        writer.writerow(headers)
        
        # Data rows
        for entry in session.entries:
            row = [
                entry.entry_id,
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                entry.speaker.display_name,
                entry.original_text,
            ]
            if include_translation:
                row.append(entry.translated_text or "")
            row.extend([
                f"{entry.confidence:.2f}",
                f"{entry.duration:.2f}",
            ])
            writer.writerow(row)
        
        return output.getvalue()
    
    def get_supported_formats(self) -> Dict[str, str]:
        """Get supported formats with descriptions"""
        return {
            "markdown": "Markdown (.md) - Formatted document",
            "text": "Text (.txt) - Plain text",
            "json": "JSON (.json) - Structured data",
            "csv": "CSV (.csv) - Spreadsheet format",
        }
