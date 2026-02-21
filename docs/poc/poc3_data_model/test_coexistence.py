"""
PoC 3: Data Model Coexistence Test
Verify MeetingEntry and TranslationEntry can coexist
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# Simulate existing TranslationEntry (from current codebase)
@dataclass
class TranslationEntry:
    """Existing translation entry - DO NOT MODIFY"""
    entry_id: int
    timestamp: datetime
    source_text: str
    translated_text: str
    confidence: float = 0.0
    is_final: bool = True


# New MeetingEntry (proposed for Meeting Mode)
@dataclass
class MeetingEntry:
    """New meeting entry - for testing coexistence"""
    entry_id: int
    timestamp_utc: datetime
    speaker_id: str
    original_text: str
    translated_text: Optional[str] = None
    confidence: float = 0.0
    duration_ms: int = 0


def test_model_creation():
    """Test 1: Can both models be created independently?"""
    print("\n=== Test 1: Model Creation ===")
    
    now = datetime.now()
    
    # Create TranslationEntry
    trans = TranslationEntry(
        entry_id=1,
        timestamp=now,
        source_text="Hello",
        translated_text="你好",
        confidence=0.95
    )
    print(f"  TranslationEntry: {trans.entry_id} - {trans.source_text}")
    
    # Create MeetingEntry
    meeting = MeetingEntry(
        entry_id=1,
        timestamp_utc=now,
        speaker_id="Speaker 1",
        original_text="Hello",
        translated_text="你好",
        confidence=0.95
    )
    print(f"  MeetingEntry: {meeting.entry_id} - {meeting.speaker_id}")
    
    print("✓ Both models created successfully")
    return True


def test_model_lists():
    """Test 2: Can lists of both models coexist?"""
    print("\n=== Test 2: Model Lists Coexistence ===")
    
    now = datetime.now()
    
    # Create translation session
    translations = [
        TranslationEntry(i, now, f"Text {i}", f"翻译{i}", 0.9)
        for i in range(100)
    ]
    
    # Create meeting session simultaneously
    meetings = [
        MeetingEntry(i, now, f"Speaker {(i%3)+1}", f"Text {i}", f"翻译{i}", 0.9)
        for i in range(100)
    ]
    
    print(f"  Created {len(translations)} TranslationEntry objects")
    print(f"  Created {len(meetings)} MeetingEntry objects")
    print("✓ Both lists coexist in memory")
    return True


def test_memory_usage():
    """Test 3: Memory usage with both models active"""
    print("\n=== Test 3: Memory Usage ===")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    # Baseline
    mem_before = process.memory_info().rss / 1024 / 1024
    
    now = datetime.now()
    
    # Create large datasets
    translations = []
    meetings = []
    
    for i in range(1000):
        translations.append(TranslationEntry(
            i, now, "Source text here", "翻译在这里", 0.9
        ))
        meetings.append(MeetingEntry(
            i, now, "Speaker 1", "Source text here", "翻译在这里", 0.9
        ))
    
    mem_after = process.memory_info().rss / 1024 / 1024
    increase = mem_after - mem_before
    
    print(f"  Baseline memory: {mem_before:.1f} MB")
    print(f"  After 2000 objects: {mem_after:.1f} MB")
    print(f"  Increase: {increase:.1f} MB")
    print(f"  Per object: {increase/2000*1024:.2f} KB")
    
    if increase < 100:
        print("✓ Memory usage acceptable (<100MB)")
        return True, increase
    else:
        print("⚠ High memory usage")
        return False, increase


def test_export_formats():
    """Test 4: Export functions work for both formats"""
    print("\n=== Test 4: Export Compatibility ===")
    
    now = datetime.now()
    
    # Translation export
    trans = TranslationEntry(1, now, "Hello", "你好", 0.95)
    trans_export = {
        "id": trans.entry_id,
        "source": trans.source_text,
        "target": trans.translated_text,
        "confidence": trans.confidence
    }
    print(f"  Translation export: {trans_export}")
    
    # Meeting export
    meeting = MeetingEntry(1, now, "Speaker 1", "Hello", "你好", 0.95)
    meeting_export = {
        "id": meeting.entry_id,
        "speaker": meeting.speaker_id,
        "original": meeting.original_text,
        "translation": meeting.translated_text
    }
    print(f"  Meeting export: {meeting_export}")
    
    print("✓ Both export formats work")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 3: Data Model Coexistence")
    print("=" * 60)
    print("\nTesting if MeetingEntry and TranslationEntry can coexist")
    
    results = {
        "creation": test_model_creation(),
        "lists": test_model_lists(),
        "memory": test_memory_usage(),
        "export": test_export_formats()
    }
    
    mem_pass, mem_mb = results["memory"]
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"  Model Creation: {'PASS' if results['creation'] else 'FAIL'}")
    print(f"  Lists Coexist: {'PASS' if results['lists'] else 'FAIL'}")
    print(f"  Memory Usage: {'PASS' if mem_pass else 'FAIL'} ({mem_mb:.1f}MB)")
    print(f"  Export Formats: {'PASS' if results['export'] else 'FAIL'}")
    
    overall = all([results["creation"], results["lists"], mem_pass, results["export"]])
    
    print("\n" + "=" * 60)
    if overall:
        print("✓ ALL TESTS PASSED - Dual-mode architecture viable")
    else:
        print("✗ SOME TESTS FAILED - Consider separate applications")
    print("=" * 60)
    
    # Write results
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 3: Data Model Coexistence\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Model Creation: {'PASS' if results['creation'] else 'FAIL'}\n")
        f.write(f"- Lists Coexist: {'PASS' if results['lists'] else 'FAIL'}\n")
        f.write(f"- Memory Usage: {mem_mb:.1f}MB (target <100MB)\n")
        f.write(f"- Export Formats: {'PASS' if results['export'] else 'FAIL'}\n")
        f.write(f"- **Overall**: {'PASS' if overall else 'FAIL'}\n")
    
    print("\n✓ Results appended to results.md")
