# Project Structure

This document outlines the organization of the VoiceTranslate Pro repository.

## Directory Layout

```
project-root/
├── assets/                 # Static assets (images, icons)
├── cli/                    # Command-line interface tools
├── config/                 # Configuration files
├── docs/                   # Documentation
│   ├── architecture/       # System architecture docs
│   ├── design/             # Design documents
│   ├── guides/             # User guides (JAPANESE_TRANSLATION_GUIDE, etc.)
│   ├── meta/               # Project meta docs (AGENTS.md, FINAL_IMPLEMENTATION)
│   ├── poc/                # Proof of concepts
│   ├── reference/          # API reference
│   ├── releases/           # Release notes
│   └── sessions/           # Session logs
├── monitoring/             # Docker monitoring config
├── scripts/                # Utility scripts
│   └── run/                # Run scripts (interview mode, etc.)
├── src/                    # Source code
│   ├── core/               # Core translation system
│   ├── gui/                # GUI application
│   └── app/                # Standalone app components
├── tests/                  # Test suite
│   └── manual/             # Manual test scripts
├── README.md               # Main project readme
├── STATUS.md               # Development status
├── PROJECT_STRUCTURE.md    # This file
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Docker image
└── requirements-*.txt      # Python dependencies
```

## Key Files

### Root Level
- `README.md` - Project overview and quick start
- `STATUS.md` - Current development status
- `PROJECT_STRUCTURE.md` - This file

### Documentation (`docs/`)
- `docs/meta/AGENTS.md` - Agent documentation for AI coding assistants
- `docs/meta/FINAL_IMPLEMENTATION_SUMMARY.md` - Implementation summary
- `docs/guides/` - User guides (Japanese translation, sentence mode, etc.)
- `docs/ROADMAP.md` - Development roadmap
- `docs/poc/` - Proof of concept experiments

### Scripts (`scripts/`)
- `scripts/run/` - Launcher scripts for different modes
  - `run_interview_mode.sh`
  - `run_japanese_to_english.sh`
  - `run_sentence_mode.sh`
  - `run_documentary_mode.sh`
  - `run_with_mic.sh`
- `scripts/build_portable.sh` - PyInstaller build script
- `scripts/setup_environment.py` - Environment setup

### Source Code (`src/`)
- `src/core/` - Core translation engine
  - `asr/` - Automatic Speech Recognition
  - `translation/` - Translation engines
  - `pipeline/` - Processing pipelines
  - `utils/` - Utilities (debug logger, model manager, etc.)
- `src/gui/` - GUI application
  - `meeting/` - Meeting mode components (Phase 4)
- `src/app/` - Standalone app components

### Tests (`tests/`)
- `tests/manual/` - Manual test scripts
- `tests/test_*.py` - Unit tests

## Quick Navigation

| What you need | Where to find it |
|---------------|------------------|
| User guides | `docs/guides/` |
| Architecture docs | `docs/architecture/` |
| Run scripts | `scripts/run/` |
| Source code | `src/` |
| Manual tests | `tests/manual/` |
| Session logs | `docs/sessions/` |
| Proof of concepts | `docs/poc/` |
