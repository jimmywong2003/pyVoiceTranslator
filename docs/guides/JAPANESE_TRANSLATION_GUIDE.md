# 🎌 Japanese → English Translation Guide

## ✅ Translation Pipeline Status: WORKING

The Japanese → English translation is fully functional. Here's how to use it correctly:

---

## 🚀 Quick Start

### Option 1: Using the GUI

1. Run the GUI:
   ```bash
   python src/gui/main.py
   ```

2. **Important Settings:**
   - **Source Language**: Select **"Japanese (ja)"** (NOT "Auto-detect")
   - **Target Language**: Select **"English (en)"**
   - **ASR Model**: Select **"base"** (not "tiny" - tiny struggles with Japanese)
   - **Audio Input**: Select your microphone

3. Click **"▶ Start Translation"**

### Option 2: Using CLI

```bash
# Japanese to English with base model
python cli/demo_realtime_translation.py \
  --source ja \
  --target en \
  --asr-model base \
  --device 4

# Or with interview mode (less filtering)
scripts/run/run_interview_mode.sh --source ja --target en --asr-model base
```

---

## ⚠️ Common Mistakes

| Mistake | Why It Fails | Solution |
|---------|--------------|----------|
| Using "Auto-detect" for source | ASR may detect Japanese as Chinese | Always select "Japanese (ja)" |
| Using "tiny" model | Too small for Japanese phonemes | Use "base" or "small" |
| Background noise | Japanese has many similar sounds | Use quiet environment |
| Speaking too fast | ASR needs clear pronunciation | Speak clearly, not too fast |

---

## 🧪 Test Your Setup

Run this test to verify everything works:

```bash
# Test Japanese translation
python test_japanese_translation.py
```

Expected output:
```
✅ Marian supports ja → en
✅ こんにちは、元気ですか？ → Hello. How are you
✅ ありがとうございます → Thank you
```

---

## 📊 Performance Tips

### Model Size Comparison for Japanese

| Model | Speed | Accuracy | Recommendation |
|-------|-------|----------|----------------|
| tiny | Fastest | Poor for JA | ❌ Not recommended |
| base | Fast | Good | ✅ Recommended |
| small | Medium | Better | ✅ Best quality |

### Audio Quality

- **Sample Rate**: 16000 Hz (default)
- **Noise Level**: Quiet environment
- **Distance**: 10-15 cm from microphone
- **Volume**: Normal speaking volume

---

## 🔧 Troubleshooting

### Issue: Japanese not recognized at all

**Check:**
1. Is source language set to "Japanese (ja)"?
2. Is the microphone working? (Check with test script)
3. Are you using "base" model or larger?

**Fix:**
```bash
# List audio devices
python cli/demo_realtime_translation.py --list-devices

# Use specific microphone
python cli/demo_realtime_translation.py \
  --source ja --target en \
  --asr-model base \
  --device 4  # Your mic device ID
```

### Issue: Translation is wrong/gibberish

**Check:**
1. Is ASR output correct? (Check the source text shown)
2. Is it a known Japanese phrase?
3. Is the audio clear?

**Fix:**
- Speak more clearly
- Reduce background noise
- Move closer to microphone
- Use "small" model for better accuracy

### Issue: "No model available for ja -> en"

**Fix:**
```bash
# Install/update transformers
pip install -U transformers sacremoses

# Download Marian model (automatic on first run)
python -c "
from src.core.translation.marian import MarianTranslator
t = MarianTranslator('ja', 'en')
t.initialize()
print('Model downloaded successfully')
"
```

---

## 🎯 Example: Correct Usage

```bash
# 1. Run with correct parameters
python cli/demo_realtime_translation.py \
  --source ja \
  --target en \
  --asr-model base

# 2. Speak Japanese clearly
# Example: "こんにちは、日本語を話しています"

# 3. Expected output:
# 🎤 [ja] こんにちは、日本語を話しています
# 🌐 [en] Hello, I am speaking Japanese
# ⏱️  850ms
```

---

## 📝 Summary

**For best Japanese → English results:**

1. ✅ Always set source language to "Japanese (ja)"
2. ✅ Use "base" or "small" model (not "tiny")
3. ✅ Speak clearly in a quiet environment
4. ✅ Use interview mode for less filtering
5. ✅ Check microphone is working first

**The translation model itself is working correctly** - the issue is usually:
- Wrong language selection
- Poor audio quality
- Model too small
- Background noise
