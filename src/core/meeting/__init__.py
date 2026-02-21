"""
Meeting Mode Core Module
========================

Data models and utilities for meeting transcription and minutes generation.

Classes:
    MeetingEntry: Single transcript entry with speaker info
    MeetingSession: Container for all meeting entries
    Speaker: Speaker information and statistics
"""

from .entry import MeetingEntry, Speaker, MeetingSession
from .export import MeetingExporter, ExportFormat

__all__ = [
    "MeetingEntry",
    "Speaker", 
    "MeetingSession",
    "MeetingExporter",
    "ExportFormat",
]
