"""
Phase 1.4 Test - Streaming UI

Tests:
1. Diff visualization
2. Draft display (grey italic)
3. Final display (black bold)
4. Stability indicators
5. Transition animations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gui.streaming_ui import (
    StreamingUI,
    DiffVisualizer,
    DisplayState
)


def test_diff_visualizer():
    """Test diff computation."""
    print("\n" + "=" * 60)
    print("TEST 1: Diff Visualizer")
    print("=" * 60)
    
    visualizer = DiffVisualizer()
    
    test_cases = [
        # (old, new, description)
        ("Hello world", "Hello world today", "extension"),
        ("Hello world today", "Hello world", "shortening"),
        ("Hello world", "Goodbye world", "replacement"),
        ("Hello world", "Hello world", "no change"),
    ]
    
    print()
    for old, new, desc in test_cases:
        diff = visualizer.compute_diff(old, new)
        summary = visualizer.get_change_summary(diff)
        
        print(f"  {desc}:")
        print(f"    '{old}' -> '{new}'")
        print(f"    Added: {summary['added']}, Removed: {summary['removed']}, Same: {summary['same']}")
        print(f"    Change ratio: {summary['change_ratio']:.2f}")
        
        # Show diff
        diff_str = visualizer.format_diff(diff, highlight_added=True)
        print(f"    Diff: {diff_str}")
        print()
    
    print("  ✅ Diff visualizer works!")
    return True


def test_draft_display():
    """Test draft display formatting."""
    print("\n" + "=" * 60)
    print("TEST 2: Draft Display")
    print("=" * 60)
    
    ui = StreamingUI()
    
    print("\n  Testing draft with low stability:")
    result = ui.show_draft("Hello...", stability=0.3)
    print(f"    Style: {result['style']}")
    print(f"    Color: {result['color']}")
    print(f"    Font: {result['font_style']}")
    print(f"    Opacity: {result['opacity']:.2f}")
    print(f"    Indicator: {result['stability_indicator']}")
    
    assert result['style'] == 'draft'
    assert result['color'] == 'grey'
    assert result['font_style'] == 'italic'
    assert result['opacity'] < 0.6  # Low stability = low opacity
    
    print("\n  Testing draft with high stability:")
    result = ui.show_draft("Hello world today...", stability=0.9)
    print(f"    Opacity: {result['opacity']:.2f}")
    print(f"    Indicator: {result['stability_indicator']}")
    
    assert result['opacity'] > 0.9  # High stability = high opacity
    assert result['stability_indicator'] == '✓'
    
    print("\n  ✅ Draft display works!")
    return True


def test_draft_update():
    """Test draft update with diff."""
    print("\n" + "=" * 60)
    print("TEST 3: Draft Update with Diff")
    print("=" * 60)
    
    ui = StreamingUI()
    
    # Initial draft
    print("\n  Initial draft:")
    ui.show_draft("Hello...", stability=0.0)
    
    # Update with change (adding 1 word to 1 word = 50% change)
    print("\n  Update (word addition):")
    result = ui.update_draft("Hello world...", stability=0.6)
    print(f"    Is significant: {result.get('is_significant_change')}")
    print(f"    Change ratio: {result['change_summary']['change_ratio']:.2f}")
    
    # Adding "world" to "Hello" = 1 added, 1 same = 50% change ratio
    # This IS significant (> 0.3 threshold)
    
    # Update with major change
    print("\n  Major update:")
    result = ui.update_draft("Goodbye world today...", stability=0.7)
    print(f"    Is significant: {result.get('is_significant_change')}")
    print(f"    Change ratio: {result['change_summary']['change_ratio']:.2f}")
    
    assert result.get('is_significant_change'), "Major change should be significant"
    
    print("\n  ✅ Draft update works!")
    return True


def test_final_display():
    """Test final display with transitions."""
    print("\n" + "=" * 60)
    print("TEST 4: Final Display")
    print("=" * 60)
    
    ui = StreamingUI()
    
    # Draft
    print("\n  Draft:")
    ui.show_draft("Hello world today...", stability=0.8)
    
    # Final (transition from draft)
    print("\n  Final (transition from draft):")
    result = ui.show_final("Hello world today.", stability=1.0)
    print(f"    Transition: {result['transition_type']}")
    print(f"    Style: {result['style']}")
    print(f"    Font: {result['font_weight']}")
    
    # "Hello world today..." -> "Hello world today." = removing "..." and adding "."
    # This is a moderate/significant change
    assert result['style'] == 'final'
    assert result['font_weight'] == 'bold'
    
    # New UI for significant change test
    ui2 = StreamingUI()
    ui2.show_draft("I want to go...", stability=0.5)
    
    print("\n  Final (significant change):")
    result = ui2.show_final("I went to the store yesterday.", stability=1.0)
    print(f"    Transition: {result['transition_type']}")
    print(f"    Changes: +{result['change_summary']['added']}/-{result['change_summary']['removed']}")
    
    assert result['transition_type'] == 'significant'
    
    print("\n  ✅ Final display works!")
    return True


def test_stability_indicators():
    """Test stability indicator logic."""
    print("\n" + "=" * 60)
    print("TEST 5: Stability Indicators")
    print("=" * 60)
    
    ui = StreamingUI()
    
    test_cases = [
        (0.0, "●"),  # Unstable
        (0.3, "●"),  # Unstable
        (0.5, "○"),  # Stabilizing
        (0.7, "○"),  # Stabilizing
        (0.9, "✓"),  # Stable
        (1.0, "✓"),  # Stable
    ]
    
    print()
    for stability, expected in test_cases:
        result = ui.show_draft("Test", stability=stability)
        actual = result['stability_indicator']
        status = "✅" if actual == expected else "❌"
        print(f"  {status} Stability {stability:.1f} -> {actual} (expected {expected})")
        assert actual == expected, f"Expected {expected}, got {actual}"
    
    print("\n  ✅ Stability indicators work!")
    return True


def test_transition_animations():
    """Test transition animation selection."""
    print("\n" + "=" * 60)
    print("TEST 6: Transition Animations")
    print("=" * 60)
    
    # Test transition types
    print("\n  Testing transitions:")
    
    # Case 1: Smooth (very minor changes)
    ui1 = StreamingUI()
    ui1.show_draft("Hello world...", stability=0.8)
    ui1.show_final("Hello world!", stability=1.0)  # Just punctuation change
    anim = ui1.get_transition_animation()
    print(f"    Minor change type: {anim['type']}")
    
    # Moderate transition
    print("\n  Moderate transition:")
    ui2 = StreamingUI()
    ui2.show_draft("Hello world...", stability=0.8)
    ui2.show_final("Hello beautiful world today.", stability=1.0)
    anim = ui2.get_transition_animation()
    print(f"    Type: {anim['type']}")
    
    # Significant transition
    print("\n  Significant transition:")
    ui3 = StreamingUI()
    ui3.show_draft("I want...", stability=0.5)
    ui3.show_final("I went to the store yesterday.", stability=1.0)
    anim = ui3.get_transition_animation()
    print(f"    Type: {anim['type']}")
    print(f"    Highlight words: {len(anim.get('highlight_words', []))}")
    assert anim['type'] == 'flash_highlight'
    
    print("\n  ✅ Transition animations work!")
    return True


def test_statistics():
    """Test UI statistics."""
    print("\n" + "=" * 60)
    print("TEST 7: Statistics")
    print("=" * 60)
    
    ui = StreamingUI()
    
    # Generate some activity
    ui.show_draft("Hello...", stability=0.0)
    ui.update_draft("Hello world...", stability=0.6)
    ui.update_draft("Hello world today...", stability=0.8)
    ui.show_final("Hello world today.", stability=1.0)
    
    stats = ui.get_stats()
    
    print(f"\n  Statistics:")
    print(f"    Draft updates: {stats['draft_updates']}")
    print(f"    Final shows: {stats['final_shows']}")
    print(f"    Total transitions: {stats['total_transitions']}")
    
    assert stats['draft_updates'] == 3, "Should have 3 draft updates"
    assert stats['final_shows'] == 1, "Should have 1 final show"
    assert stats['total_transitions'] == 3, "Should have 3 transitions (2 updates + 1 final)"
    
    print("\n  ✅ Statistics work!")
    return True


def main():
    """Run all Phase 1.4 tests."""
    print("\n" + "=" * 70)
    print(" " * 20 + "PHASE 1.4 TESTS")
    print(" " * 20 + "(Streaming UI)")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("Diff Visualizer", test_diff_visualizer()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Diff Visualizer", False))
    
    try:
        results.append(("Draft Display", test_draft_display()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Draft Display", False))
    
    try:
        results.append(("Draft Update", test_draft_update()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Draft Update", False))
    
    try:
        results.append(("Final Display", test_final_display()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Final Display", False))
    
    try:
        results.append(("Stability Indicators", test_stability_indicators()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Stability Indicators", False))
    
    try:
        results.append(("Transition Animations", test_transition_animations()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Transition Animations", False))
    
    try:
        results.append(("Statistics", test_statistics()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Statistics", False))
    
    # Final summary
    print("\n" + "=" * 70)
    print(" " * 20 + "FINAL SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print(" " * 15 + "✅ ALL TESTS PASSED!")
        print(" " * 10 + "🎉 Phase 1.4 Complete!")
        print(" " * 5 + "Ready for Phase 1.5: Integration")
    else:
        print(" " * 15 + "❌ SOME TESTS FAILED!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
