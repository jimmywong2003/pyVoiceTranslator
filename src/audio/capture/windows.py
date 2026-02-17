"""
Windows audio capture implementation using WASAPI
"""

import platform
import numpy as np
from typing import Callable, List, Dict, Optional
import logging

from .base import BaseAudioCapture

logger = logging.getLogger(__name__)


class WindowsAudioCapture(BaseAudioCapture):
    """
    Windows audio capture using WASAPI
    
    Supports both microphone and system audio (loopback) capture.
    Requires pyaudiowpatch for loopback support.
    """
    
    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 30):
        super().__init__(sample_rate, chunk_duration_ms)
        self._pyaudio = None
        self._stream = None
        
        # Verify we're on Windows
        if platform.system() != "Windows":
            raise RuntimeError("WindowsAudioCapture only works on Windows")
    
    def list_devices(self) -> List[Dict]:
        """List all available audio devices"""
        try:
            import pyaudiowpatch as pyaudio
            
            p = pyaudio.PyAudio()
            devices = []
            
            try:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxInputChannels"],
                        "sample_rate": int(info["defaultSampleRate"]),
                        "is_loopback": info.get("isLoopbackDevice", False)
                    })
            finally:
                p.terminate()
                
            return devices
            
        except ImportError:
            logger.error("pyaudiowpatch not installed. Run: pip install pyaudiowpatch")
            return []
    
    def get_loopback_device(self) -> Optional[Dict]:
        """
        Find the default WASAPI loopback device
        
        Returns:
            Device info dict or None if not found
        """
        try:
            import pyaudiowpatch as pyaudio
            
            p = pyaudio.PyAudio()
            try:
                # Get default WASAPI info
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = p.get_device_info_by_index(
                    wasapi_info["defaultOutputDevice"]
                )
                
                # Check if already loopback
                if default_speakers.get("isLoopbackDevice"):
                    return default_speakers
                
                # Find matching loopback device
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        return loopback
                        
                return None
                
            finally:
                p.terminate()
                
        except Exception as e:
            logger.error(f"Error finding loopback device: {e}")
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
            is_loopback: Whether to capture system audio
            
        Returns:
            True if started successfully
        """
        try:
            import pyaudiowpatch as pyaudio
            
            self._callback = callback
            self._pyaudio = pyaudio.PyAudio()
            
            if is_loopback:
                # Find loopback device
                if device_index is None:
                    device = self.get_loopback_device()
                    if device is None:
                        raise RuntimeError(
                            "No loopback device found. "
                            "Install VB-Cable or enable Stereo Mix."
                        )
                    device_index = device["index"]
                    sample_rate = int(device["defaultSampleRate"])
                    channels = device["maxInputChannels"]
                else:
                    device_info = self._pyaudio.get_device_info_by_index(device_index)
                    sample_rate = int(device_info["defaultSampleRate"])
                    channels = device_info["maxInputChannels"]
            else:
                # Microphone capture
                if device_index is None:
                    device_index = self._pyaudio.get_default_input_device_info()["index"]
                device_info = self._pyaudio.get_device_info_by_index(device_index)
                sample_rate = int(device_info["defaultSampleRate"])
                channels = device_info["maxInputChannels"]
            
            # Resample if needed
            self._target_sample_rate = self.sample_rate
            self._source_sample_rate = sample_rate
            
            def audio_callback(in_data, frame_count, time_info, status):
                """PyAudio callback"""
                # Convert to numpy array
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                
                # Convert to mono if stereo
                if channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                
                # Resample if needed
                if self._source_sample_rate != self._target_sample_rate:
                    audio_data = self._resample(audio_data, self._source_sample_rate, self._target_sample_rate)
                
                self._process_audio(audio_data)
                return (in_data, pyaudio.paContinue)
            
            # Open stream
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                frames_per_buffer=self.chunk_samples,
                input=True,
                input_device_index=device_index,
                stream_callback=audio_callback
            )
            
            self._stream.start_stream()
            self.is_capturing = True
            
            logger.info(f"Started capture from device {device_index} at {sample_rate}Hz")
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
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")
            finally:
                self._stream = None
        
        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self._pyaudio = None
        
        logger.info("Audio capture stopped")
    
    def _resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """Fast linear resampling"""
        if orig_sr == target_sr:
            return audio
        
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)
