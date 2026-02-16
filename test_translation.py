#!/usr/bin/env python3
"""
Phase 4: Translation Engine Test Script
Tests MarianMT and NLLB translation models for Chinese-English
"""

import time
import sys

print('='*60)
print('PHASE 4: TRANSLATION ENGINE TEST')
print('='*60)

# Test MarianMT for Chinese-English
print('\n[1] Testing MarianMT (Chinese ↔ English)')
print('-'*60)

try:
    from voice_translation.src.translation.marian import MarianTranslator
    
    # Chinese to English
    print('\nLoading zh→en model...')
    t0 = time.time()
    translator_zh_en = MarianTranslator(source_lang='zh', target_lang='en')
    translator_zh_en.initialize()
    print(f'Loaded in {time.time()-t0:.2f}s')
    
    test_cases = [
        ('你好，世界', 'Hello world'),
        ('谢谢', 'Thank you'),
        ('今天天气很好', 'Nice weather today'),
    ]
    
    print('\nChinese → English:')
    for text, expected in test_cases:
        t0 = time.time()
        result = translator_zh_en.translate(text)
        print(f'  "{text}" → "{result.translated_text}" ({time.time()-t0:.2f}s)')
    
    # English to Chinese
    print('\nLoading en→zh model...')
    t0 = time.time()
    translator_en_zh = MarianTranslator(source_lang='en', target_lang='zh')
    translator_en_zh.initialize()
    print(f'Loaded in {time.time()-t0:.2f}s')
    
    test_cases = [
        ('Hello', '你好'),
        ('Thank you', '谢谢'),
        ('Good morning', '早上好'),
    ]
    
    print('\nEnglish → Chinese:')
    for text, expected in test_cases:
        t0 = time.time()
        result = translator_en_zh.translate(text)
        print(f'  "{text}" → "{result.translated_text}" ({time.time()-t0:.2f}s)')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

# Test NLLB-200
print('\n[2] Testing NLLB-200 (600M)')
print('-'*60)

try:
    from voice_translation.src.translation.nllb import NLLBTranslator
    
    print('\nLoading NLLB model...')
    t0 = time.time()
    translator = NLLBTranslator(model_name='600M', device='auto')
    translator.initialize()
    print(f'Loaded in {time.time()-t0:.2f}s')
    
    test_cases = [
        ('你好', 'zh', 'en'),
        ('Hello', 'en', 'zh'),
        ('Bonjour', 'fr', 'en'),
    ]
    
    print('\nMulti-language translations:')
    for text, src, tgt in test_cases:
        t0 = time.time()
        result = translator.translate(text, src, tgt)
        print(f'  "{text}" ({src}→{tgt}) → "{result.translated_text}" ({time.time()-t0:.2f}s)')

except Exception as e:
    print(f'Error: {e}')

print('\n' + '='*60)
print('TRANSLATION TEST COMPLETE')
print('='*60)
