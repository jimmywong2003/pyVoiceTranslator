#!/usr/bin/env python3
"""
VoiceTranslate Pro - Environment Setup Script
==============================================

This script provides a step-by-step checklist and automated setup for the
VoiceTranslate Pro environment.

Prerequisites:
- Python 3.9+ installed
- Virtual environment already created and activated
- pip is up to date

Usage:
    python setup_environment.py [--skip-checks] [--install-all]

Options:
    --skip-checks    Skip environment validation checks
    --install-all    Automatically install all dependencies
"""

import argparse
import os
import platform
import subprocess
import sys
from enum import Enum
from typing import Callable, List, Optional, Tuple


class CheckStatus(Enum):
    """Status of a setup check."""
    PENDING = "⏳"
    IN_PROGRESS = "🔄"
    PASSED = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    SKIPPED = "⏭️"


class SetupStep:
    """Represents a single setup step with checkable status."""
    
    def __init__(
        self,
        number: int,
        title: str,
        description: str,
        check_func: Optional[Callable[[], Tuple[bool, str]]] = None,
        install_func: Optional[Callable[[], Tuple[bool, str]]] = None,
        is_optional: bool = False
    ):
        self.number = number
        self.title = title
        self.description = description
        self.check_func = check_func
        self.install_func = install_func
        self.is_optional = is_optional
        self.status = CheckStatus.PENDING
        self.message = ""
    
    def check(self) -> bool:
        """Run the check function and update status."""
        if self.check_func is None:
            self.status = CheckStatus.SKIPPED
            return True
        
        self.status = CheckStatus.IN_PROGRESS
        try:
            passed, message = self.check_func()
            self.status = CheckStatus.PASSED if passed else CheckStatus.FAILED
            self.message = message
            return passed
        except Exception as e:
            self.status = CheckStatus.FAILED
            self.message = f"Error: {e}"
            return False
    
    def install(self) -> bool:
        """Run the install function and update status."""
        if self.install_func is None:
            return False
        
        self.status = CheckStatus.IN_PROGRESS
        try:
            passed, message = self.install_func()
            self.status = CheckStatus.PASSED if passed else CheckStatus.FAILED
            self.message = message
            return passed
        except Exception as e:
            self.status = CheckStatus.FAILED
            self.message = f"Error: {e}"
            return False
    
    def display(self, width: int = 70):
        """Display the step with its current status."""
        optional_tag = " [OPTIONAL]" if self.is_optional else ""
        print(f"\n{'=' * width}")
        print(f"Step {self.number}: {self.title}{optional_tag}")
        print(f"{'-' * width}")
        print(f"{self.status.value} {self.description}")
        if self.message:
            print(f"   └─> {self.message}")


class EnvironmentSetup:
    """Main setup orchestrator."""
    
    def __init__(self):
        self.platform = platform.system()
        self.machine = platform.machine()
        self.python_version = sys.version_info
        self.steps: List[SetupStep] = []
        self._setup_steps()
    
    def _setup_steps(self):
        """Define all setup steps."""
        self.steps = [
            # Step 1: Python Version Check
            SetupStep(
                number=1,
                title="Python Version Validation",
                description="Check Python 3.9+ is installed",
                check_func=self._check_python_version
            ),
            
            # Step 2: Virtual Environment Check
            SetupStep(
                number=2,
                title="Virtual Environment",
                description="Verify running in virtual environment",
                check_func=self._check_virtual_env
            ),
            
            # Step 3: pip Update
            SetupStep(
                number=3,
                title="Package Manager (pip)",
                description="Ensure pip is up to date",
                check_func=self._check_pip_version,
                install_func=self._update_pip
            ),
            
            # Step 4: Core Dependencies
            SetupStep(
                number=4,
                title="Core Dependencies",
                description="Install base requirements.txt",
                check_func=self._check_core_deps,
                install_func=self._install_core_deps
            ),
            
            # Step 5: Platform-Specific Dependencies
            SetupStep(
                number=5,
                title="Platform-Specific Dependencies",
                description=f"Install {self.platform}-specific packages",
                check_func=self._check_platform_deps,
                install_func=self._install_platform_deps
            ),
            
            # Step 6: PyTorch Installation
            SetupStep(
                number=6,
                title="PyTorch Framework",
                description="Install PyTorch with platform optimizations",
                check_func=self._check_pytorch,
                install_func=self._install_pytorch
            ),
            
            # Step 7: Audio Backend
            SetupStep(
                number=7,
                title="Audio Backend",
                description="Verify PortAudio/PyAudio installation",
                check_func=self._check_audio_backend,
                install_func=self._install_audio_backend
            ),
            
            # Step 8: FFmpeg
            SetupStep(
                number=8,
                title="FFmpeg (Video Support)",
                description="Verify FFmpeg is installed",
                check_func=self._check_ffmpeg
            ),
            
            # Step 9: VAD Models
            SetupStep(
                number=9,
                title="Voice Activity Detection",
                description="Download Silero VAD model",
                check_func=self._check_vad_models,
                install_func=self._download_vad_models
            ),
            
            # Step 10: Test Imports
            SetupStep(
                number=10,
                title="Import Validation",
                description="Verify all packages can be imported",
                check_func=self._test_imports
            ),
            
            # Step 11: Run Tests (Optional)
            SetupStep(
                number=11,
                title="Run Unit Tests",
                description="Execute test suite to verify setup",
                check_func=self._check_tests,
                install_func=self._run_tests,
                is_optional=True
            ),
        ]
    
    # ==================== Check Functions ====================
    
    def _check_python_version(self) -> Tuple[bool, str]:
        """Check Python version is 3.9 or higher."""
        if self.python_version >= (3, 9):
            return True, f"Python {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro} ✓"
        return False, f"Python {self.python_version.major}.{self.python_version.minor} is too old. Need 3.9+"
    
    def _check_virtual_env(self) -> Tuple[bool, str]:
        """Check if running in a virtual environment."""
        in_venv = (
            hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
            os.environ.get('VIRTUAL_ENV') is not None
        )
        if in_venv:
            venv_path = os.environ.get('VIRTUAL_ENV', sys.prefix)
            return True, f"Active: {venv_path}"
        return False, "Not in virtual environment! Please activate it first."
    
    def _check_pip_version(self) -> Tuple[bool, str]:
        """Check pip is reasonably up to date."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True
            )
            version_line = result.stdout.strip()
            # Extract version number
            import re
            match = re.search(r'pip (\d+)\.(\d+)', version_line)
            if match:
                major, minor = int(match.group(1)), int(match.group(2))
                if major >= 23:
                    return True, version_line
                return False, f"{version_line} (recommend 23.0+)"
            return True, version_line
        except Exception as e:
            return False, str(e)
    
    def _check_core_deps(self) -> Tuple[bool, str]:
        """Check core dependencies are installed."""
        required = ["numpy", "scipy", "sounddevice", "torch", "transformers"]
        missing = []
        for pkg in required:
            if not self._is_package_installed(pkg):
                missing.append(pkg)
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        return True, "All core packages installed"
    
    def _check_platform_deps(self) -> Tuple[bool, str]:
        """Check platform-specific dependencies."""
        if self.platform == "Windows":
            return self._check_windows_deps()
        elif self.platform == "Darwin":
            return self._check_macos_deps()
        else:
            return True, "Linux - no extra platform deps required"
    
    def _check_windows_deps(self) -> Tuple[bool, str]:
        """Check Windows-specific dependencies."""
        missing = []
        for pkg in ["comtypes", "pywin32"]:
            if not self._is_package_installed(pkg):
                missing.append(pkg)
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        return True, "Windows packages installed"
    
    def _check_macos_deps(self) -> Tuple[bool, str]:
        """Check macOS-specific dependencies."""
        # Check if running on Apple Silicon
        if self.machine == "arm64":
            # Check for ARM64 optimized packages
            try:
                import torch
                if torch.backends.mps.is_available():
                    return True, "Apple Silicon with MPS support ✓"
                return True, "Apple Silicon (MPS not available, using CPU)"
            except ImportError:
                return False, "PyTorch not installed"
        return True, "Intel Mac - standard packages"
    
    def _check_pytorch(self) -> Tuple[bool, str]:
        """Check PyTorch installation and capabilities."""
        try:
            import torch
            version = torch.__version__
            
            # Check CUDA/MPS availability
            if torch.cuda.is_available():
                cuda_version = torch.version.cuda
                gpu_name = torch.cuda.get_device_name(0)
                return True, f"{version} (CUDA {cuda_version} - {gpu_name})"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return True, f"{version} (Apple MPS enabled)"
            else:
                return True, f"{version} (CPU mode)"
        except ImportError:
            return False, "PyTorch not installed"
    
    def _check_audio_backend(self) -> Tuple[bool, str]:
        """Check audio backend availability."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            return True, f"PortAudio OK - {len(input_devices)} input device(s) found"
        except ImportError:
            return False, "sounddevice not installed"
        except Exception as e:
            return False, f"PortAudio issue: {e}"
    
    def _check_ffmpeg(self) -> Tuple[bool, str]:
        """Check FFmpeg installation."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return True, version_line
            return False, "FFmpeg not working properly"
        except FileNotFoundError:
            if self.platform == "Windows":
                return False, "FFmpeg not found. Install via: winget install FFmpeg"
            elif self.platform == "Darwin":
                return False, "FFmpeg not found. Install via: brew install ffmpeg"
            else:
                return False, "FFmpeg not found. Install via: sudo apt install ffmpeg"
    
    def _check_vad_models(self) -> Tuple[bool, str]:
        """Check if VAD models are downloaded."""
        try:
            from pathlib import Path
            cache_dir = Path.home() / ".voice_translate" / "models"
            if cache_dir.exists() and any(cache_dir.iterdir()):
                models = list(cache_dir.iterdir())
                return True, f"Models cached: {len(models)} item(s)"
            return False, "VAD models not downloaded yet"
        except Exception as e:
            return False, str(e)
    
    def _test_imports(self) -> Tuple[bool, str]:
        """Test all critical imports work."""
        imports = [
            ("numpy", "np"),
            ("scipy", "sp"),
            ("torch", "torch"),
            ("sounddevice", "sd"),
            ("librosa", "librosa"),
            ("transformers", "transformers"),
        ]
        
        failed = []
        for module, alias in imports:
            try:
                __import__(module)
            except ImportError as e:
                failed.append(f"{module}: {e}")
        
        if failed:
            return False, f"Failed imports: {', '.join(failed)}"
        return True, f"All {len(imports)} critical packages importable"
    
    def _check_tests(self) -> Tuple[bool, str]:
        """Check if tests can be run."""
        test_files = [
            "voice_translation_app/tests/test_platform.py",
            "tests/test_platform.py"
        ]
        for test_file in test_files:
            if os.path.exists(test_file):
                return True, f"Tests found: {test_file}"
        return False, "No test files found"
    
    # ==================== Install Functions ====================
    
    def _update_pip(self) -> Tuple[bool, str]:
        """Update pip to latest version."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, "pip updated successfully"
            return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def _install_core_deps(self) -> Tuple[bool, str]:
        """Install core requirements."""
        return self._pip_install("requirements.txt")
    
    def _install_platform_deps(self) -> Tuple[bool, str]:
        """Install platform-specific requirements."""
        if self.platform == "Windows":
            return self._pip_install("voice_translation_app/requirements-windows.txt")
        elif self.platform == "Darwin":
            if self.machine == "arm64":
                return self._pip_install("voice_translation_app/requirements-macos-arm64.txt")
            return self._pip_install("voice_translation_app/requirements.txt")
        return True, "No platform-specific deps for Linux"
    
    def _install_pytorch(self) -> Tuple[bool, str]:
        """Install PyTorch with appropriate backend."""
        if self.platform == "Darwin" and self.machine == "arm64":
            # Apple Silicon
            cmd = [
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio"
            ]
        elif self.platform == "Windows":
            # Windows with CUDA 11.8
            cmd = [
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu118"
            ]
        else:
            # CPU only for Linux or Intel Mac
            cmd = [
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cpu"
            ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True, "PyTorch installed successfully"
            return False, result.stderr[:500]
        except Exception as e:
            return False, str(e)
    
    def _install_audio_backend(self) -> Tuple[bool, str]:
        """Install and configure audio backend."""
        if self.platform == "Darwin":
            # macOS needs PortAudio from brew
            return self._brew_install("portaudio", "PortAudio")
        elif self.platform == "Windows":
            # Windows PyAudio might need special handling
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "PyAudio>=0.2.13"],
                    capture_output=True,
                    check=True
                )
                return True, "PyAudio installed"
            except subprocess.CalledProcessError:
                return False, "PyAudio install failed. Try: pip install pipwin && pipwin install pyaudio"
        return True, "Audio backend OK"
    
    def _download_vad_models(self) -> Tuple[bool, str]:
        """Download VAD models."""
        try:
            # Use torch hub to download Silero VAD
            import torch
            model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            return True, "Silero VAD model downloaded"
        except Exception as e:
            return False, f"Failed to download VAD model: {e}"
    
    def _run_tests(self) -> Tuple[bool, str]:
        """Run the test suite."""
        test_file = None
        for path in ["voice_translation_app/tests/test_platform.py", "tests/test_platform.py"]:
            if os.path.exists(path):
                test_file = path
                break
        
        if not test_file:
            return False, "No test files found"
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, "All tests passed"
            return False, f"Tests failed:\n{result.stdout[-1000:]}"
        except Exception as e:
            return False, str(e)
    
    # ==================== Helper Methods ====================
    
    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            __import__(package_name.replace("-", "_"))
            return True
        except ImportError:
            return False
    
    def _pip_install(self, requirements_file: str) -> Tuple[bool, str]:
        """Install from a requirements file."""
        if not os.path.exists(requirements_file):
            return False, f"{requirements_file} not found"
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                return True, f"Installed from {requirements_file}"
            return False, result.stderr[:500]
        except subprocess.TimeoutExpired:
            return False, "Installation timed out (5 min)"
        except Exception as e:
            return False, str(e)
    
    def _brew_install(self, package: str, display_name: str) -> Tuple[bool, str]:
        """Install a package using Homebrew (macOS)."""
        try:
            # Check if already installed
            result = subprocess.run(
                ["brew", "list", package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, f"{display_name} already installed"
            
            # Install
            result = subprocess.run(
                ["brew", "install", package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, f"{display_name} installed via Homebrew"
            return False, f"brew install failed: {result.stderr}"
        except FileNotFoundError:
            return False, "Homebrew not found. Install from https://brew.sh"
        except Exception as e:
            return False, str(e)
    
    # ==================== Main Execution ====================
    
    def run(self, skip_checks: bool = False, install_all: bool = False):
        """Run the setup process."""
        print("=" * 70)
        print("VoiceTranslate Pro - Environment Setup")
        print("=" * 70)
        print(f"Platform: {self.platform} ({self.machine})")
        print(f"Python: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        print("-" * 70)
        
        if not skip_checks:
            print("\n🔍 Phase 1: Environment Validation")
            print("-" * 70)
            
            all_passed = True
            for step in self.steps:
                step.display()
                passed = step.check()
                step.display()
                if not passed and not step.is_optional:
                    all_passed = False
            
            print("\n" + "=" * 70)
            if all_passed:
                print("✅ All critical checks passed! Environment is ready.")
            else:
                print("⚠️  Some checks failed. Review above for details.")
            print("=" * 70)
        
        # Auto-install or prompt for installation
        if install_all or (not skip_checks and not all_passed):
            print("\n📦 Phase 2: Installing Missing Dependencies")
            print("-" * 70)
            
            for step in self.steps:
                if step.status == CheckStatus.FAILED and step.install_func:
                    print(f"\n⏳ Installing: {step.title}...")
                    step.install()
                    step.display()
            
            # Re-run checks
            print("\n🔄 Phase 3: Re-validating Environment")
            print("-" * 70)
            all_passed = True
            for step in self.steps:
                if not step.is_optional:
                    passed = step.check()
                    step.display()
                    if not passed:
                        all_passed = False
            
            print("\n" + "=" * 70)
            if all_passed:
                print("✅ Setup complete! Environment is ready.")
                print("\nNext steps:")
                print("  • Run the app: python voice_translation_app/src/main.py")
                print("  • List devices: python voice_translation_app/src/main.py --list-devices")
                print("  • Run tests: python -m pytest voice_translation_app/tests/ -v")
            else:
                print("❌ Setup incomplete. Please fix remaining issues manually.")
                print("\nCommon fixes:")
                print("  • macOS: brew install portaudio ffmpeg")
                print("  • Windows: winget install FFmpeg")
                print("  • All: pip install --upgrade pip")
            print("=" * 70)
    
    def print_checklist(self):
        """Print a manual checklist for users."""
        checklist = """
╔═══════════════════════════════════════════════════════════════════════════╗
║           VoiceTranslate Pro - Setup Checklist (Manual)                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  □ Step 1: Python Environment                                             ║
║    └─ □ Python 3.9+ installed (current: {py_version})
║    └─ □ Virtual environment created and activated                         ║
║    └─ □ pip upgraded: pip install --upgrade pip                           ║
║                                                                           ║
║  □ Step 2: System Dependencies                                            ║
""".format(py_version=f"{self.python_version.major}.{self.python_version.minor}")
        
        if self.platform == "Darwin":
            checklist += """║    └─ □ Homebrew installed (https://brew.sh)                              ║
║    └─ □ PortAudio: brew install portaudio                                 ║
║    └─ □ FFmpeg: brew install ffmpeg                                       ║
"""
        elif self.platform == "Windows":
            checklist += """║    └─ □ FFmpeg installed via winget: winget install FFmpeg                ║
║    └─ □ (Optional) CUDA 11.8 for GPU acceleration                         ║
"""
        else:
            checklist += """║    └─ □ PortAudio: sudo apt-get install portaudio19-dev                   ║
║    └─ □ FFmpeg: sudo apt-get install ffmpeg                               ║
"""
        
        checklist += """║                                                                           ║
║  □ Step 3: Python Dependencies                                            ║
║    └─ □ Core requirements: pip install -r requirements.txt                ║
"""
        
        if self.platform == "Darwin" and self.machine == "arm64":
            checklist += """║    └─ □ macOS ARM64: pip install -r voice_translation_app/                ║
║                      requirements-macos-arm64.txt                         ║
"""
        elif self.platform == "Windows":
            checklist += """║    └─ □ Windows: pip install -r voice_translation_app/                    ║
║                    requirements-windows.txt                               ║
"""
        
        checklist += """║                                                                           ║
║  □ Step 4: PyTorch Installation                                           ║
"""
        
        if self.platform == "Darwin" and self.machine == "arm64":
            checklist += """║    └─ □ Apple Silicon: pip install torch torchvision torchaudio           ║
"""
        elif self.platform == "Windows":
            checklist += """║    └─ □ Windows CUDA: pip install torch torchvision torchaudio            ║
║      --index-url https://download.pytorch.org/whl/cu118                   ║
"""
        else:
            checklist += """║    └─ □ CPU: pip install torch torchvision torchaudio                     ║
║      --index-url https://download.pytorch.org/whl/cpu                     ║
"""
        
        checklist += """║                                                                           ║
║  □ Step 5: Verification                                                   ║
║    └─ □ Run setup script: python setup_environment.py                     ║
║    └─ □ List audio devices: python voice_translation_app/src/main.py      ║
║                             --list-devices                                ║
║    └─ □ Check dependencies: python voice_translation_app/src/main.py      ║
║                             --check-deps                                  ║
║                                                                           ║
║  □ Step 6: (Optional) Run Tests                                           ║
║    └─ □ pytest voice_translation_app/tests/ -v                            ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Quick Commands Summary:                                                  ║
"""
        
        if self.platform == "Darwin":
            checklist += """║  $ brew install portaudio ffmpeg                                          ║
"""
        elif self.platform == "Windows":
            checklist += """║  $ winget install FFmpeg                                                  ║
"""
        
        checklist += """║  $ pip install --upgrade pip                                              ║
║  $ pip install -r requirements.txt                                        ║
"""
        
        if self.platform == "Darwin" and self.machine == "arm64":
            checklist += """║  $ pip install -r voice_translation_app/requirements-macos-arm64.txt      ║
"""
        elif self.platform == "Windows":
            checklist += """║  $ pip install -r voice_translation_app/requirements-windows.txt          ║
"""
        
        checklist += """║  $ python setup_environment.py --install-all                              ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
        print(checklist)


def main():
    parser = argparse.ArgumentParser(
        description="VoiceTranslate Pro Environment Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run checks only (default)
  python setup_environment.py
  
  # Run checks and auto-install missing dependencies
  python setup_environment.py --install-all
  
  # Print manual checklist
  python setup_environment.py --print-checklist
  
  # Skip validation, just install everything
  python setup_environment.py --skip-checks --install-all
        """
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip initial environment validation"
    )
    parser.add_argument(
        "--install-all",
        action="store_true",
        help="Automatically install all missing dependencies"
    )
    parser.add_argument(
        "--print-checklist",
        action="store_true",
        help="Print manual setup checklist and exit"
    )
    
    args = parser.parse_args()
    
    setup = EnvironmentSetup()
    
    if args.print_checklist:
        setup.print_checklist()
        return
    
    setup.run(skip_checks=args.skip_checks, install_all=args.install_all)


if __name__ == "__main__":
    main()
