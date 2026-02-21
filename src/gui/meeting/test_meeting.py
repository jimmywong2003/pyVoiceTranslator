"""
Meeting Mode Component Tests
============================

Unit tests for meeting mode functionality.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add project root to path (handle running from any directory)
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.meeting.entry import MeetingEntry, MeetingSession, Speaker, EntryType
from src.core.meeting.export import MeetingExporter, ExportFormat


class TestMeetingEntry(unittest.TestCase):
    """Test MeetingEntry data model"""
    
    def test_entry_creation(self):
        """Test creating a meeting entry"""
        speaker = Speaker("Speaker 1", "Alice")
        entry = MeetingEntry(
            entry_id=1,
            timestamp=datetime.now(),
            speaker=speaker,
            original_text="Hello world",
            translated_text="こんにちは世界",
            confidence=0.85,
            duration=2.5,
        )
        
        self.assertEqual(entry.entry_id, 1)
        self.assertEqual(entry.original_text, "Hello world")
        self.assertEqual(entry.translated_text, "こんにちは世界")
        self.assertEqual(entry.confidence, 0.85)
    
    def test_minutes_format(self):
        """Test formatting as meeting minutes"""
        speaker = Speaker("Speaker 1", "Alice")
        entry = MeetingEntry(
            entry_id=1,
            timestamp=datetime(2026, 2, 21, 10, 30, 0),
            speaker=speaker,
            original_text="Hello world",
            translated_text="こんにちは世界",
            confidence=0.85,
            duration=2.5,
        )
        
        formatted = entry.to_minutes_format()
        self.assertIn("[10:30:00]", formatted)
        self.assertIn("Alice", formatted)
        self.assertIn("Hello world", formatted)
        self.assertIn("こんにちは世界", formatted)
    
    def test_dict_serialization(self):
        """Test serialization to/from dict"""
        speaker = Speaker("Speaker 1", "Alice", "#6C5DD3")
        entry = MeetingEntry(
            entry_id=1,
            timestamp=datetime.now(),
            speaker=speaker,
            original_text="Hello world",
            confidence=0.85,
            duration=2.5,
        )
        
        data = entry.to_dict()
        restored = MeetingEntry.from_dict(data)
        
        self.assertEqual(restored.entry_id, entry.entry_id)
        self.assertEqual(restored.original_text, entry.original_text)
        self.assertEqual(restored.speaker.speaker_id, entry.speaker.speaker_id)


class TestMeetingSession(unittest.TestCase):
    """Test MeetingSession"""
    
    def test_session_creation(self):
        """Test creating a meeting session"""
        session = MeetingSession(
            session_id="test-001",
            title="Test Meeting",
            created_at=datetime.now(),
        )
        
        self.assertEqual(session.session_id, "test-001")
        self.assertEqual(session.title, "Test Meeting")
        self.assertEqual(len(session.entries), 0)
    
    def test_add_entry(self):
        """Test adding entries to session"""
        session = MeetingSession(
            session_id="test-001",
            title="Test Meeting",
            created_at=datetime.now(),
        )
        
        speaker = Speaker("Speaker 1", "Alice")
        entry = MeetingEntry(
            entry_id=1,
            timestamp=datetime.now(),
            speaker=speaker,
            original_text="Hello",
            duration=2.0,
        )
        
        session.add_entry(entry)
        
        self.assertEqual(len(session.entries), 1)
        self.assertIn("Speaker 1", session.speakers)
        self.assertEqual(session.speakers["Speaker 1"].entry_count, 1)
        self.assertEqual(session.speakers["Speaker 1"].total_duration, 2.0)
    
    def test_speaker_stats(self):
        """Test speaker statistics"""
        session = MeetingSession(
            session_id="test-001",
            title="Test Meeting",
            created_at=datetime.now(),
        )
        
        # Add entries from different speakers
        for i in range(4):
            speaker = Speaker(f"Speaker {i % 2 + 1}")
            entry = MeetingEntry(
                entry_id=i,
                timestamp=datetime.now(),
                speaker=speaker,
                original_text=f"Entry {i}",
                duration=2.0,
            )
            session.add_entry(entry)
        
        stats = session.get_speaker_stats()
        self.assertEqual(stats["total_entries"], 4)
        self.assertEqual(len(stats["speakers"]), 2)


class TestMeetingExporter(unittest.TestCase):
    """Test export functionality"""
    
    def setUp(self):
        self.exporter = MeetingExporter()
        self.session = MeetingSession(
            session_id="test-001",
            title="Test Meeting",
            created_at=datetime(2026, 2, 21, 10, 0, 0),
        )
        
        # Add test entries
        for i in range(3):
            speaker = Speaker(f"Speaker {i % 2 + 1}")
            entry = MeetingEntry(
                entry_id=i,
                timestamp=datetime(2026, 2, 21, 10, i, 0),
                speaker=speaker,
                original_text=f"Test entry {i}",
                translated_text=f"翻訳 {i}" if i % 2 == 0 else None,
                confidence=0.85,
                duration=2.0,
            )
            self.session.add_entry(entry)
    
    def test_export_markdown(self):
        """Test Markdown export"""
        content = self.exporter._export_markdown(self.session, True)
        
        self.assertIn("# Test Meeting", content)
        self.assertIn("Test entry 0", content)
        self.assertIn("Participants", content)
    
    def test_export_text(self):
        """Test text export"""
        content = self.exporter._export_text(self.session, True)
        
        self.assertIn("MEETING: Test Meeting", content)
        self.assertIn("Test entry 0", content)
    
    def test_export_json(self):
        """Test JSON export"""
        content = self.exporter._export_json(self.session, True)
        
        self.assertIn("test-001", content)
        self.assertIn("Test Meeting", content)
        self.assertIn("Test entry 0", content)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestMeetingEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestMeetingSession))
    suite.addTests(loader.loadTestsFromTestCase(TestMeetingExporter))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
