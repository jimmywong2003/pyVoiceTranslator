# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# PyInstaller Spec for macOS (Universal2 - Intel + Apple Silicon)
# =============================================================================
# Build commands:
#   Intel only:    pyinstaller voice-translate-macos.spec --target-arch x86_64
#   Apple Silicon: pyinstaller voice-translate-macos.spec --target-arch arm64
#   Universal2:    pyinstaller voice-translate-macos.spec --target-arch universal2
#
# Code signing (required for distribution):
#   codesign --deep --force --verify --verbose --sign "Developer ID" dist/VoiceTranslate.app
# =============================================================================

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(SPECPATH, '..', 'src')))

block_cipher = None

# Application metadata
APP_NAME = "VoiceTranslate"
APP_VERSION = "1.0.0"
BUNDLE_IDENTIFIER = "com.yourcompany.voicetranslate"

# Determine architecture
import platform
machine = platform.machine()
is_arm64 = machine == 'arm64'

# Analysis configuration
a = Analysis(
    ['../src/main.py'],  # Entry point
    pathex=[
        '../src',
        '../',
    ],
    binaries=[
        # Include PortAudio library
        ('/opt/homebrew/lib/libportaudio.dylib', '.') if is_arm64 else ('/usr/local/lib/libportaudio.dylib', '.'),
    ],
    datas=[
        # Include model files, configs, etc.
        ('../config', 'config'),
        ('../models', 'models'),
        ('../assets', 'assets'),
    ],
    hiddenimports=[
        # PyTorch
        'torch',
        'torchaudio',
        'torchvision',
        'torch._C',
        'torch._dynamo',
        'torch._inductor',
        
        # Transformers
        'transformers',
        'transformers.models.whisper',
        'transformers.models.whisper.modeling_whisper',
        'transformers.models.whisper.tokenization_whisper',
        
        # Audio
        'sounddevice',
        'soundfile',
        'librosa',
        'librosa.core',
        'librosa.feature',
        
        # ML
        'numpy',
        'scipy',
        'sklearn',
        
        # Utilities
        'pkg_resources',
        'pkg_resources.py2_warn',
        
        # Platform-specific
        'objc',
        'CoreFoundation',
        'CoreAudio',
        
        # Whisper
        'whisper',
        'whisper.model',
        'whisper.tokenizer',
        'whisper.audio',
        
        # VAD
        'silero_vad',
        'webrtcvad',
    ],
    hookspath=[
        '../config/hooks',  # Custom hooks directory
    ],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'unittest',
        'pydoc',
        'pdb',
        'doctest',
        'email',
        'http',
        'xml',
        'xmlrpc',
        'html',
        'test',
        '_testcapi',
        'multiprocessing.popen_spawn_win32',  # Windows only
        'multiprocessing.popen_forkserver',   # Linux only
        'distutils',
        'setuptools',
        'pip',
        'wheel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate binaries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# macOS-specific executable configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols for smaller binary
    upx=True,    # UPX compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS argv emulation
    target_arch='universal2',  # Build for both Intel and Apple Silicon
    codesign_identity=None,  # Set to your Developer ID for distribution
    entitlements_file='../config/entitlements.plist',
)

# macOS App Bundle configuration
app = BUNDLE(
    exe,
    name=f'{APP_NAME}.app',
    icon='../assets/icon.icns',  # macOS icon file
    bundle_identifier=BUNDLE_IDENTIFIER,
    version=APP_VERSION,
    info_plist={
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleExecutable': APP_NAME,
        'CFBundleIdentifier': BUNDLE_IDENTIFIER,
        'CFBundleVersion': APP_VERSION,
        'CFBundleShortVersionString': APP_VERSION,
        'LSMinimumSystemVersion': '11.0',  # macOS Big Sur minimum
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'VoiceTranslate needs access to your microphone to capture audio for translation.',
        'NSSystemAdministrationUsageDescription': 'VoiceTranslate may need system access for audio capture.',
        'LSBackgroundOnly': False,
        'LSUIElement': False,
        # Apple Silicon specific
        'LSRequiresNativeExecution': True,
    },
)
