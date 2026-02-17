"""
Setup script for Voice Translation Application
Supports building cross-platform executables
"""

import sys
import os
from setuptools import setup, find_packages

# Application metadata
APP_NAME = "VoiceTranslate"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Real-time Voice Translation Application"

# Determine platform
if sys.platform == 'darwin':
    PLATFORM = 'macos'
    from platform import machine
    ARCH = machine()
elif sys.platform == 'win32':
    PLATFORM = 'windows'
    ARCH = 'x86_64'
else:
    PLATFORM = 'unknown'
    ARCH = 'unknown'


def get_data_files():
    """Get platform-specific data files"""
    data_files = []
    
    if PLATFORM == 'macos':
        data_files.append(
            ('.', ['config/entitlements.plist'])
        )
    
    return data_files


def get_options():
    """Get py2app options for macOS"""
    if PLATFORM != 'macos':
        return {}
    
    return {
        'py2app': {
            'argv_emulation': True,
            'iconfile': 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
            'plist': {
                'CFBundleName': APP_NAME,
                'CFBundleDisplayName': APP_NAME,
                'CFBundleVersion': APP_VERSION,
                'CFBundleShortVersionString': APP_VERSION,
                'LSMinimumSystemVersion': '11.0',
                'NSHighResolutionCapable': True,
                'NSMicrophoneUsageDescription': 
                    'VoiceTranslate needs access to your microphone to capture audio for translation.',
                'NSSystemAdministrationUsageDescription': 
                    'VoiceTranslate may need system access for audio capture.',
            },
            'packages': [
                'torch',
                'torchaudio',
                'transformers',
                'whisper',
                'sounddevice',
                'librosa',
            ],
            'includes': [
                'numpy',
                'scipy',
                'soundfile',
                'pkg_resources',
            ],
            'excludes': [
                'matplotlib',
                'tkinter',
                'PyQt5',
                'PyQt6',
                'unittest',
                'pydoc',
            ],
            'resources': [
                'config',
                'models',
                'assets',
            ],
        }
    }


# Read requirements
def read_requirements():
    """Read requirements based on platform"""
    if PLATFORM == 'macos':
        if ARCH == 'arm64':
            req_file = 'requirements-macos-arm64.txt'
        else:
            req_file = 'requirements.txt'
    elif PLATFORM == 'windows':
        req_file = 'requirements-windows.txt'
    else:
        req_file = 'requirements.txt'
    
    try:
        with open(req_file, 'r') as f:
            return [line.strip() for line in f 
                    if line.strip() and not line.startswith('#') and not line.startswith('-')]
    except FileNotFoundError:
        return []


setup(
    name=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    author='Your Company',
    author_email='your@email.com',
    url='https://github.com/yourcompany/voice-translate',
    
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    
    install_requires=read_requirements(),
    
    python_requires='>=3.9',
    
    entry_points={
        'console_scripts': [
            'voice-translate=main:main',
        ],
        'gui_scripts': [
            'voice-translate-gui=main:main',
        ],
    },
    
    data_files=get_data_files(),
    
    options=get_options(),
    
    setup_requires=['py2app'] if PLATFORM == 'macos' else [],
    app=['src/main.py'] if PLATFORM == 'macos' else [],
    
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Multimedia :: Sound/Audio :: Speech',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    
    keywords='voice translation speech recognition whisper ai ml',
    
    project_urls={
        'Bug Reports': 'https://github.com/yourcompany/voice-translate/issues',
        'Source': 'https://github.com/yourcompany/voice-translate',
        'Documentation': 'https://github.com/yourcompany/voice-translate/docs',
    },
)
