# Contributing Guidelines

## VoiceTranslate Pro - Contribution Guide

Thank you for your interest in contributing to VoiceTranslate Pro! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contribution Workflow](#contribution-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Release Process](#release-process)
10. [Community](#community)

---

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at conduct@voicetranslate.pro.

---

## Getting Started

### Ways to Contribute

1. **Report Bugs**: Submit detailed bug reports
2. **Suggest Features**: Propose new features or improvements
3. **Write Code**: Implement bug fixes or new features
4. **Improve Documentation**: Fix typos, add examples, clarify instructions
5. **Review Code**: Review pull requests from other contributors
6. **Help Others**: Answer questions in discussions and issues
7. **Translate**: Help translate the application and documentation
8. **Test**: Test pre-release versions and report issues

### Before You Start

1. **Check existing issues**: Look for existing issues related to your contribution
2. **Create an issue**: For significant changes, create an issue first to discuss
3. **Read documentation**: Familiarize yourself with the project structure
4. **Join discussions**: Participate in community discussions

---

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Virtual environment tool (venv, conda, or virtualenv)
- Code editor (VS Code, PyCharm, etc.)

### Step-by-Step Setup

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/voicetranslate-pro.git
cd voicetranslate-pro

# Add upstream remote
git remote add upstream https://github.com/original/voicetranslate-pro.git
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### 3. Install Dependencies

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e ".[dev]"
```

#### 4. Set Up Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

#### 5. Verify Setup

```bash
# Run tests
pytest tests/unit/ -v

# Run the application
python -m voicetranslate_pro --version
```

### IDE Configuration

#### VS Code

Recommended extensions:
- Python
- Pylance
- autoDocstring
- GitLens
- Error Lens

Settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
```

#### PyCharm

1. Set project interpreter to virtual environment
2. Enable pytest as test runner
3. Configure code style to match project standards
4. Enable auto-formatting on save

---

## Contribution Workflow

### 1. Create a Branch

```bash
# Fetch latest changes
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

**Branch Naming Conventions:**

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/add-dark-mode` |
| Bug Fix | `fix/issue-description` | `fix/memory-leak-in-asr` |
| Documentation | `docs/description` | `docs/update-api-reference` |
| Refactoring | `refactor/description` | `refactor/simplify-pipeline` |
| Performance | `perf/description` | `perf/reduce-latency` |

### 2. Make Changes

- Write clean, readable code
- Follow coding standards (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with conventional message
git commit -m "feat: add dark mode support

- Add theme toggle in settings
- Implement dark color scheme
- Save preference to config

Closes #123"
```

**Commit Message Format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

**Examples:**

```
feat(asr): add support for Whisper large-v3 model

fix(translation): handle empty text input gracefully

docs(api): update WebSocket API examples

refactor(gui): simplify main window initialization

test(pipeline): add integration tests for video mode
```

### 4. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

#### Code Formatting

```python
# Use Black for formatting
# Line length: 88 characters
# Use single quotes for strings

# Good
name = 'John'
full_name = f'{first_name} {last_name}'

# Bad
name = "John"
full_name = first_name + " " + last_name
```

#### Imports

```python
# Order: stdlib, third-party, local
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import torch

from voicetranslate_pro.asr import WhisperASR
from voicetranslate_pro.utils import load_config
```

#### Type Hints

```python
from typing import Optional, Dict, List

def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    context: Optional[str] = None
) -> Dict[str, str]:
    """Translate text from source to target language.
    
    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        context: Optional context for better translation
        
    Returns:
        Dictionary containing translation and metadata
        
    Raises:
        ValueError: If text is empty
        UnsupportedLanguageError: If language is not supported
    """
    if not text:
        raise ValueError("Text cannot be empty")
    
    # Implementation
    return {"translation": translated_text, "confidence": 0.95}
```

#### Docstrings

Use Google-style docstrings:

```python
def process_audio(
    audio: np.ndarray,
    sample_rate: int = 16000,
    apply_noise_reduction: bool = True
) -> np.ndarray:
    """Process audio for speech recognition.
    
    Applies preprocessing steps including normalization,
    resampling, and optional noise reduction.
    
    Args:
        audio: Input audio array
        sample_rate: Target sample rate in Hz
        apply_noise_reduction: Whether to apply noise reduction
        
    Returns:
        Processed audio array
        
    Example:
        >>> audio = load_audio('input.wav')
        >>> processed = process_audio(audio, sample_rate=16000)
        >>> assert processed.shape == audio.shape
    """
    pass
```

### Linting and Formatting

```bash
# Run all checks
make lint

# Or individually:
# Format with Black
black voicetranslate_pro/ tests/

# Lint with flake8
flake8 voicetranslate_pro/ tests/

# Type check with mypy
mypy voicetranslate_pro/

# Sort imports
isort voicetranslate_pro/ tests/
```

### Configuration Files

```ini
# setup.cfg
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv

[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

---

## Testing Guidelines

### Test Structure

```python
# tests/unit/test_module.py
import pytest
from voicetranslate_pro.module import Module

class TestModule:
    """Test cases for Module."""
    
    @pytest.fixture
    def module(self):
        """Create module instance for tests."""
        return Module()
    
    def test_initialization(self, module):
        """Test module initializes correctly."""
        assert module is not None
    
    def test_functionality(self, module):
        """Test main functionality."""
        result = module.process("input")
        assert result == "expected_output"
    
    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_multiple_cases(self, module, input, expected):
        """Test with multiple inputs."""
        assert module.process(input) == expected
```

### Test Coverage

- Minimum 80% code coverage for new code
- 100% coverage for critical paths
- Use `pytest-cov` for coverage reporting

```bash
# Run tests with coverage
pytest --cov=voicetranslate_pro --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_asr.py -v

# Run specific test
pytest tests/unit/test_asr.py::TestWhisperASR::test_transcribe -v

# Run with markers
pytest -m "slow" -v
pytest -m "not slow" -v

# Run in parallel
pytest -n auto
```

---

## Documentation

### Code Documentation

- All public functions must have docstrings
- Include type hints
- Provide usage examples
- Document exceptions

### README Updates

Update README.md when:
- Adding new features
- Changing installation process
- Modifying configuration
- Adding new dependencies

### Documentation Files

Documentation is in the `docs/` directory:

```
docs/
├── README.md              # Documentation index
├── installation.md        # Installation guide
├── user-guide.md          # User guide
├── api-reference.md       # API documentation
├── contributing.md        # This file
├── architecture.md        # Architecture documentation
├── troubleshooting.md     # Troubleshooting guide
└── changelog.md           # Change log
```

---

## Pull Request Process

### Before Submitting

1. **Run all tests**
   ```bash
   pytest
   ```

2. **Check code style**
   ```bash
   make lint
   ```

3. **Update documentation**
   - Add docstrings
   - Update relevant .md files
   - Add examples if needed

4. **Write clear commit messages**
   - Use conventional commit format
   - Reference related issues

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No new warnings

## Related Issues
Fixes #123
```

### Review Process

1. **Automated checks** must pass:
   - CI/CD pipeline
   - Code coverage
   - Linting

2. **Code review** by maintainers:
   - At least one approval required
   - Address all comments
   - Keep discussion constructive

3. **Merge** when approved:
   - Squash commits if needed
   - Use descriptive merge message

---

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist

1. Update version in `__init__.py`
2. Update `CHANGELOG.md`
3. Create release branch
4. Run full test suite
5. Build packages
6. Create GitHub release
7. Publish to PyPI
8. Update documentation

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Discord**: Real-time chat [discord.gg/voicetranslate](https://discord.gg/voicetranslate)
- **Email**: dev@voicetranslate.pro

### Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

### Becoming a Maintainer

Active contributors may be invited to become maintainers:
- Consistent quality contributions
- Helpful code reviews
- Community involvement
- Understanding of project goals

---

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search closed issues
3. Ask in GitHub Discussions
4. Join our Discord server
5. Email dev@voicetranslate.pro

Thank you for contributing to VoiceTranslate Pro! 🎉
