"""
Meeting Data Models
===================

Defines data structures for meeting transcription entries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Dict, Any
import time


class EntryType(Enum):
    """Type of meeting entry"""
    SPEECH = auto()      # Regular speech
    ACTION_ITEM = auto()  # Action item detected
    DECISION = auto()    # Decision made
    NOTE = auto()        # Manual note


@dataclass
class Speaker:
    """
    Speaker information for meeting transcripts.
    
    Attributes:
        speaker_id: Unique identifier (e.g., "Speaker 1")
        name: Optional display name
        color: UI color for this speaker
        entry_count: Number of entries by this speaker
        total_duration: Total speaking time in seconds
    """
    speaker_id: str
    name: Optional[str] = None
    color: str = "#6C5DD3"  # Default accent color
    entry_count: int = 0
    total_duration: float = 0.0
    
    def __post_init__(self):
        if self.name is None:
            self.name = self.speaker_id
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return self.name or self.speaker_id


@dataclass
class MeetingEntry:
    """
    Single entry in meeting transcript.
    
    Coexists with TranslationEntry - used in Meeting Mode while
    TranslationEntry is used in Translation Mode.
    
    Attributes:
        entry_id: Sequential entry number
        timestamp: When entry was created
        speaker: Speaker information
        original_text: Transcribed text
        translated_text: Translated text (if translation enabled)
        confidence: ASR confidence (0.0 - 1.0)
        entry_type: Type of entry
        duration: Audio duration in seconds
        metadata: Additional metadata
    """
    entry_id: int
    timestamp: datetime
    speaker: Speaker
    original_text: str
    translated_text: Optional[str] = None
    confidence: float = 0.0
    entry_type: EntryType = EntryType.SPEECH
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal timing
    unix_timestamp: float = field(default_factory=time.time)
    delta_from_previous: float = 0.0  # Time from previous entry
    
    def to_minutes_format(self) -> str:
        """
        Format entry as meeting minutes.
        
        Returns:
            Formatted string like "[10:30:45] Speaker 1: Hello world"
        """
        time_str = self.timestamp.strftime("%H:%M:%S")
        speaker_name = self.speaker.display_name
        
        if self.translated_text:
            return (
                f"[{time_str}] {speaker_name}:\n"
                f"  {self.original_text}\n"
                f"  → {self.translated_text}"
            )
        return f"[{time_str}] {speaker_name}: {self.original_text}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "unix_timestamp": self.unix_timestamp,
            "speaker": {
                "speaker_id": self.speaker.speaker_id,
                "name": self.speaker.name,
                "color": self.speaker.color,
            },
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "confidence": self.confidence,
            "entry_type": self.entry_type.name,
            "duration": self.duration,
            "delta_from_previous": self.delta_from_previous,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingEntry":
        """Create MeetingEntry from dictionary"""
        speaker_data = data.get("speaker", {})
        speaker = Speaker(
            speaker_id=speaker_data.get("speaker_id", "Unknown"),
            name=speaker_data.get("name"),
            color=speaker_data.get("color", "#6C5DD3"),
        )
        
        return cls(
            entry_id=data["entry_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            speaker=speaker,
            original_text=data["original_text"],
            translated_text=data.get("translated_text"),
            confidence=data.get("confidence", 0.0),
            entry_type=EntryType[data.get("entry_type", "SPEECH")],
            duration=data.get("duration", 0.0),
            metadata=data.get("metadata", {}),
            unix_timestamp=data.get("unix_timestamp", 0),
            delta_from_previous=data.get("delta_from_previous", 0.0),
        )


@dataclass
class MeetingSession:
    """
    Container for a complete meeting session.
    
    Attributes:
        session_id: Unique session identifier
        title: Meeting title
        created_at: Session start time
        entries: List of meeting entries
        speakers: Dictionary of speakers
        settings: Session settings
    """
    session_id: str
    title: str
    created_at: datetime
    entries: List[MeetingEntry] = field(default_factory=list)
    speakers: Dict[str, Speaker] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def add_entry(self, entry: MeetingEntry) -> None:
        """Add entry and update speaker statistics"""
        self.entries.append(entry)
        
        # Update speaker stats
        speaker_id = entry.speaker.speaker_id
        if speaker_id not in self.speakers:
            self.speakers[speaker_id] = entry.speaker
        
        self.speakers[speaker_id].entry_count += 1
        self.speakers[speaker_id].total_duration += entry.duration
    
    def get_speaker_stats(self) -> Dict[str, Any]:
        """Get statistics for all speakers"""
        total_duration = sum(e.duration for e in self.entries)
        
        return {
            "total_entries": len(self.entries),
            "total_duration": total_duration,
            "speakers": {
                sid: {
                    "name": s.display_name,
                    "entries": s.entry_count,
                    "speaking_time": s.total_duration,
                    "percentage": (s.total_duration / total_duration * 100) 
                                 if total_duration > 0 else 0,
                }
                for sid, s in self.speakers.items()
            }
        }
    
    def export_to_markdown(self) -> str:
        """Export entire session to Markdown format"""
        lines = [
            f"# {self.title}",
            f"",
            f"**Date:** {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Duration:** {self._format_duration()}",
            f"**Entries:** {len(self.entries)}",
            f"",
            "## Participants",
            "",
        ]
        
        for speaker in self.speakers.values():
            lines.append(f"- {speaker.display_name}")
        
        lines.extend(["", "## Transcript", ""])
        
        for entry in self.entries:
            lines.append(entry.to_minutes_format())
            lines.append("")
        
        return "\n".join(lines)
    
    def export_to_text(self) -> str:
        """Export to plain text format"""
        lines = [
            f"MEETING: {self.title}",
            f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"{'=' * 50}",
            "",
        ]
        
        for entry in self.entries:
            time_str = entry.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{time_str}] {entry.speaker.display_name}:")
            lines.append(f"  {entry.original_text}")
            if entry.translated_text:
                lines.append(f"  [{entry.translated_text}]")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_duration(self) -> str:
        """Format total duration as HH:MM:SS"""
        total_seconds = sum(e.duration for e in self.entries)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
