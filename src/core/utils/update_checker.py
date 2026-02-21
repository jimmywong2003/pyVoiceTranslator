"""
Update Checker - Phase 5
========================

Simple update check mechanism that queries a server for latest version info.

Features:
- Check for updates from remote JSON endpoint
- Compare semantic versions
- Open browser to download page
- Non-blocking check (uses QThread)

Usage:
    from src.core.utils.update_checker import UpdateChecker
    
    checker = UpdateChecker(current_version="2.0.0")
    checker.update_available.connect(on_update_available)
    checker.check_for_updates()
"""

import json
import webbrowser
from dataclasses import dataclass
from typing import Optional, Callable
from packaging import version

import requests
from PySide6.QtCore import QObject, Signal, QThread


@dataclass
class UpdateInfo:
    """Information about available update."""
    version: str
    download_url: str
    release_notes: str
    release_date: str
    is_required: bool = False
    
    @property
    def is_newer_than(self, current_version: str) -> bool:
        """Check if this update is newer than current version."""
        try:
            return version.parse(self.version) > version.parse(current_version)
        except Exception:
            return self.version != current_version


class UpdateCheckThread(QThread):
    """Background thread for checking updates."""
    
    check_complete = Signal(bool, object)  # has_update, UpdateInfo or None
    check_failed = Signal(str)
    
    def __init__(self, current_version: str, 
                 update_url: str = "https://api.voicetranslate.pro/updates"):
        super().__init__()
        self.current_version = current_version
        self.update_url = update_url
    
    def run(self):
        """Check for updates."""
        try:
            # Fetch update info (with timeout)
            response = requests.get(
                self.update_url,
                timeout=10,
                headers={"User-Agent": f"VoiceTranslate/{self.current_version}"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse update info
            update_info = UpdateInfo(
                version=data.get("version", "0.0.0"),
                download_url=data.get("download_url", ""),
                release_notes=data.get("release_notes", ""),
                release_date=data.get("release_date", ""),
                is_required=data.get("is_required", False)
            )
            
            # Check if update is available
            has_update = update_info.is_newer_than(self.current_version)
            
            self.check_complete.emit(has_update, update_info if has_update else None)
            
        except requests.exceptions.Timeout:
            self.check_failed.emit("Update check timed out")
        except requests.exceptions.ConnectionError:
            self.check_failed.emit("No internet connection")
        except Exception as e:
            self.check_failed.emit(f"Update check failed: {e}")


class UpdateChecker(QObject):
    """
    Update checker for VoiceTranslate Pro.
    
    Signals:
        update_available: Emitted when update is found
        no_update: Emitted when no update available
        check_failed: Emitted when check fails
    """
    
    update_available = Signal(object)  # UpdateInfo
    no_update = Signal()
    check_failed = Signal(str)
    
    def __init__(self, current_version: str, 
                 update_url: str = "https://api.voicetranslate.pro/updates"):
        super().__init__()
        self.current_version = current_version
        self.update_url = update_url
        self._check_thread: Optional[UpdateCheckThread] = None
    
    def check_for_updates(self):
        """Start async check for updates."""
        # Cancel any existing check
        if self._check_thread and self._check_thread.isRunning():
            self._check_thread.wait(1000)
        
        # Create and start check thread
        self._check_thread = UpdateCheckThread(self.current_version, self.update_url)
        self._check_thread.check_complete.connect(self._on_check_complete)
        self._check_thread.check_failed.connect(self.check_failed)
        self._check_thread.start()
    
    def _on_check_complete(self, has_update: bool, update_info: Optional[UpdateInfo]):
        """Handle check completion."""
        if has_update and update_info:
            self.update_available.emit(update_info)
        else:
            self.no_update.emit()
    
    def open_download_page(self, url: str):
        """Open download page in browser."""
        webbrowser.open(url)


# Mock endpoint for testing (returns sample data)
MOCK_UPDATE_RESPONSE = {
    "version": "2.1.0",
    "download_url": "https://voicetranslate.pro/download",
    "release_notes": "Bug fixes and performance improvements",
    "release_date": "2026-03-01",
    "is_required": False
}
