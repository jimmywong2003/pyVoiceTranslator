"""
Cross-Platform Utilities and Detection
Provides platform detection, conditional imports, and compatibility helpers
"""

import platform
import sys
import os
import subprocess
import logging
from typing import Optional, Dict, Any, Callable, List
from functools import wraps
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """Platform type enumeration"""
    MACOS_APPLE_SILICON = "macos_apple_silicon"
    MACOS_INTEL = "macos_intel"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """Comprehensive platform information"""
    platform_type: PlatformType
    system: str
    machine: str
    processor: str
    architecture: str
    python_version: str
    python_implementation: str
    is_64bit: bool
    is_conda: bool
    is_virtualenv: bool
    
    @property
    def is_macos(self) -> bool:
        return self.platform_type in [PlatformType.MACOS_APPLE_SILICON, PlatformType.MACOS_INTEL]
    
    @property
    def is_windows(self) -> bool:
        return self.platform_type == PlatformType.WINDOWS
    
    @property
    def is_apple_silicon(self) -> bool:
        return self.platform_type == PlatformType.MACOS_APPLE_SILICON


# =============================================================================
# Platform Detection
# =============================================================================

def detect_platform() -> PlatformType:
    """Detect the current platform type"""
    system = platform.system()
    machine = platform.machine().lower()
    
    if system == 'Darwin':
        if 'arm' in machine or 'aarch64' in machine:
            return PlatformType.MACOS_APPLE_SILICON
        return PlatformType.MACOS_INTEL
    elif system == 'Windows':
        return PlatformType.WINDOWS
    elif system == 'Linux':
        return PlatformType.LINUX
    return PlatformType.UNKNOWN


def get_platform_info() -> PlatformInfo:
    """Get comprehensive platform information"""
    platform_type = detect_platform()
    
    # Detect conda environment
    is_conda = (
        'CONDA_DEFAULT_ENV' in os.environ or
        'conda' in sys.prefix.lower() or
        os.path.exists(os.path.join(sys.prefix, 'conda-meta'))
    )
    
    # Detect virtualenv
    is_virtualenv = (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
        os.path.exists(os.path.join(sys.prefix, 'pyvenv.cfg'))
    )
    
    return PlatformInfo(
        platform_type=platform_type,
        system=platform.system(),
        machine=platform.machine(),
        processor=platform.processor(),
        architecture=platform.architecture()[0],
        python_version=platform.python_version(),
        python_implementation=platform.python_implementation(),
        is_64bit=platform.architecture()[0] == '64bit',
        is_conda=is_conda,
        is_virtualenv=is_virtualenv
    )


# =============================================================================
# Conditional Imports and Decorators
# =============================================================================

def platform_import(module_name: str, fallback=None):
    """Conditionally import a module based on platform"""
    try:
        module = __import__(module_name)
        return module
    except ImportError:
        logger.warning(f"Could not import {module_name}")
        return fallback


def macos_only(func: Callable) -> Callable:
    """Decorator to only run function on macOS"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not detect_platform().value.startswith('macos'):
            logger.debug(f"Skipping {func.__name__} - macOS only")
            return None
        return func(*args, **kwargs)
    return wrapper


def windows_only(func: Callable) -> Callable:
    """Decorator to only run function on Windows"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if detect_platform() != PlatformType.WINDOWS:
            logger.debug(f"Skipping {func.__name__} - Windows only")
            return None
        return func(*args, **kwargs)
    return wrapper


def apple_silicon_only(func: Callable) -> Callable:
    """Decorator to only run function on Apple Silicon"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if detect_platform() != PlatformType.MACOS_APPLE_SILICON:
            logger.debug(f"Skipping {func.__name__} - Apple Silicon only")
            return None
        return func(*args, **kwargs)
    return wrapper


def not_windows(func: Callable) -> Callable:
    """Decorator to skip function on Windows"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if detect_platform() == PlatformType.WINDOWS:
            logger.debug(f"Skipping {func.__name__} - not supported on Windows")
            return None
        return func(*args, **kwargs)
    return wrapper


# =============================================================================
# Platform-Specific Path Handling
# =============================================================================

class PlatformPaths:
    """Cross-platform path management"""
    
    def __init__(self, app_name: str = "VoiceTranslate"):
        self.app_name = app_name
        self.platform = detect_platform()
    
    def get_config_dir(self) -> str:
        """Get platform-appropriate config directory"""
        if self.platform.value.startswith('macos'):
            return os.path.expanduser(f'~/Library/Application Support/{self.app_name}')
        elif self.platform == PlatformType.WINDOWS:
            return os.path.join(os.environ.get('APPDATA', ''), self.app_name)
        else:
            return os.path.expanduser(f'~/.config/{self.app_name}')
    
    def get_cache_dir(self) -> str:
        """Get platform-appropriate cache directory"""
        if self.platform.value.startswith('macos'):
            return os.path.expanduser(f'~/Library/Caches/{self.app_name}')
        elif self.platform == PlatformType.WINDOWS:
            return os.path.join(os.environ.get('LOCALAPPDATA', ''), self.app_name, 'Cache')
        else:
            return os.path.expanduser(f'~/.cache/{self.app_name}')
    
    def get_log_dir(self) -> str:
        """Get platform-appropriate log directory"""
        if self.platform.value.startswith('macos'):
            return os.path.expanduser(f'~/Library/Logs/{self.app_name}')
        elif self.platform == PlatformType.WINDOWS:
            return os.path.join(os.environ.get('LOCALAPPDATA', ''), self.app_name, 'Logs')
        else:
            return os.path.expanduser(f'~/.local/share/{self.app_name}/logs')
    
    def get_models_dir(self) -> str:
        """Get platform-appropriate models directory"""
        base_dir = self.get_config_dir()
        return os.path.join(base_dir, 'models')
    
    def ensure_dirs(self):
        """Ensure all necessary directories exist"""
        for dir_path in [
            self.get_config_dir(),
            self.get_cache_dir(),
            self.get_log_dir(),
            self.get_models_dir()
        ]:
            os.makedirs(dir_path, exist_ok=True)


# =============================================================================
# Platform-Specific Audio Helpers
# =============================================================================

class AudioPlatformHelper:
    """Platform-specific audio helpers"""
    
    def __init__(self):
        self.platform = detect_platform()
    
    def get_recommended_sample_rate(self) -> int:
        """Get recommended sample rate for the platform"""
        # Most platforms work well with 16kHz for speech
        return 16000
    
    def get_recommended_buffer_size(self) -> int:
        """Get recommended audio buffer size"""
        if self.platform == PlatformType.MACOS_APPLE_SILICON:
            return 512  # Lower latency on Apple Silicon
        elif self.platform == PlatformType.WINDOWS:
            return 1024  # Standard for Windows
        return 1024
    
    def check_audio_permissions(self) -> bool:
        """Check if audio permissions are granted"""
        if self.platform.value.startswith('macos'):
            return self._check_macos_audio_permissions()
        elif self.platform == PlatformType.WINDOWS:
            return self._check_windows_audio_permissions()
        return True
    
    @macos_only
    def _check_macos_audio_permissions(self) -> bool:
        """Check macOS microphone permissions"""
        try:
            # Try to import AVFoundation for permission checking
            from AVFoundation import AVAudioSession
            # Note: Actual permission check requires more implementation
            return True
        except ImportError:
            # AVFoundation not available, assume granted
            return True
    
    @windows_only
    def _check_windows_audio_permissions(self) -> bool:
        """Check Windows microphone permissions"""
        try:
            import winreg
            # Check privacy settings
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
                value, _ = winreg.QueryValueEx(key, "Value")
                winreg.CloseKey(key)
                return value == "Allow"
            except WindowsError:
                return True  # Assume granted if can't check
        except ImportError:
            return True


# =============================================================================
# Dependency Checking
# =============================================================================

class DependencyChecker:
    """Check platform-specific dependencies"""
    
    def __init__(self):
        self.platform = detect_platform()
        self.missing = []
        self.warnings = []
    
    def check_all(self) -> Dict[str, Any]:
        """Run all dependency checks"""
        results = {
            'python_version': self._check_python_version(),
            'pytorch': self._check_pytorch(),
            'audio': self._check_audio_deps(),
            'ml': self._check_ml_deps(),
            'platform_specific': self._check_platform_deps(),
            'missing': self.missing,
            'warnings': self.warnings,
            'all_ok': len(self.missing) == 0
        }
        return results
    
    def _check_python_version(self) -> bool:
        """Check Python version"""
        version = sys.version_info
        if version < (3, 9):
            self.missing.append(f"Python 3.9+ required, found {version.major}.{version.minor}")
            return False
        return True
    
    def _check_pytorch(self) -> bool:
        """Check PyTorch installation"""
        try:
            import torch
            logger.info(f"PyTorch {torch.__version__} installed")
            
            if self.platform == PlatformType.MACOS_APPLE_SILICON:
                if not torch.backends.mps.is_available():
                    self.warnings.append("MPS not available - performance will be reduced")
            elif self.platform == PlatformType.WINDOWS:
                if not torch.cuda.is_available():
                    self.warnings.append("CUDA not available - will use CPU")
            return True
        except ImportError:
            self.missing.append("PyTorch not installed")
            return False
    
    def _check_audio_deps(self) -> bool:
        """Check audio dependencies"""
        ok = True
        
        # Check numpy
        try:
            import numpy
        except ImportError:
            self.missing.append("numpy not installed")
            ok = False
        
        # Check platform-specific audio
        if self.platform.value.startswith('macos'):
            try:
                import sounddevice
            except ImportError:
                self.missing.append("sounddevice not installed (required for macOS)")
                ok = False
        elif self.platform == PlatformType.WINDOWS:
            try:
                import pyaudio
            except ImportError:
                self.missing.append("pyaudio not installed (required for Windows)")
                ok = False
        
        return ok
    
    def _check_ml_deps(self) -> bool:
        """Check ML dependencies"""
        ok = True
        
        try:
            import transformers
        except ImportError:
            self.missing.append("transformers not installed")
            ok = False
        
        try:
            import whisper
        except ImportError:
            self.missing.append("openai-whisper not installed")
            ok = False
        
        return ok
    
    def _check_platform_deps(self) -> bool:
        """Check platform-specific dependencies"""
        ok = True
        
        if self.platform == PlatformType.MACOS_APPLE_SILICON:
            # Check for ARM64 wheels
            import platform as pf
            if pf.machine() != 'arm64':
                self.warnings.append("Running under Rosetta - install ARM64 Python for better performance")
        
        elif self.platform == PlatformType.WINDOWS:
            # Check for Visual C++ Redistributables
            pass  # Would need to check registry
        
        return ok


# =============================================================================
# Environment Setup Helpers
# =============================================================================

def setup_environment():
    """Setup environment variables for optimal performance"""
    platform_type = detect_platform()
    
    # Common settings
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    if platform_type == PlatformType.MACOS_APPLE_SILICON:
        # Apple Silicon optimizations
        os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
        os.environ['OMP_NUM_THREADS'] = str(os.cpu_count())
        os.environ['MKL_NUM_THREADS'] = str(os.cpu_count())
        
    elif platform_type == PlatformType.WINDOWS:
        # Windows optimizations
        os.environ['OMP_NUM_THREADS'] = str(os.cpu_count())
        os.environ['MKL_NUM_THREADS'] = str(os.cpu_count())
        
        # PyTorch CUDA settings
        os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
        os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'


def get_optimal_thread_count() -> int:
    """Get optimal thread count for the platform"""
    cpu_count = os.cpu_count() or 4
    platform_type = detect_platform()
    
    if platform_type == PlatformType.MACOS_APPLE_SILICON:
        # Apple Silicon: Use performance cores
        # M1 Pro: 8 performance cores, 2 efficiency cores
        return min(cpu_count - 2, 8)  # Leave some cores free
    
    return max(1, cpu_count - 1)


# =============================================================================
# Utility Functions
# =============================================================================

def run_platform_command(command: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command with platform-specific handling"""
    platform_type = detect_platform()
    
    # On Windows, use shell=True for some commands
    if platform_type == PlatformType.WINDOWS and kwargs.get('shell') is None:
        # Check if command needs shell
        if any('|' in str(c) or '>' in str(c) for c in command):
            kwargs['shell'] = True
    
    return subprocess.run(command, **kwargs)


def get_executable_extension() -> str:
    """Get platform-appropriate executable extension"""
    return '.exe' if detect_platform() == PlatformType.WINDOWS else ''


def get_library_extension() -> str:
    """Get platform-appropriate library extension"""
    platform_type = detect_platform()
    if platform_type == PlatformType.WINDOWS:
        return '.dll'
    elif platform_type.value.startswith('macos'):
        return '.dylib'
    return '.so'


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Get platform info
    info = get_platform_info()
    print("Platform Information:")
    print(f"  Type: {info.platform_type.value}")
    print(f"  System: {info.system}")
    print(f"  Machine: {info.machine}")
    print(f"  Python: {info.python_version}")
    print(f"  Is Conda: {info.is_conda}")
    print(f"  Is Apple Silicon: {info.is_apple_silicon}")
    
    # Check dependencies
    print("\nDependency Check:")
    checker = DependencyChecker()
    results = checker.check_all()
    print(f"  All OK: {results['all_ok']}")
    if results['missing']:
        print(f"  Missing: {results['missing']}")
    if results['warnings']:
        print(f"  Warnings: {results['warnings']}")
    
    # Platform paths
    print("\nPlatform Paths:")
    paths = PlatformPaths()
    print(f"  Config: {paths.get_config_dir()}")
    print(f"  Cache: {paths.get_cache_dir()}")
    print(f"  Models: {paths.get_models_dir()}")
    
    # Audio helper
    print("\nAudio Settings:")
    audio = AudioPlatformHelper()
    print(f"  Sample Rate: {audio.get_recommended_sample_rate()}")
    print(f"  Buffer Size: {audio.get_recommended_buffer_size()}")
