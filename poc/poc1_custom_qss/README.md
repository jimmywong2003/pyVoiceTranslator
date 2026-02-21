# PoC 1: Custom QSS Theme

**Objective:** Develop modern UI theme using PySide6 + Custom QSS (license-safe)

**Why Not PyQt-Fluent-Widgets?**
- PyQt-Fluent-Widgets requires PyQt6 which is GPL licensed
- GPL requires open-sourcing derivative works (commercial risk)
- PySide6 is LGPL - safe for commercial/proprietary use

---

## Tests

1. **test_custom_theme.py** - Basic QSS theme application
2. **test_components.py** - Modern components (cards, buttons)
3. **test_threading.py** - Audio threading compatibility

---

## Design Goals

Replicate Fluent Design using QSS:
- Dark theme (#1E1E2E background)
- Accent color (#6C5DD3 purple)
- Rounded corners (12px radius)
- Card-style containers
- Smooth hover/pressed states

---

## Success Criteria

- [ ] Modern look achieved with QSS
- [ ] No GPL dependencies
- [ ] Performance acceptable
