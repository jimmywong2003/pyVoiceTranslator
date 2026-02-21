"""
Meeting Mode GUI Module
=======================

GUI components for meeting transcription and minutes generation.

Components:
    MeetingDisplay: Scrollable transcript display with speaker labels
    SpeakerBadge: Color-coded speaker identifier
    MeetingToolbar: Controls for meeting mode
    MeetingWindow: Standalone meeting mode window

Usage:
    from src.gui.meeting import MeetingDisplay
    display = MeetingDisplay()
    display.add_entry(meeting_entry)
"""

from .display import MeetingDisplay, SpeakerBadge
from .window import MeetingWindow
from .toolbar import MeetingToolbar

__all__ = [
    "MeetingDisplay",
    "SpeakerBadge",
    "MeetingWindow",
    "MeetingToolbar",
]
