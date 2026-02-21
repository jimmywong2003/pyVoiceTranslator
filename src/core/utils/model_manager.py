"""
Model Manager - Phase 5
=======================

Async model downloader with progress tracking, checksum verification, and mirror support.

Features:
- QThread-based async downloads (non-blocking UI)
- SHA256 checksum verification
- Multiple mirror URLs for corporate firewalls
- Resume capability for partial downloads
- Offline mode support

Usage:
    from src.core.utils.model_manager import ModelManager, ModelConfig
    
    manager = ModelManager()
    manager.progress_changed.connect(update_progress_bar)
    
    config = ModelConfig(
        name="whisper-base",
        url="https://example.com/model.bin",
        checksum="abc123..."
    )
    manager.download_model_async(config)
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Callable
from urllib.parse import urlparse
import time

import requests
from PySide6.QtCore import QObject, Signal, QThread


@dataclass
class ModelConfig:
    """Configuration for a downloadable model."""
    name: str
    url: str
    checksum: Optional[str] = None
    checksum_algo: str = "sha256"
    size_mb: Optional[float] = None
    mirrors: List[str] = None
    description: str = ""
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.mirrors is None:
            self.mirrors = []


class DownloadThread(QThread):
    """
    Background thread for downloading models.
    
    Signals:
        progress_changed: Emitted with (percent, speed_mbps)
        download_complete: Emitted with (success, message)
        status_changed: Emitted with status message
    """
    
    progress_changed = Signal(int, float)  # percent, speed_mbps
    download_complete = Signal(bool, str)  # success, message
    status_changed = Signal(str)
    
    def __init__(self, config: ModelConfig, target_path: Path, 
                 chunk_size: int = 8192, resume: bool = True):
        super().__init__()
        self.config = config
        self.target_path = target_path
        self.chunk_size = chunk_size
        self.resume = resume
        self._is_cancelled = False
        
    def cancel(self):
        """Cancel the download."""
        self._is_cancelled = True
    
    def run(self):
        """Execute the download."""
        try:
            self.status_changed.emit(f"Starting download: {self.config.name}")
            
            # Try mirrors in order
            urls = [self.config.url] + self.config.mirrors
            last_error = None
            
            for url in urls:
                if self._is_cancelled:
                    self.download_complete.emit(False, "Download cancelled")
                    return
                
                try:
                    success = self._try_download(url)
                    if success:
                        return
                except Exception as e:
                    last_error = e
                    self.status_changed.emit(f"Mirror failed: {e}")
                    continue
            
            # All mirrors failed
            self.download_complete.emit(False, f"All mirrors failed: {last_error}")
            
        except Exception as e:
            self.download_complete.emit(False, f"Download error: {e}")
    
    def _try_download(self, url: str) -> bool:
        """Try downloading from a single URL."""
        # Check for partial download to resume
        resume_pos = 0
        if self.resume and self.target_path.exists():
            resume_pos = self.target_path.stat().st_size
            self.status_changed.emit(f"Resuming from {resume_pos} bytes")
        
        # Setup request with resume support
        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"
        
        # Download with progress tracking
        start_time = time.time()
        downloaded = resume_pos
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get total size
        total_size = int(response.headers.get('content-length', 0)) + resume_pos
        
        # Open file for writing (append if resuming)
        mode = 'ab' if resume_pos > 0 else 'wb'
        with open(self.target_path, mode) as f:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if self._is_cancelled:
                    return False
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calculate progress
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                    else:
                        percent = 0
                    
                    # Calculate speed
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                    else:
                        speed_mbps = 0
                    
                    self.progress_changed.emit(percent, speed_mbps)
        
        # Verify checksum if provided
        if self.config.checksum:
            self.status_changed.emit("Verifying checksum...")
            if not self._verify_checksum():
                self.target_path.unlink()  # Delete corrupted file
                raise ValueError("Checksum verification failed")
        
        self.download_complete.emit(True, f"Downloaded successfully to {self.target_path}")
        return True
    
    def _verify_checksum(self) -> bool:
        """Verify file checksum."""
        if not self.config.checksum:
            return True
        
        hasher = hashlib.new(self.config.checksum_algo)
        with open(self.target_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        calculated = hasher.hexdigest().lower()
        expected = self.config.checksum.lower()
        
        return calculated == expected


class ModelManager(QObject):
    """
    Manager for downloading and managing ML models.
    
    Signals:
        progress_changed: Emitted when download progress updates
        download_complete: Emitted when download finishes
        status_changed: Emitted with status messages
    """
    
    progress_changed = Signal(int, float)  # percent, speed_mbps
    download_complete = Signal(bool, str)  # success, message
    status_changed = Signal(str)
    
    def __init__(self, models_dir: Optional[Path] = None):
        super().__init__()
        
        # Default models directory
        if models_dir is None:
            self.models_dir = Path.home() / ".voicetranslate" / "models"
        else:
            self.models_dir = Path(models_dir)
        
        self._ensure_models_dir()
        
        # Active download thread
        self._download_thread: Optional[DownloadThread] = None
        
        # Model registry
        self._registry_file = self.models_dir / "registry.json"
        self._registry: Dict[str, Dict] = self._load_registry()
    
    def _ensure_models_dir(self) -> bool:
        """Ensure models directory exists and is writable."""
        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
            # Test write permission
            test_file = self.models_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except PermissionError:
            # Fallback to temp directory
            import tempfile
            self.models_dir = Path(tempfile.gettempdir()) / "voicetranslate_models"
            self.models_dir.mkdir(parents=True, exist_ok=True)
            self.status_changed.emit(f"Using fallback models directory: {self.models_dir}")
            return True
        except Exception as e:
            self.status_changed.emit(f"Failed to create models directory: {e}")
            return False
    
    def _load_registry(self) -> Dict[str, Dict]:
        """Load model registry from file."""
        if self._registry_file.exists():
            try:
                with open(self._registry_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_registry(self):
        """Save model registry to file."""
        try:
            with open(self._registry_file, 'w') as f:
                json.dump(self._registry, f, indent=2)
        except Exception as e:
            self.status_changed.emit(f"Failed to save registry: {e}")
    
    def is_model_available(self, name: str) -> bool:
        """Check if a model is already downloaded."""
        model_path = self.models_dir / name
        return model_path.exists() and name in self._registry
    
    def get_model_path(self, name: str) -> Optional[Path]:
        """Get path to model if available."""
        if self.is_model_available(name):
            return self.models_dir / name
        return None
    
    def download_model_async(self, config: ModelConfig) -> bool:
        """
        Start async download of a model.
        
        Args:
            config: Model configuration
            
        Returns:
            True if download started successfully
        """
        # Cancel any existing download
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait(5000)
        
        # Setup target path
        target_path = self.models_dir / config.name
        
        # Create and start download thread
        self._download_thread = DownloadThread(config, target_path)
        self._download_thread.progress_changed.connect(self.progress_changed)
        self._download_thread.download_complete.connect(self._on_download_complete)
        self._download_thread.status_changed.connect(self.status_changed)
        
        self._download_thread.start()
        return True
    
    def _on_download_complete(self, success: bool, message: str):
        """Handle download completion."""
        if success and self._download_thread:
            # Update registry
            config = self._download_thread.config
            self._registry[config.name] = {
                "version": config.version,
                "downloaded_at": time.time(),
                "path": str(self.models_dir / config.name),
            }
            self._save_registry()
        
        self.download_complete.emit(success, message)
    
    def cancel_download(self):
        """Cancel current download."""
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait(5000)
    
    def get_available_models(self) -> List[str]:
        """Get list of available (downloaded) models."""
        return list(self._registry.keys())
    
    def delete_model(self, name: str) -> bool:
        """Delete a downloaded model."""
        try:
            model_path = self.models_dir / name
            if model_path.exists():
                if model_path.is_dir():
                    import shutil
                    shutil.rmtree(model_path)
                else:
                    model_path.unlink()
            
            if name in self._registry:
                del self._registry[name]
                self._save_registry()
            
            return True
        except Exception as e:
            self.status_changed.emit(f"Failed to delete model: {e}")
            return False
    
    def get_models_dir_size(self) -> int:
        """Get total size of models directory in bytes."""
        try:
            total = 0
            for item in self.models_dir.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total
        except Exception:
            return 0
