"""
macOS audio capture implementation using CoreAudio via sounddevice
"""

import platform
import numpy as np
from typing import Callable, List, Dict, Optional
import logging

from .base import BaseAudioCapture

logger = logging.getLogger(__name__)


class MacOSAudioCapture(BaseAudioCapture):
    """
    macOS audio capture using CoreAudio via sounddevice
    
    Supports microphone capture natively.
    For system audio, requires BlackHole virtual audio device.
    
    BlackHole Installation:
        brew install blackhole-2ch  # or blackhole-16ch
    
    Setup for system audio:
        1. Install BlackHole
        2. Set BlackHole as output device in System Preferences
        3. Capture from BlackHole input
    """
    
    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 30):
        super().__init__(sample_rate, chunk_duration_ms)
        self._stream = None
        
        # Verify we're on macOS
        if platform.system() != "Darwin":
            raise RuntimeError("MacOSAudioCapture only works on macOS")
    
    def list_devices(self) -> List[Dict]:
        """List all available audio devices"""
        try:
            import sounddevice as sd
            
            devices = []
            for i, device in enumerate(sd.query_devices()):
                devices.append({
                    "index": i,
                    "name": device["name"],
                    "channels": device["max_input_channels"],
                    "sample_rate": int(device["default_samplerate"]),
                    "is_blackhole": "BlackHole" in device["name"]
                })
            return devices
            
        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice")
            return []
    
    def find_blackhole_device(self) -> Optional[tuple]:
        """
        Find BlackHole virtual audio device
        
        Returns:
            Tuple of (device_index, device_info) or None
        """
        try:
            import sounddevice as sd
            
            for idx, device in enumerate(sd.query_devices()):
                if "BlackHole" in device["name"] and device["max_input_channels"] > 0:
                    return idx, device
            return None
            
        except Exception as e:
            logger.error(f"Error finding BlackHole: {e}")
            return None
    
    def find_microphone(self) -> Optional[tuple]:
        """
        Find default microphone
        
        Returns:
            Tuple of (device_index, device_info) or None
        """
        try:
            import sounddevice as sd
            
            default_input = sd.query_devices(kind="input")
            for idx, device in enumerate(sd.query_devices()):
                if device["name"] == default_input["name"]:
                    return idx, device
            return None
            
        except Exception as e:
            logger.error(f"Error finding microphone: {e}")
            return None
    
    def start_capture(
        self,
        callback: Callable[[np.ndarray], None],
        device_index: Optional[int] = None,
        is_loopback: bool = False
    ) -> bool:
        """
        Start audio capture
        
        Args:
            callback: Function to call with each audio chunk
            device_index: Specific device index (None for default)
            is_loopback: Whether to capture from BlackHole
            
        Returns:
            True if started successfully
        """
        try:
            import sounddevice as sd
            
            self._callback = callback
            
            if is_loopback:
                # Use BlackHole for system audio
                if device_index is None:
                    result = self.find_blackhole_device()
                    if result is None:
                        raise RuntimeError(
                            "BlackHole not found. Install with: "
                            "brew install blackhole-2ch"
                        )
                    device_index, device_info = result
                    logger.info(f"Using BlackHole: {device_info['name']}")
            else:
                # Use microphone
                if device_index is None:
                    result = self.find_microphone()
                    if result is None:
                        raise RuntimeError("No microphone found")
                    device_index, device_info = result
            
            def audio_callback(indata, frames, time_info, status):
                """sounddevice callback"""
                if status:
                    logger.warning(f"Audio status: {status}")
                
                # Convert to mono if needed (average multiple channels)
                if indata.shape[1] > 1:
                    audio_data = np.mean(indata, axis=1).copy()
                else:
                    audio_data = indata.copy().flatten()
                
                # Convert to int16
                audio_data = (audio_data * 32767).astype(np.int16)
                
                self._process_audio(audio_data)
            
            # Get device info to determine actual channels
            device_info = sd.query_devices(device_index)
            actual_channels = device_info['max_input_channels']
            
            # Use device's actual channels (some devices don't support mono)
            channels_to_use = min(actual_channels, 2)  # Use 1 or 2 channels
            
            logger.info(f"Opening stream: device={device_index}, "
                       f"channels={channels_to_use}, samplerate={self.sample_rate}")
            
            # Open stream with device's native channels
            self._stream = sd.InputStream(
                device=device_index,
                channels=channels_to_use,
                samplerate=self.sample_rate,
                blocksize=self.chunk_samples,
                dtype=np.float32,
                callback=audio_callback
            )
            
            self._stream.start()
            self.is_capturing = True
            
            logger.info(f"Started capture from device {device_index} at {self.sample_rate}Hz")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start capture: {e}")
            self.stop_capture()
            return False
    
    def stop_capture(self):
        """Stop audio capture"""
        self.is_capturing = False
        
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")
            finally:
                self._stream = None
        
        logger.info("Audio capture stopped")
