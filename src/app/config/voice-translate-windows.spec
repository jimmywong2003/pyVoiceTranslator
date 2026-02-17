# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# PyInstaller Spec for Windows 10/11
# =============================================================================
# Build command:
#   pyinstaller voice-translate-windows.spec
#
# Code signing (optional but recommended):
#   signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 dist/VoiceTranslate.exe
#
# Create installer with Inno Setup or WiX
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
COMPANY_NAME = "Your Company"
COPYRIGHT = "Copyright (C) 2024"

# Analysis configuration
a = Analysis(
    ['../src/main.py'],  # Entry point
    pathex=[
        '../src',
        '../',
    ],
    binaries=[
        # Include PyAudio DLLs
        ('C:/Windows/System32/PortAudio.dll', '.'),
        # CUDA DLLs (if using CUDA)
        # ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.8/bin/*.dll', 'lib'),
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
        'torch.cuda',
        'torch.cuda.amp',
        
        # Transformers
        'transformers',
        'transformers.models.whisper',
        'transformers.models.whisper.modeling_whisper',
        'transformers.models.whisper.tokenization_whisper',
        
        # Audio
        'pyaudio',
        'soundfile',
        'librosa',
        'librosa.core',
        'librosa.feature',
        
        # ML
        'numpy',
        'scipy',
        'sklearn',
        
        # Windows specific
        'pywin32',
        'win32api',
        'win32con',
        'win32gui',
        'comtypes',
        'comtypes.client',
        
        # Utilities
        'pkg_resources',
        'pkg_resources.py2_warn',
        
        # Whisper
        'whisper',
        'whisper.model',
        'whisper.tokenizer',
        'whisper.audio',
        'whisper.transcribe',
        
        # VAD
        'silero_vad',
        'webrtcvad',
        
        # ONNX Runtime (optional)
        'onnxruntime',
        'onnxruntime.capi',
        
        # DirectML (optional)
        'torch_directml',
    ],
    hookspath=[
        '../config/hooks',  # Custom hooks directory
    ],
    hooksconfig={
        # PyInstaller hooks configuration
        'pytorch': {
            'include_cuda': True,  # Include CUDA libraries
        },
    },
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
        'distutils',
        'setuptools',
        'pip',
        'wheel',
        # Linux/macOS specific
        'posixpath',
        'pwd',
        'grp',
        'termios',
        'resource',
        'nis',
        'macpath',
        'ossaudiodev',
        'spwd',
        'fcntl',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate binaries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows executable configuration
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
    strip=False,  # Don't strip on Windows (causes issues)
    upx=True,     # UPX compression
    upx_exclude=[
        'vcruntime140.dll',  # Don't compress MSVC runtime
        'python*.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # GUI application (use True for debug)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # Use default architecture
    codesign_identity=None,
    entitlements_file=None,
    # Windows-specific
    icon='../assets/icon.ico',  # Windows icon file
    version='../config/version_info.txt',  # Version info file
    uac_admin=False,  # Don't require admin privileges
    uac_uiaccess=False,
)

# Windows-specific: Create a single-file executable
# For a folder-based distribution, use COLLECT instead:
#
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     name=APP_NAME
# )
