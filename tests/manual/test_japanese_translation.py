#!/usr/bin/env python3
"""
Test Japanese → English Translation Pipeline
Diagnose issues with ASR, translation, and post-processing
"""

import sys
sys.path.insert(0, '.')

print("="*70)
print("🎌 Japanese → English Translation Diagnostic")
print("="*70)

# Test 1: Check if Marian model supports Japanese
print("\n1️⃣ Checking Translation Model Support...")
from src.core.translation.marian import MarianTranslator

if ('ja', 'en') in MarianTranslator.MODEL_NAMES:
    print(f"   ✅ Marian supports ja → en")
    print(f"   📦 Model: {MarianTranslator.MODEL_NAMES[('ja', 'en')]}")
else:
    print("   ❌ Marian does NOT support ja → en")

# Test 2: Test translation quality
print("\n2️⃣ Testing Translation Quality...")
try:
    translator = MarianTranslator(source_lang='ja', target_lang='en', device='cpu')
    translator.initialize()
    
    test_phrases = [
        ('こんにちは、元気ですか？', 'Hello. How are you'),
        ('これは日本語のテストです', 'This is a Japanese test'),
        ('ありがとうございます', 'Thank you very much'),
    ]
    
    for ja_text, expected_en in test_phrases:
        result = translator.translate(ja_text, 'ja', 'en')
        status = "✅" if expected_en.lower() in result.translated_text.lower() else "⚠️"
        print(f"   {status} {ja_text}")
        print(f"      → {result.translated_text}")
        print(f"      (confidence: {result.confidence:.2f})")
except Exception as e:
    print(f"   ❌ Translation error: {e}")

# Test 3: Check ASR Post-Processor for Japanese
print("\n3️⃣ Checking ASR Post-Processor for Japanese...")
from src.core.asr.post_processor import ASRPostProcessor, PostProcessConfig

# Create post-processor
config = PostProcessConfig(
    enable_hallucination_filter=True,
    language='ja'
)
processor = ASRPostProcessor(config)

# Test with Japanese text
ja_samples = [
    'こんにちは、元気ですか？',
    '日本語を話しています',
    'これはテストです',
    'ありがとうございます、さようなら',
]

print("   Testing Japanese text through post-processor:")
for text in ja_samples:
    result = processor.process(text)
    status = "✅" if not result.should_skip_translation else "❌ FILTERED"
    print(f"   {status} '{text[:30]}...'")
    if result.should_skip_translation:
        print(f"      Reason: {result.filters_applied}")

# Test 4: Check if character diversity check affects CJK
print("\n4️⃣ Checking Character Diversity for CJK...")

def check_diversity(text):
    unique_chars = len(set(text))
    diversity = unique_chars / len(text)
    return diversity

for text in ja_samples:
    diversity = check_diversity(text)
    print(f"   '{text[:20]}...' → diversity: {diversity:.2%}")

print("\n" + "="*70)
print("📝 Summary")
print("="*70)
print("""
Common Issues with Japanese Translation:

1. ASR Language Detection: Make sure to set source language to "Japanese"
   in the GUI/CLI, not "Auto-detect"

2. Post-Processor: The diversity check was designed for alphabetic languages
   and may not work well with Japanese/CJK. Run with interview mode:
   
   ./run_interview_mode.sh

3. Model Size: Use 'base' or larger model for better Japanese recognition
   (tiny model may struggle with Japanese)

4. Audio Quality: Japanese has many similar sounds, requires clear audio

Correct Usage:
   GUI: Select "Japanese (ja)" as source, "English (en)" as target
   CLI: python cli/demo_realtime_translation.py --source ja --target en
""")
