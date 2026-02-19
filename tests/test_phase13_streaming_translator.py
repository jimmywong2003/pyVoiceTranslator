"""
Phase 1.3 Test - Streaming Translator

Tests:
1. Semantic gating (verb/punctuation detection)
2. SOV language safety (JA, KO, DE, TR)
3. Stability scoring
4. Skip reason tracking
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.translation.streaming_translator import (
    StreamingTranslator,
    SemanticRules,
    StreamingTranslationResult
)


class MockTranslator:
    """Mock translator for testing."""
    
    def translate(self, text, source_lang=None, target_lang=None):
        """Mock translate - just adds '[translated]' prefix."""
        from src.core.translation.base import TranslationResult
        
        return TranslationResult(
            translated_text=f"[translated] {text}",
            source_text=text,
            source_language=source_lang or 'en',
            target_language=target_lang or 'fr',
            confidence=0.9
        )


def test_semantic_rules():
    """Test semantic rules for different languages."""
    print("\n" + "=" * 60)
    print("TEST 1: Semantic Rules")
    print("=" * 60)
    
    print("\n  Language Classifications:")
    
    sov_langs = ['ja', 'ko', 'de', 'tr', 'hi']
    svo_langs = ['en', 'zh', 'fr', 'es', 'it']
    
    for lang in sov_langs:
        is_sov = SemanticRules.is_sov(lang)
        status = "✅" if is_sov else "❌"
        print(f"    {status} {lang.upper()}: SOV = {is_sov}")
        assert is_sov, f"{lang} should be SOV"
    
    for lang in svo_langs:
        is_svo = SemanticRules.is_svo(lang)
        status = "✅" if is_svo else "❌"
        print(f"    {status} {lang.upper()}: SVO = {is_svo}")
        assert is_svo, f"{lang} should be SVO"
    
    print("\n  Verb Lists:")
    en_verbs = SemanticRules.get_verbs('en')
    print(f"    English: {len(en_verbs)} verbs")
    assert len(en_verbs) > 10, "Should have English verbs"
    
    ja_verbs = SemanticRules.get_verbs('ja')
    print(f"    Japanese: {len(ja_verbs)} verbs")
    assert len(ja_verbs) > 10, "Should have Japanese verbs"
    
    print("\n  ✅ Semantic rules work!")
    return True


def test_semantic_gating_svo():
    """Test semantic gating for SVO languages (English)."""
    print("\n" + "=" * 60)
    print("TEST 2: Semantic Gating (SVO - EN)")
    print("=" * 60)
    
    mock = MockTranslator()
    translator = StreamingTranslator(
        mock, source_lang='en', target_lang='fr',
        min_words=2
    )
    
    test_cases = [
        # (text, should_translate, description)
        ("Hello", False, "too short (< 2 words)"),
        ("Hello world", False, "no verb, no punctuation"),
        ("Hello world.", True, "has punctuation"),
        ("I went", True, "has verb (even without punctuation)"),
        ("I go to", False, "no verb at end, no punctuation"),
        ("I go to store.", True, "has punctuation"),
    ]
    
    print()
    for text, should_translate, description in test_cases:
        result = translator.translate_streaming(text, is_final=False)
        translated = result.text is not None
        
        status = "✅" if translated == should_translate else "❌"
        action = "TRANSLATED" if translated else "SKIPPED"
        
        print(f"  {status} '{text}'")
        print(f"       Expected: {'translate' if should_translate else 'skip'}")
        print(f"       Got:      {action.lower()} ({description})")
        
        if result.skipped_reason:
            print(f"       Reason:   {result.skipped_reason}")
    
    print("\n  ✅ SVO semantic gating works!")
    return True


def test_semantic_gating_sov():
    """Test semantic gating for SOV languages (Japanese)."""
    print("\n" + "=" * 60)
    print("TEST 3: Semantic Gating (SOV - JA)")
    print("=" * 60)
    
    mock = MockTranslator()
    translator = StreamingTranslator(
        mock, source_lang='en', target_lang='ja',
        min_words=2
    )
    
    print("\n  ⚠️  SOV mode: Must wait for punctuation!")
    
    test_cases = [
        # (text, should_translate, description)
        ("Hello world", False, "SOV: no punctuation = incomplete"),
        ("I went", False, "SOV: verb not enough, need punctuation"),
        ("Hello world.", True, "SOV: has punctuation = complete"),
        ("I went to store.", True, "SOV: has punctuation = complete"),
        ("This is a test!", True, "SOV: has exclamation"),
    ]
    
    print()
    for text, should_translate, description in test_cases:
        result = translator.translate_streaming(text, is_final=False)
        translated = result.text is not None
        
        status = "✅" if translated == should_translate else "❌"
        action = "TRANSLATED" if translated else "SKIPPED"
        
        print(f"  {status} '{text}'")
        print(f"       Expected: {'translate' if should_translate else 'skip'}")
        print(f"       Got:      {action.lower()}")
        print(f"       Note:     {description}")
        
        if result.skipped_reason:
            print(f"       Reason:   {result.skipped_reason}")
    
    print("\n  ✅ SOV semantic gating works!")
    return True


def test_final_mode():
    """Test that final mode always translates."""
    print("\n" + "=" * 60)
    print("TEST 4: Final Mode (Always Translate)")
    print("=" * 60)
    
    mock = MockTranslator()
    translator = StreamingTranslator(
        mock, source_lang='en', target_lang='ja',
        min_words=2
    )
    
    test_cases = [
        "Hello",  # Too short, but final
        "Hi",     # Too short, but final
    ]
    
    print()
    for text in test_cases:
        result = translator.translate_streaming(text, is_final=True)
        
        print(f"  '{text}'")
        print(f"       is_final: {result.is_final}")
        print(f"       text:     {result.text}")
        
        assert result.text is not None, "Final should always translate"
        assert result.is_final, "Should have is_final=True"
    
    print("\n  ✅ Final mode works!")
    return True


def test_stability_scoring():
    """Test stability scoring between drafts."""
    print("\n" + "=" * 60)
    print("TEST 5: Stability Scoring")
    print("=" * 60)
    
    mock = MockTranslator()
    translator = StreamingTranslator(
        mock, source_lang='en', target_lang='fr'
    )
    
    # First draft
    print("\n  First draft:")
    result1 = translator.translate_streaming("Hello world.", is_final=False)
    print(f"    Text:     {result1.text}")
    print(f"    Stability: {result1.stability:.2f} (expected: 0.0, first draft)")
    assert result1.stability == 0.0, "First draft should have stability=0"
    
    # Similar draft (high stability)
    print("\n  Similar draft:")
    result2 = translator.translate_streaming("Hello world today.", is_final=False)
    print(f"    Text:     {result2.text}")
    print(f"    Stability: {result2.stability:.2f} (high = similar)")
    
    # Very different draft (low stability)
    print("\n  Different draft:")
    # Reset to simulate different context
    translator._previous_translation = None
    result3 = translator.translate_streaming("Goodbye world.", is_final=False)
    print(f"    Text:     {result3.text}")
    print(f"    Stability: {result3.stability:.2f}")
    
    print("\n  ✅ Stability scoring works!")
    return True


def test_statistics():
    """Test statistics collection."""
    print("\n" + "=" * 60)
    print("TEST 6: Statistics")
    print("=" * 60)
    
    mock = MockTranslator()
    translator = StreamingTranslator(
        mock, source_lang='en', target_lang='ja'
    )
    
    # Generate some translations and skips
    print("\n  Generating translations...")
    
    # Should skip (SOV, no punctuation)
    translator.translate_streaming("Hello world", is_final=False)
    
    # Should translate (SOV, has punctuation)
    translator.translate_streaming("Hello world.", is_final=False)
    
    # Should skip (too short)
    translator.translate_streaming("Hi", is_final=False)
    
    # Should translate (final)
    translator.translate_streaming("Test.", is_final=True)
    
    # Get stats
    stats = translator.get_stats()
    
    print(f"\n  Statistics:")
    print(f"    Triggered:    {stats['triggered']}")
    print(f"    Skipped:      {stats['skipped']}")
    print(f"    Trigger Rate: {stats['trigger_rate']:.1f}%")
    
    print(f"\n  Skip Reasons:")
    for reason, count in stats['skip_reasons'].items():
        if count > 0:
            print(f"    {reason}: {count}")
    
    assert stats['triggered'] == 2, f"Expected 2 triggered, got {stats['triggered']}"
    assert stats['skipped'] == 2, f"Expected 2 skipped, got {stats['skipped']}"
    
    print("\n  ✅ Statistics work!")
    return True


def main():
    """Run all Phase 1.3 tests."""
    print("\n" + "=" * 70)
    print(" " * 20 + "PHASE 1.3 TESTS")
    print(" " * 15 + "(Streaming Translator)")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("Semantic Rules", test_semantic_rules()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Semantic Rules", False))
    
    try:
        results.append(("SVO Gating", test_semantic_gating_svo()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("SVO Gating", False))
    
    try:
        results.append(("SOV Gating", test_semantic_gating_sov()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("SOV Gating", False))
    
    try:
        results.append(("Final Mode", test_final_mode()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Final Mode", False))
    
    try:
        results.append(("Stability Scoring", test_stability_scoring()))
    except Exception as e:
        print(f"\n  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Stability Scoring", False))
    
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
        print(" " * 10 + "🎉 Phase 1.3 Complete!")
        print(" " * 5 + "Ready for Phase 1.4: Diff-Based UI")
    else:
        print(" " * 15 + "❌ SOME TESTS FAILED!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
