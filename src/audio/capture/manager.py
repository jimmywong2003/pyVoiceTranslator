"""
Cross-platform audio capture manager
"""

import platform
import logging
from typing import Callable, List, Dict, Optional
import numpy as np

from ..config import AudioConfig, AudioSource
from .base import BaseAudioCapture

logger = logging.getLogger(__name__)


class AudioManager:
    """
    Cross-platform audio capture manager
    
    Automatically selects the appropriate capture implementation
    based on the current platform.
    
    Usage:
        config = AudioConfig(sample_rate=16000)
        manager = AudioManager(config)
        
        def on_audio(chunk):
            print(f"Received {len(chunk)} samples")
        
        manager.start_capture(AudioSource.MICROPHONE, on_audio)
        # ... do work ...
        manager.stop_capture()
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.platform = platform.system()
        self._capture: Optional[BaseAudioCapture] = None
        self._source: Optional[AudioSource] = None
        
        logger.info(f"AudioManager initialized for {self.platform}")
    
    def _create_capture(self) -> BaseAudioCapture:
        """Create platform-specific capture instance"""
        if self.platform == "Windows":
            from .windows import WindowsAudioCapture
            return WindowsAudioCapture(
                self.config.sample_rate,
                self.config.chunk_duration_ms
            )
        elif self.platform == "Darwin":  # macOS
            from .macos import MacOSAudioCapture
            return MacOSAudioCapture(
                self.config.sample_rate,
                self.config.chunk_duration_ms
            )
        else:
            raise NotImplementedError(f"Platform {self.platform} not supported")
    
    def list_devices(self, source: AudioSource = AudioSource.MICROPHONE) -> List[Dict]:
        """
        List available audio devices
        
        Args:
            source: Type of audio source to list devices for
            
        Returns:
            List of device information dictionaries
        """
        capture = self._create_capture()
        devices = capture.list_devices()
        
        # Filter based on source type
        if source == AudioSource.SYSTEM_AUDIO:
            if self.platform == "Windows":
                devices = [d for d in devices if d.get("is_loopback")]
            elif self.platform == "Darwin":
                devices = [d for d in devices if d.get("is_blackhole")]
        
        return devices
    
    def start_capture(
        self,
        source: AudioSource,
        callback: Callable[[np.ndarray], None],
        device_index: Optional[int] = None
    ) -> bool:
        """
        Start audio capture
        
        Args:
            source: Audio source type (microphone or system audio)
            callback: Function to call with each audio chunk
            device_index: Specific device to use (None for default)
            
        Returns:
            True if capture started successfully
        """
        if self._capture is not None:
            logger.warning("Capture already running, stopping first")
            self.stop_capture()
        
        self._source = source
        self._capture = self._create_capture()
        
        is_loopback = (source == AudioSource.SYSTEM_AUDIO)
        
        success = self._capture.start_capture(
            callback=callback,
            device_index=device_index,
            is_loopback=is_loopback
        )
        
        if success:
            logger.info(f"Started {source.value} capture")
        else:
            logger.error(f"Failed to start {source.value} capture")
            self._capture = None
        
        return success
    
    def stop_capture(self):
        """Stop audio capture"""
        if self._capture is not None:
            self._capture.stop_capture()
            self._capture = None
            self._source = None
            logger.info("Capture stopped")
    
    @property
    def is_capturing(self) -> bool:
        """Check if capture is active"""
        return self._capture is not None and self._capture.is_capturing
    
    @property
    def current_source(self) -> Optional[AudioSource]:
        """Get current audio source"""
        return self._source
