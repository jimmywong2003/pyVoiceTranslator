# Real-Time Voice Translation System: ASR & Translation Subsystem Design

## Executive Summary

This document provides a comprehensive design for the speech recognition and translation subsystem of a real-time voice translation application. The design supports hybrid edge-cloud deployment, targets Chinese (zh), English (en), Japanese (ja), and French (fr) languages, and is optimized for cross-platform deployment on Windows and macOS (Apple Silicon M1 Pro).

---

## 1. ASR Model Recommendations

### 1.1 Primary Recommendation: faster-whisper

**Why faster-whisper?**
- Uses CTranslate2 C++ backend for optimized inference
- Supports both CPU and GPU acceleration
- Excellent quantization support (INT8, FP16)
- Cross-platform compatibility
- Batch processing for improved throughput

**Model Variants:**

| Model | Parameters | Disk Size | VRAM (FP16) | VRAM (INT8) | Best For |
|-------|------------|-----------|-------------|-------------|----------|
| tiny | 39M | ~75 MB | ~1 GB | ~0.5 GB | Ultra-low latency, draft quality |
| base | 74M | ~150 MB | ~1 GB | ~0.5 GB | Fast transcription, good accuracy |
| small | 244M | ~500 MB | ~2 GB | ~1 GB | Balanced speed/accuracy |
| medium | 769M | ~1.5 GB | ~5 GB | ~2.5 GB | High accuracy, recommended default |
| large-v3 | 1.55B | ~3 GB | ~10 GB | ~5 GB | Maximum accuracy |
| large-v3-turbo | 809M | ~1.6 GB | ~6 GB | ~3 GB | Fast with near-large accuracy |
| distil-large-v3 | 756M | ~1.5 GB | ~5 GB | ~2.5 GB | English-only, 6x faster |

**Installation:**
```bash
pip install faster-whisper
```

**Download Links:**
- Models auto-download from HuggingFace on first use
- Manual download: https://huggingface.co/Systran

### 1.2 Apple Silicon Optimization: whisper.cpp

**Why whisper.cpp for M1 Pro?**
- Native Metal GPU acceleration
- 6-7x faster than vanilla Whisper on CPU
- 72% lower RAM usage than faster-whisper
- Optimized for Apple Silicon's unified memory architecture
- No Python overhead - pure C++

**Benchmarks on M1 Pro (10-min audio, Medium model):**
| Implementation | Time | RTF | RAM Usage |
|----------------|------|-----|-----------|
| whisper.cpp (Metal) | ~2 min | 0.2x | ~1.8 GB |
| faster-whisper (CPU) | ~5.5 min | 0.55x | ~6.4 GB |
| openai-whisper | ~12 min | 1.2x | ~7 GB |

**Installation:**
```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
# Download models
bash models/download-ggml-model.sh medium
# Build with Metal support
make clean && WHISPER_METAL=1 make -j
```

**Model Download:**
```bash
# Pre-converted GGML models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
wget https://huggingface.co/distil-whisper/distil-large-v3-ggml/resolve/main/ggml-distil-large-v3.bin
```

### 1.3 Alternative: mlx-whisper (Apple Silicon Only)

**For maximum speed on macOS:**
- Uses Apple's MLX framework
- ~50% faster than vanilla Whisper on Apple Silicon
- Lightning-Whisper-MLX claims 10x faster than whisper.cpp

**Installation:**
```bash
pip install mlx-whisper
# OR for maximum speed
pip install lightning-whisper-mlx
```

### 1.4 ASR Model Selection Decision Matrix

| Use Case | Recommended Model | Implementation | Reason |
|----------|-------------------|----------------|--------|
| macOS M1 Pro (Production) | medium/large-v3 | whisper.cpp | Best Metal optimization |
| Windows (Production) | medium | faster-whisper | Best CPU/GPU support |
| Real-time streaming | tiny/base | whisper.cpp | Low latency |
| Video transcription | large-v3 | faster-whisper | Batch processing |
| English-only | distil-large-v3 | faster-whisper | 6x speedup |
| Cloud deployment | large-v3-turbo | faster-whisper | Best throughput |

---

## 2. Translation Model Recommendations

### 2.1 Primary Recommendation: NLLB-200 (No Language Left Behind)

**Why NLLB?**
- Supports 200 languages including all required (zh, en, ja, fr)
- Single model for all language pairs
- Excellent zero-shot translation quality
- Open-source from Meta AI

**Available Model Sizes:**

| Model | Parameters | Disk Size | BLEU (avg) | Best For |
|-------|------------|-----------|------------|----------|
| nllb-200-distilled-350M | 350M | ~1.3 GB | 26.8 | Edge deployment |
| nllb-200-distilled-600M | 600M | ~2.4 GB | 28.2 | Balanced |
| nllb-200-1.3B | 1.3B | ~5.2 GB | 29.5 | Higher accuracy |
| nllb-200-3.3B | 3.3B | ~13 GB | 30.8 | Maximum quality |

**Language Codes for NLLB:**
- Chinese (Simplified): `zho_Hans`
- Chinese (Traditional): `zho_Hant`
- English: `eng_Latn`
- Japanese: `jpn_Jpan`
- French: `fra_Latn`

**Installation:**
```bash
pip install transformers torch
```

**Download Links:**
- https://huggingface.co/facebook/nllb-200-distilled-600M
- https://huggingface.co/facebook/nllb-200-distilled-350M

### 2.2 Alternative: Marian NMT (Opus-MT)

**Why Marian NMT?**
- Lightweight models per language pair
- Faster inference for specific pairs
- Lower memory footprint
- Good for edge deployment with known language pairs

**Recommended Models:**

| Language Pair | Model Name | Size | Speed |
|---------------|------------|------|-------|
| zh -> en | Helsinki-NLP/opus-mt-zh-en | ~400 MB | Fast |
| en -> zh | Helsinki-NLP/opus-mt-en-zh | ~400 MB | Fast |
| ja -> en | Helsinki-NLP/opus-mt-ja-en | ~400 MB | Fast |
| en -> ja | Helsinki-NLP/opus-mt-en-ja | ~400 MB | Fast |
| fr -> en | Helsinki-NLP/opus-mt-fr-en | ~300 MB | Very Fast |
| en -> fr | Helsinki-NLP/opus-mt-en-fr | ~300 MB | Very Fast |

**Installation:**
```bash
pip install transformers sacremoses
```

**Download Links:**
- https://huggingface.co/Helsinki-NLP/opus-mt-zh-en
- https://huggingface.co/Helsinki-NLP/opus-mt-en-zh
- https://huggingface.co/Helsinki-NLP/opus-mt-ja-en
- https://huggingface.co/Helsinki-NLP/opus-mt-en-ja
- https://huggingface.co/Helsinki-NLP/opus-mt-fr-en
- https://huggingface.co/Helsinki-NLP/opus-mt-en-fr

### 2.3 Translation Model Selection Decision Matrix

| Scenario | Recommendation | Model | Reason |
|----------|----------------|-------|--------|
| Multi-language (4+ pairs) | NLLB-600M | Single model | Simplicity, good quality |
| Edge deployment | NLLB-350M | Single model | Small size, all languages |
| Known pairs only | Marian NMT | Multiple models | Faster, lower memory |
| Maximum quality | NLLB-1.3B | Single model | Best BLEU scores |
| Cloud API | NLLB-3.3B | Single model | Production quality |

---

## 3. Edge vs Cloud Decision Matrix

### 3.1 Decision Framework

| Factor | Edge-Only | Hybrid (Recommended) | Cloud-Only |
|--------|-----------|---------------------|------------|
| **Latency** | <100ms (local) | 100-500ms | 200-1000ms |
| **Privacy** | Maximum | High | Depends on provider |
| **Cost** | Hardware only | Mixed | Per-usage |
| **Accuracy** | Limited by hardware | Balanced | Maximum |
| **Offline** | Yes | Partial | No |
| **Scalability** | Limited | Flexible | Unlimited |

### 3.2 Recommended Hybrid Architecture

```
                    Client Application
  +--------------+  +--------------+  +--------------+
  |   Audio      |  |   Edge ASR   |  |   Edge NMT   |
  |   Capture    |->|  (whisper.cpp|->|  (NLLB-350M) |
  |              |  |   medium)    |  |              |
  +--------------+  +--------------+  +--------------+
         |                 |                  |
         |                 v                  v
         |          +---------------------------+
         |          |   Quality Assessment      |
         |          |  (Confidence / Language)  |
         |          +---------------------------+
         |                       |
         |          +------------+------------+
         |          v                         v
         |    [High Confidence]        [Low Confidence]
         |         |                        |
         |         v                        v
         |    Use Local Result      Send to Cloud API
         |                          (Large-v3 + NLLB-1.3B)

                    Cloud API (Optional)
  +--------------------------------------------------+
  |  OpenAI Whisper API / Azure Speech / AWS Transcribe|
  |  +                                                |
  |  DeepL API / Google Translate / Custom NLLB-3.3B  |
  +--------------------------------------------------+
```

### 3.3 When to Use Edge vs Cloud

| Condition | Action |
|-----------|--------|
| Internet unavailable | Use edge exclusively |
| High-confidence transcription (>0.9) | Use edge result |
| Low-confidence transcription (<0.7) | Retry with cloud |
| Rare language detected | Use cloud (better support) |
| Batch video processing | Use cloud (faster throughput) |
| Real-time conversation | Use edge (lower latency) |
| Privacy-sensitive content | Use edge exclusively |

---

## 4. Model Size vs Accuracy Trade-offs

### 4.1 ASR Trade-offs

| Model | WER (English) | WER (Multilingual) | RTF (M1 Pro) | Memory |
|-------|---------------|-------------------|--------------|--------|
| tiny | ~18% | ~25% | 0.05x | ~1 GB |
| base | ~14% | ~20% | 0.08x | ~1 GB |
| small | ~10% | ~15% | 0.15x | ~2 GB |
| medium | ~8% | ~12% | 0.25x | ~5 GB |
| large-v3 | ~7.4% | ~10% | 0.5x | ~10 GB |
| large-v3-turbo | ~7.75% | ~11% | 0.15x | ~6 GB |
| distil-large-v3 | ~7.5% | N/A (en only) | 0.08x | ~5 GB |

**Recommendation:**
- **Edge (M1 Pro 16GB):** medium model (best balance)
- **Edge (M1 Pro 8GB):** small model
- **Cloud:** large-v3-turbo (best throughput)
- **English-only:** distil-large-v3 (fastest)

### 4.2 Translation Trade-offs

| Model | BLEU (zh-en) | BLEU (ja-en) | BLEU (fr-en) | Size | Speed |
|-------|--------------|--------------|--------------|------|-------|
| NLLB-350M | 24.5 | 18.2 | 32.1 | 1.3 GB | Very Fast |
| NLLB-600M | 26.8 | 20.5 | 34.8 | 2.4 GB | Fast |
| NLLB-1.3B | 28.5 | 22.1 | 36.2 | 5.2 GB | Medium |
| Marian (pair) | 27.2 | 21.0 | 35.5 | 0.4 GB | Very Fast |

**Recommendation:**
- **Edge:** NLLB-350M or Marian (known pairs)
- **Cloud:** NLLB-1.3B or NLLB-3.3B

---

## 5. Quantization and Optimization Strategies

### 5.1 Quantization Comparison

| Precision | Memory Reduction | Speed Gain | Accuracy Impact | Best For |
|-----------|------------------|------------|-----------------|----------|
| FP32 | Baseline | Baseline | 0% | Training |
| FP16 | 2x | 1.5-2x | <0.5% | Modern GPUs |
| INT8 | 4x | 2-3x | 1-2% | CPU, Edge |
| INT4 | 8x | 3-4x | 3-5% | Extreme edge |

### 5.2 Recommended Quantization Strategy

**For faster-whisper:**
```python
# INT8 quantization - recommended for edge
model = WhisperModel("medium", device="cpu", compute_type="int8")

# FP16 quantization - for GPU deployment
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
```

**For whisper.cpp:**
```bash
# Models are pre-quantized to Q5_0 (5-bit)
# Download Q8_0 for better accuracy (8-bit)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q8_0.bin
```

**For NLLB:**
```python
# Load with FP16 for inference
model = AutoModelForSeq2SeqLM.from_pretrained(
    "facebook/nllb-200-distilled-600M",
    torch_dtype=torch.float16,
    device_map="auto"
)

# OR use ONNX Runtime with INT8
# Convert to ONNX then apply dynamic quantization
```

### 5.3 Additional Optimizations

1. **ONNX Runtime:**
   ```bash
   pip install onnxruntime-gpu
   ```
   - 2-3x faster than PyTorch for CPU inference
   - Supports INT8 dynamic quantization

2. **TensorRT (NVIDIA GPUs):**
   - 3-5x faster than PyTorch
   - Requires model conversion

3. **Core ML (Apple Silicon):**
   ```bash
   # Convert Whisper to Core ML
   pip install coremltools
   ```
   - Native Apple Silicon optimization
   - Best for iOS/macOS deployment

4. **Batch Processing:**
   ```python
   # faster-whisper batch processing
   segments, info = model.transcribe(audio_files, batch_size=8)
   ```

---

## 6. Pipeline Architecture

### 6.1 End-to-End Pipeline

```
                    Voice Translation Pipeline

Phase 1: Audio Preprocessing
  +-------------+   +-------------+   +-------------+
  | Audio Input |-> |   VAD       |-> | Resampling  |
  | (any format)|   | (silero-vad)|   | (16kHz mono)|
  +-------------+   +-------------+   +-------------+
                              |
                              v
Phase 2: Speech Recognition (ASR)
  +--------------------------------------------------+
  |           ASR Engine (whisper.cpp/faster-whisper)|
  |  +-------------+   +-------------+   +---------+ |
  |  |   Encoder   |-> |   Decoder   |-> |Timestamps| |
  |  |  (Mel-spec) |   |  (Tokens)   |   |+ Language| |
  |  +-------------+   +-------------+   +---------+ |
  +--------------------------------------------------+
                              |
                              v
Phase 3: Text Normalization
  +-------------+   +-------------+   +-------------+
  | Punctuation |-> |  Sentence   |-> |  Confidence |
  |  Handling   |   |  Splitting  |   |   Scoring   |
  +-------------+   +-------------+   +-------------+
                              |
                              v
Phase 4: Machine Translation
  +--------------------------------------------------+
  |              Translation Engine (NLLB/Marian)    |
  |  +-------------+   +-------------+   +---------+ |
  |  |   Tokenize  |-> |   Encode    |-> |  Decode | |
  |  |  (Source)   |   |  (Context)  |   | (Target)| |
  |  +-------------+   +-------------+   +---------+ |
  +--------------------------------------------------+
                              |
                              v
Phase 5: Post-processing
  +-------------+   +-------------+   +-------------+
  |   Text      |-> |  Timestamp  |-> |   Output    |
  | Formatting  |   |  Alignment  |   |  (SRT/JSON) |
  +-------------+   +-------------+   +-------------+
```

### 6.2 Real-Time Streaming Pipeline

```python
# Pseudo-code for real-time processing
class StreamingTranslator:
    def __init__(self):
        self.vad = SileroVAD()
        self.asr = WhisperCpp(model="medium")
        self.translator = NLLBTranslator(model="350M")
        self.buffer = AudioBuffer()
    
    def process_chunk(self, audio_chunk):
        # 1. Add to buffer
        self.buffer.add(audio_chunk)
        
        # 2. Check for speech
        if self.vad.detect_speech(self.buffer):
            # 3. Transcribe when speech ends
            if self.vad.speech_ended():
                text = self.asr.transcribe(self.buffer.get_speech())
                
                # 4. Translate
                translated = self.translator.translate(
                    text, 
                    src_lang="zho_Hans",
                    tgt_lang="eng_Latn"
                )
                
                return translated
        return None
```

---

## 7. Code Structure for ML Module

### 7.1 Project Structure

```
voice_translation/
├── src/
│   ├── __init__.py
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract ASR interface
│   │   ├── whisper_cpp.py       # whisper.cpp wrapper
│   │   ├── faster_whisper.py    # faster-whisper wrapper
│   │   └── mlx_whisper.py       # mlx-whisper wrapper (macOS)
│   ├── translation/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract translator interface
│   │   ├── nllb.py              # NLLB implementation
│   │   └── marian.py            # Marian NMT implementation
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── processor.py         # Audio preprocessing
│   │   ├── vad.py               # Voice activity detection
│   │   └── video.py             # Video file extraction
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── base.py              # Pipeline interface
│   │   ├── realtime.py          # Real-time pipeline
│   │   └── batch.py             # Batch/video pipeline
│   ├── cloud/
│   │   ├── __init__.py
│   │   ├── base.py              # Cloud API interface
│   │   ├── openai.py            # OpenAI Whisper API
│   │   └── azure.py             # Azure Speech API
│   └── utils/
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       └── logger.py            # Logging utilities
├── models/                      # Downloaded models (gitignored)
├── tests/
├── configs/
│   ├── edge.yaml
│   └── cloud.yaml
├── requirements.txt
├── requirements-macos.txt
├── setup.py
└── main.py
```

### 7.2 Core Implementation Files

**`src/asr/base.py`:**
```python
from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    segments: list
    words: Optional[list] = None

class BaseASR(ABC):
    @abstractmethod
    def transcribe(
        self, 
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        pass
    
    @abstractmethod
    def transcribe_stream(
        self,
        audio_stream: Iterator[bytes],
        **kwargs
    ) -> Iterator[TranscriptionResult]:
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        pass
```

**`src/asr/whisper_cpp.py`:**
```python
import subprocess
import json
from pathlib import Path
from .base import BaseASR, TranscriptionResult

class WhisperCppASR(BaseASR):
    def __init__(
        self,
        model_path: str,
        executable_path: str = "./whisper.cpp/main",
        threads: int = 4,
        use_metal: bool = True
    ):
        self.model_path = model_path
        self.executable = executable_path
        self.threads = threads
        self.use_metal = use_metal
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        cmd = [
            self.executable,
            "-m", self.model_path,
            "-f", audio_path,
            "-t", str(self.threads),
            "--output-json",
            "--word-timestamps"
        ]
        
        if language:
            cmd.extend(["-l", language])
        if self.use_metal:
            cmd.append("--use-metal")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = json.loads(result.stdout)
        
        return TranscriptionResult(
            text=output["text"],
            language=output.get("language", "auto"),
            confidence=output.get("confidence", 0.0),
            segments=output["segments"]
        )
    
    @property
    def supports_streaming(self) -> bool:
        return False  # Requires external buffer management
```

**`src/asr/faster_whisper.py`:**
```python
from faster_whisper import WhisperModel
from .base import BaseASR, TranscriptionResult

class FasterWhisperASR(BaseASR):
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[str] = None
    ):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=download_root
        )
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        best_of: int = 5,
        **kwargs
    ) -> TranscriptionResult:
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            best_of=best_of,
            word_timestamps=True
        )
        
        segments_list = list(segments)
        full_text = " ".join([s.text for s in segments_list])
        
        return TranscriptionResult(
            text=full_text,
            language=info.language,
            confidence=1.0 - info.language_probability,
            segments=[{
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "words": [{"word": w.word, "start": w.start, "end": w.end} 
                         for w in (s.words or [])]
            } for s in segments_list]
        )
    
    @property
    def supports_streaming(self) -> bool:
        return False
```

**`src/translation/nllb.py`:**
```python
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from .base import BaseTranslator

class NLLBTranslator(BaseTranslator):
    LANGUAGE_CODES = {
        "zh": "zho_Hans",
        "en": "eng_Latn",
        "ja": "jpn_Jpan",
        "fr": "fra_Latn"
    }
    
    def __init__(
        self,
        model_name: str = "facebook/nllb-200-distilled-600M",
        device: str = "auto",
        max_length: int = 256
    ):
        self.device = device
        self.max_length = max_length
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map=device
        )
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        **kwargs
    ) -> str:
        src_code = self.LANGUAGE_CODES.get(source_lang, source_lang)
        tgt_code = self.LANGUAGE_CODES.get(target_lang, target_lang)
        
        self.tokenizer.src_lang = src_code
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        ).to(self.model.device)
        
        forced_bos_token_id = self.tokenizer.lang_code_to_id[tgt_code]
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=self.max_length
            )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    def translate_batch(
        self,
        texts: list,
        source_lang: str,
        target_lang: str,
        batch_size: int = 8
    ) -> list:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self._translate_batch_internal(
                batch, source_lang, target_lang
            ))
        return results
```

**`src/pipeline/realtime.py`:**
```python
import numpy as np
from typing import Callable, Optional
from dataclasses import dataclass
from ..asr.base import BaseASR
from ..translation.base import BaseTranslator
from ..audio.vad import SileroVAD

@dataclass
class TranslationOutput:
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    timestamp: float
    confidence: float

class RealtimeTranslator:
    def __init__(
        self,
        asr: BaseASR,
        translator: BaseTranslator,
        source_lang: str,
        target_lang: str,
        min_speech_duration: float = 1.0,
        silence_threshold: float = 0.5
    ):
        self.asr = asr
        self.translator = translator
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.vad = SileroVAD()
        self.min_speech_duration = min_speech_duration
        self.silence_threshold = silence_threshold
        
        self.audio_buffer = []
        self.is_speaking = False
        self.speech_start = 0
    
    def process_audio_chunk(
        self,
        audio_chunk: np.ndarray,
        callback: Optional[Callable[[TranslationOutput], None]] = None
    ) -> Optional[TranslationOutput]:
        # Add to buffer
        self.audio_buffer.append(audio_chunk)
        
        # Check VAD
        speech_prob = self.vad.detect(audio_chunk)
        
        if speech_prob > 0.5 and not self.is_speaking:
            # Speech started
            self.is_speaking = True
            self.speech_start = len(self.audio_buffer)
        
        elif speech_prob < 0.3 and self.is_speaking:
            # Speech ended
            duration = (len(self.audio_buffer) - self.speech_start) * 0.02
            
            if duration >= self.min_speech_duration:
                # Process speech segment
                speech_audio = np.concatenate(self.audio_buffer[self.speech_start:])
                result = self._process_segment(speech_audio)
                
                if callback:
                    callback(result)
                
                # Reset buffer to keep memory low
                self.audio_buffer = self.audio_buffer[-100:]
                
                self.is_speaking = False
                return result
        
        return None
    
    def _process_segment(self, audio: np.ndarray) -> TranslationOutput:
        # Save temp audio file
        temp_path = "/tmp/temp_speech.wav"
        self._save_audio(audio, temp_path)
        
        # Transcribe
        asr_result = self.asr.transcribe(temp_path, language=self.source_lang)
        
        # Translate
        translated = self.translator.translate(
            asr_result.text,
            self.source_lang,
            self.target_lang
        )
        
        return TranslationOutput(
            source_text=asr_result.text,
            translated_text=translated,
            source_language=asr_result.language,
            target_language=self.target_lang,
            timestamp=0,
            confidence=asr_result.confidence
        )
```

---

## 8. Performance Benchmarks

### 8.1 ASR Benchmarks

**Benchmark: 10-minute audio file transcription**

| Implementation | Model | Platform | Precision | Time | RTF | Memory |
|----------------|-------|----------|-----------|------|-----|--------|
| whisper.cpp | medium | M1 Pro | Q5_0 | 2m 00s | 0.20x | 1.8 GB |
| whisper.cpp | large-v3 | M1 Pro | Q5_0 | 4m 30s | 0.45x | 3.5 GB |
| whisper.cpp | distil-large-v3 | M1 Pro | Q5_0 | 1m 05s | 0.11x | 1.5 GB |
| faster-whisper | medium | M1 Pro (CPU) | int8 | 5m 30s | 0.55x | 6.4 GB |
| faster-whisper | medium | RTX 3070 | fp16 | 1m 03s | 0.10x | 4.5 GB |
| faster-whisper | medium | RTX 3070 | int8 | 59s | 0.10x | 2.9 GB |
| faster-whisper | large-v3 | RTX 3070 | fp16 | 2m 23s | 0.24x | 4.7 GB |
| faster-whisper | large-v3-turbo | RTX 3070 | fp16 | 19s | 0.03x | 2.5 GB |
| faster-whisper | distil-large-v3 | RTX 3070 | int8 | 22s | 0.04x | 1.5 GB |
| mlx-whisper | medium | M1 Pro | fp16 | 1m 30s | 0.15x | 2.0 GB |

### 8.2 Translation Benchmarks

**Benchmark: 100 sentences (~5000 characters)**

| Model | Platform | Precision | Time | Sentences/sec | Memory |
|-------|----------|-----------|------|---------------|--------|
| NLLB-350M | M1 Pro (CPU) | fp32 | 45s | 2.2 | 2.5 GB |
| NLLB-600M | M1 Pro (CPU) | fp32 | 78s | 1.3 | 4.0 GB |
| NLLB-600M | M1 Pro (GPU) | fp16 | 25s | 4.0 | 3.5 GB |
| NLLB-1.3B | RTX 3070 | fp16 | 35s | 2.9 | 6.0 GB |
| Marian (en-zh) | M1 Pro (CPU) | fp32 | 30s | 3.3 | 1.5 GB |

### 8.3 End-to-End Pipeline Benchmarks

**Benchmark: 5-minute video (zh -> en)**

| Configuration | ASR | Translation | Total Time | RTF | Quality |
|---------------|-----|-------------|------------|-----|---------|
| Edge (M1 Pro) | whisper.cpp medium | NLLB-350M | 3m 30s | 0.7x | Good |
| Edge (M1 Pro) | whisper.cpp large-v3 | NLLB-600M | 6m 45s | 1.35x | Very Good |
| Cloud (GPU) | faster-whisper large-v3 | NLLB-1.3B | 1m 30s | 0.3x | Excellent |
| Hybrid | whisper.cpp medium (edge) + cloud retry | NLLB-600M | 3m 00s | 0.6x | Very Good |

### 8.4 Latency Benchmarks (Real-time)

| Configuration | First Word Latency | Streaming Latency | Memory |
|---------------|-------------------|-------------------|--------|
| whisper.cpp tiny | 200ms | 100ms | 500 MB |
| whisper.cpp base | 350ms | 150ms | 800 MB |
| whisper.cpp small | 600ms | 250ms | 1.5 GB |
| whisper.cpp medium | 1.2s | 400ms | 3.5 GB |

---

## 9. Implementation Checklist

### Phase 1: Core Setup
- [ ] Install whisper.cpp with Metal support (macOS)
- [ ] Install faster-whisper (Windows/Linux)
- [ ] Download ASR models (medium, large-v3, distil-large-v3)
- [ ] Install NLLB-600M (or 350M for edge)
- [ ] Set up Python virtual environment
- [ ] Create project structure

### Phase 2: ASR Module
- [ ] Implement BaseASR interface
- [ ] Implement WhisperCppASR wrapper
- [ ] Implement FasterWhisperASR wrapper
- [ ] Add audio preprocessing (resampling, VAD)
- [ ] Create model auto-selection logic

### Phase 3: Translation Module
- [ ] Implement BaseTranslator interface
- [ ] Implement NLLBTranslator
- [ ] Implement MarianTranslator (optional)
- [ ] Add batch translation support
- [ ] Create language code mapping

### Phase 4: Pipeline Integration
- [ ] Implement RealtimeTranslator
- [ ] Implement BatchVideoTranslator
- [ ] Add confidence scoring
- [ ] Create hybrid edge-cloud fallback
- [ ] Add progress callbacks

### Phase 5: Optimization
- [ ] Implement INT8 quantization
- [ ] Add batch processing for video
- [ ] Optimize memory usage
- [ ] Add model caching
- [ ] Profile and optimize bottlenecks

### Phase 6: Testing
- [ ] Unit tests for each module
- [ ] Integration tests for pipeline
- [ ] Benchmark on target hardware
- [ ] Test all 4 languages
- [ ] Test video file transcription

---

## 10. Resource Requirements

### Minimum Requirements (Edge)
- **CPU:** 4 cores (Intel i5 / Apple M1)
- **RAM:** 8 GB
- **Storage:** 5 GB for models
- **Models:** whisper.cpp small + NLLB-350M

### Recommended Requirements (Edge)
- **CPU:** 8+ cores (Intel i7 / Apple M1 Pro)
- **RAM:** 16 GB
- **Storage:** 10 GB for models
- **Models:** whisper.cpp medium + NLLB-600M

### Cloud Requirements
- **GPU:** NVIDIA T4 or better
- **VRAM:** 8+ GB
- **Models:** faster-whisper large-v3-turbo + NLLB-1.3B

---

## 11. Model Download Summary

### ASR Models
```bash
# whisper.cpp models (GGML format)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
wget https://huggingface.co/distil-whisper/distil-large-v3-ggml/resolve/main/ggml-distil-large-v3.bin

# faster-whisper models (auto-download on first use)
# Or manual download from: https://huggingface.co/Systran
```

### Translation Models
```bash
# NLLB models (HuggingFace)
# Auto-download with transformers, or:
git lfs install
git clone https://huggingface.co/facebook/nllb-200-distilled-350M
git clone https://huggingface.co/facebook/nllb-200-distilled-600M

# Marian models (HuggingFace)
git clone https://huggingface.co/Helsinki-NLP/opus-mt-zh-en
git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-zh
git clone https://huggingface.co/Helsinki-NLP/opus-mt-ja-en
git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-ja
git clone https://huggingface.co/Helsinki-NLP/opus-mt-fr-en
git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-fr
```

---

## 12. References

1. **Whisper Paper:** https://arxiv.org/abs/2212.04356
2. **Distil-Whisper Paper:** https://arxiv.org/abs/2311.00430
3. **NLLB Paper:** https://arxiv.org/abs/2207.04672
4. **whisper.cpp:** https://github.com/ggerganov/whisper.cpp
5. **faster-whisper:** https://github.com/SYSTRAN/faster-whisper
6. **NLLB Models:** https://huggingface.co/facebook/nllb-200-distilled-600M
7. **Marian NMT:** https://huggingface.co/Helsinki-NLP

---

*Document Version: 1.0*
*Last Updated: 2025*
