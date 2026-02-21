"""
Debug Logging System - Phase 5
==============================

Comprehensive debug logging for VoiceTranslate Pro using loguru.

Features:
- Rotating log files with size limits
- System info capture
- Component-level logging
- Crash dump generation
- Privacy mode (redact sensitive text)
- Runtime log level switching
- Automatic cleanup of old logs

Usage:
    from src.core.utils.debug_logger import DebugLogger
    
    debug_logger = DebugLogger()
    debug_logger.enable()
    
    # Privacy mode (redact transcripts)
    debug_logger.set_privacy_mode(True)
    
    # Log with component tags
    debug_logger.log_component("ASR", "Processing audio segment", level="INFO")
"""

import sys
import os
import platform
import traceback
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import json
import shutil

from loguru import logger


@dataclass
class SystemInfo:
    """System information for debugging."""
    platform: str
    platform_version: str
    python_version: str
    cpu_count: int
    memory_gb: float
    cpu_percent: float
    memory_percent: float
    gpu_info: str = "Unknown"
    
    @classmethod
    def collect(cls) -> "SystemInfo":
        """Collect current system information."""
        try:
            mem = psutil.virtual_memory()
            return cls(
                platform=platform.system(),
                platform_version=platform.version(),
                python_version=platform.python_version(),
                cpu_count=os.cpu_count() or 0,
                memory_gb=round(mem.total / (1024**3), 2),
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=mem.percent,
                gpu_info=cls._get_gpu_info()
            )
        except Exception as e:
            return cls(
                platform=platform.system(),
                platform_version="Unknown",
                python_version=platform.python_version(),
                cpu_count=0,
                memory_gb=0.0,
                cpu_percent=0.0,
                memory_percent=0.0,
                gpu_info=f"Error: {e}"
            )
    
    @staticmethod
    def _get_gpu_info() -> str:
        """Get GPU information if available."""
        try:
            # Try to detect Apple Silicon
            if platform.system() == "Darwin" and platform.machine() == "arm64":
                return "Apple Silicon (M1/M2/M3)"
            
            # Try torch for CUDA info
            try:
                import torch
                if torch.cuda.is_available():
                    return f"CUDA: {torch.cuda.get_device_name(0)}"
            except ImportError:
                pass
            
            return "No GPU detected"
        except Exception as e:
            return f"Unknown ({e})"


class DebugLogger:
    """
    Comprehensive debug logging for VoiceTranslate Pro.
    
    Features:
    - Rotating log files
    - System info capture
    - Crash dump generation
    - Privacy mode (disable text logging)
    - Runtime log level switching
    - Automatic cleanup of old logs
    """
    
    LOG_DIR = Path.home() / ".voicetranslate" / "logs"
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5
    DEFAULT_RETENTION_DAYS = 30
    
    def __init__(self, app_version: str = "2.0.0"):
        """
        Initialize debug logger.
        
        Args:
            app_version: Application version string
        """
        self.app_version = app_version
        self._enabled = False
        self._privacy_mode = False
        self._log_id: Optional[int] = None
        self._session_start = datetime.now()
        
        # Ensure log directory exists
        self._ensure_log_dir()
    
    def _ensure_log_dir(self) -> bool:
        """
        Ensure log directory exists and is writable.
        
        Returns:
            True if directory is ready
        """
        try:
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)
            # Test write permission
            test_file = self.LOG_DIR / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except PermissionError:
            # Fallback to temp directory
            import tempfile
            self.LOG_DIR = Path(tempfile.gettempdir()) / "voicetranslate_logs"
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback log directory: {self.LOG_DIR}")
            return True
        except Exception as e:
            logger.error(f"Failed to create log directory: {e}")
            return False
    
    def enable(self, level: str = "DEBUG") -> bool:
        """
        Enable debug logging to file.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            
        Returns:
            True if enabled successfully
        """
        if self._enabled:
            return True
        
        try:
            # Clean old logs first
            self.cleanup_old_logs()
            
            # Generate log filename with timestamp
            timestamp = self._session_start.strftime("%Y%m%d_%H%M%S")
            log_file = self.LOG_DIR / f"voicetranslate_{timestamp}.log"
            
            # Add file handler with rotation
            self._log_id = logger.add(
                str(log_file),
                level=level,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} | {message}",
                rotation=self.MAX_BYTES,
                retention=self.BACKUP_COUNT,
                encoding="utf-8",
            )
            
            self._enabled = True
            
            # Log startup info
            self._log_startup_info()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable debug logging: {e}")
            return False
    
    def disable(self):
        """Disable debug logging."""
        if self._log_id is not None:
            logger.remove(self._log_id)
            self._log_id = None
            self._enabled = False
    
    def set_privacy_mode(self, enabled: bool):
        """
        Enable/disable privacy mode.
        
        When enabled, transcripts and translations are redacted
        to protect sensitive information.
        
        Args:
            enabled: True to enable privacy mode
        """
        self._privacy_mode = enabled
        if enabled:
            logger.info("🔒 Privacy mode enabled - transcripts will be redacted")
        else:
            logger.info("🔓 Privacy mode disabled - full logging enabled")
    
    def _redact_sensitive(self, text: str) -> str:
        """Redact sensitive text in privacy mode."""
        if not self._privacy_mode or not text:
            return text
        # Replace with hash or placeholder
        return f"[REDACTED:{hash(text) & 0xFFFFFF:06X}]"
    
    def log_component(self, component: str, message: str, level: str = "INFO", **kwargs):
        """
        Log with component tag.
        
        Args:
            component: Component name (e.g., "ASR", "Translation", "VAD")
            message: Log message
            level: Log level
            **kwargs: Additional context data
        """
        if not self._enabled:
            return
        
        # Redact sensitive data if privacy mode is on
        if self._privacy_mode and "text" in kwargs:
            kwargs["text"] = self._redact_sensitive(kwargs["text"])
        
        # Format: [COMPONENT] message | key=value, key2=value2
        context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"[{component}] {message}"
        if context:
            full_message += f" | {context}"
        
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(full_message)
    
    def log_transcript(self, speaker: str, text: str, translated: Optional[str] = None):
        """
        Log transcript with privacy protection.
        
        Args:
            speaker: Speaker identifier
            text: Original text
            translated: Translated text (optional)
        """
        if not self._enabled:
            return
        
        if self._privacy_mode:
            text = self._redact_sensitive(text)
            translated = self._redact_sensitive(translated) if translated else None
        
        if translated:
            logger.info(f"[TRANSCRIPT] {speaker}: {text} -> {translated}")
        else:
            logger.info(f"[TRANSCRIPT] {speaker}: {text}")
    
    def _log_startup_info(self):
        """Log system information at startup."""
        logger.info(f"{'='*60}")
        logger.info(f"VoiceTranslate Pro v{self.app_version}")
        logger.info(f"Session started: {self._session_start.isoformat()}")
        logger.info(f"{'='*60}")
        
        # System info
        sys_info = SystemInfo.collect()
        logger.info("System Information:")
        for key, value in asdict(sys_info).items():
            logger.info(f"  {key}: {value}")
        
        logger.info(f"{'='*60}")
    
    def log_crash(self, exception: Exception, context: Optional[Dict] = None):
        """
        Log crash information.
        
        Args:
            exception: The exception that caused the crash
            context: Additional context data
        """
        if not self._enabled:
            return
        
        logger.error(f"{'='*60}")
        logger.error("CRASH REPORT")
        logger.error(f"{'='*60}")
        logger.error(f"Time: {datetime.now().isoformat()}")
        logger.error(f"Exception: {type(exception).__name__}: {exception}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        if context:
            logger.error(f"Context: {json.dumps(context, indent=2, default=str)}")
        
        # System state at crash
        sys_info = SystemInfo.collect()
        logger.error(f"System state at crash:")
        for key, value in asdict(sys_info).items():
            logger.error(f"  {key}: {value}")
        
        logger.error(f"{'='*60}")
        
        # Also write crash dump file
        self._write_crash_dump(exception, context)
    
    def _write_crash_dump(self, exception: Exception, context: Optional[Dict] = None):
        """Write crash dump to separate file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_file = self.LOG_DIR / f"crash_{timestamp}.json"
            
            dump_data = {
                "timestamp": datetime.now().isoformat(),
                "app_version": self.app_version,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "traceback": traceback.format_exc(),
                "system_info": asdict(SystemInfo.collect()),
                "context": context or {}
            }
            
            with open(dump_file, 'w', encoding='utf-8') as f:
                json.dump(dump_data, f, indent=2, default=str)
            
            logger.info(f"Crash dump written to: {dump_file}")
        except Exception as e:
            logger.error(f"Failed to write crash dump: {e}")
    
    def cleanup_old_logs(self, days: int = None) -> int:
        """
        Delete log files older than specified days.
        
        Args:
            days: Number of days to retain (default: 30)
            
        Returns:
            Number of files deleted
        """
        if days is None:
            days = self.DEFAULT_RETENTION_DAYS
        
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        try:
            for log_file in self.LOG_DIR.glob("*.log"):
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff:
                        log_file.unlink()
                        deleted += 1
                except Exception:
                    pass
            
            # Also clean old crash dumps
            for dump_file in self.LOG_DIR.glob("crash_*.json"):
                try:
                    mtime = datetime.fromtimestamp(dump_file.stat().st_mtime)
                    if mtime < cutoff:
                        dump_file.unlink()
                        deleted += 1
                except Exception:
                    pass
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old log files")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning old logs: {e}")
            return 0
    
    def get_log_files(self) -> List[Path]:
        """Get list of log files sorted by modification time (newest first)."""
        try:
            files = list(self.LOG_DIR.glob("*.log"))
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return files
        except Exception:
            return []
    
    def get_log_dir_size(self) -> int:
        """Get total size of log directory in bytes."""
        try:
            total = 0
            for f in self.LOG_DIR.glob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total
        except Exception:
            return 0


# Global instance for easy access
_debug_logger: Optional[DebugLogger] = None


def get_debug_logger(app_version: str = "2.0.0") -> DebugLogger:
    """Get or create global debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger(app_version)
    return _debug_logger
