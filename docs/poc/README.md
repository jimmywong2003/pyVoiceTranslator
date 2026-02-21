# VoiceTranslate Pro - Proof of Concept (PoC)

> **⚠️ CRITICAL:** This directory contains isolated PoC code. Do NOT modify files in `../src/` - copy them here for testing.

## Overview

This directory contains proof-of-concept tests to validate technical feasibility before full implementation.

**Status:** 🔄 In Progress  
**Timeline:** 1 Week (Week 0)  
**Goal:** Validate 4 critical technical assumptions

---

## Current Results

| PoC | Status | Result |
|-----|--------|--------|
| 1 - Custom QSS | 🔄 **In Progress** | PySide6 + Custom QSS (license-safe) |
| 2 - Speaker Diarization | ✅ **COMPLETE** | ✅ PASS - 0.04ms latency |
| 3 - Data Model Coexistence | ✅ **COMPLETE** | ✅ PASS - Dual mode viable |
| 4 - Async Model Download | 🔄 **In Progress** | Pending UI test |

### Summary of Findings

**Architecture Decision:**
- ✅ **PySide6 + Custom QSS** (LGPL/commercial-friendly)
- ❌ **PyQt-Fluent-Widgets NOT USED** (GPL licensing risk)

**Good News:**
- **PoC 2:** Speaker diarization adds only 0.04ms latency (125x better than 50ms target)
- **PoC 3:** Data models coexist with 0.3MB memory overhead (333x better than 100MB target)

---

## PoC Structure

```
poc/
├── README.md                       # This file
├── requirements.txt                # PoC-specific dependencies
├── poc1_custom_qss/                # PoC 1: Custom QSS Theme
│   ├── README.md
│   ├── test_custom_theme.py
│   ├── test_components.py
│   ├── test_threading.py
│   └── results.md                  # Fill in after testing
├── poc2_speaker_diarization/       # PoC 2: Speaker Detection
│   ├── README.md
│   ├── speaker_test.py
│   ├── test_latency.py             # CRITICAL: Real audio test
│   ├── test_integration.py
│   └── results.md                  # ✅ COMPLETE
├── poc3_data_model/                # PoC 3: Model Coexistence
│   ├── README.md
│   ├── test_coexistence.py
│   ├── test_macos_gatekeeper.py    # Test macOS warnings
│   └── results.md                  # ✅ COMPLETE
└── poc4_model_download/            # PoC 4: Model Management
    ├── README.md
    ├── model_manager_test.py
    ├── test_async_ui.py            # CRITICAL: UI responsiveness
    ├── test_resume.py
    ├── test_permissions.py
    └── results.md                  # 🔄 In progress
```

---

## PoC Rules

1. **🚫 DO NOT MODIFY `../src/`** - Main codebase remains untouched
2. **📂 Isolate all work** - Keep everything in `poc/` subdirectories
3. **📋 Document everything** - Each PoC must have `results.md`
4. **🧪 Test realistically** - Use real audio, real data, real scenarios
5. **🗑️ Cleanup allowed** - This folder can be deleted after implementation

---

## Dependencies

Install PoC dependencies:

```bash
cd poc
pip install -r requirements.txt
```

**Note:** PyQt-Fluent-Widgets is NOT included due to GPL licensing. We use Custom QSS with PySide6 instead.

---

## Running PoCs

### PoC 1: Custom QSS Theme
```bash
cd poc1_custom_qss
python test_custom_theme.py
python test_components.py
python test_threading.py
```

### PoC 2: Speaker Diarization
```bash
cd poc2_speaker_diarization
python speaker_test.py      # ✅ COMPLETE
python test_latency.py      # Requires microphone
python test_integration.py
```

### PoC 3: Data Model Coexistence
```bash
cd poc3_data_model
python test_coexistence.py  # ✅ COMPLETE
```

### PoC 4: Model Download (Async)
```bash
cd poc4_model_download
python test_async_ui.py     # Tests UI responsiveness
python test_resume.py
python test_permissions.py
```

---

## Success Criteria

| PoC | Must Pass | Fallback if Failed |
|-----|-----------|-------------------|
| 1 | Custom QSS renders correctly with PySide6 | Use standard Qt theme |
| 2 | Speaker diarization <50ms latency | Delay speaker ID to V2 |
| 3 | Models can coexist | Separate applications |
| 4 | Async download, UI responsive | Manual model download |

---

## Review Checklist (End of Week 0)

Before PoC review meeting, ensure:

- [ ] All 4 PoC directories have `results.md`
- [ ] Each `results.md` contains:
  - Test methodology
  - Benchmarks/numbers
  - Issues encountered
  - Go/No-Go recommendation
- [ ] No files in `../src/` were modified
- [ ] Demo ready for review meeting

---

## Timeline

| Day | PoC | Focus |
|-----|-----|-------|
| 1-2 | PoC 1 | Custom QSS theme development |
| 3-4 | PoC 2 | Speaker diarization with real audio |
| 5 | PoC 3 | Data model coexistence + macOS test |
| 6 | PoC 4 | Async download & UI responsiveness |
| 7 | Review | Compile results, make go/no-go decisions |

---

## License Note

**PySide6** is used throughout (LGPL/commercial-friendly).  
**PyQt-Fluent-Widgets is NOT used** due to GPL licensing restrictions.

---

## Contact

Questions about PoC? Refer to `../docs/ROADMAP.md` Section "Proof of Concept (PoC)"
