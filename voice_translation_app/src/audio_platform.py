"""
Cross-Platform Audio Capture Layer
Supports: macOS (CoreAudio/BlackHole) and Windows (WASAPI/PyAudio)
"""

import platform
import sys
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration for capture"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: str = "int16"
    device_index: Optional[int] = None
    

class AudioCaptureBase(ABC):
    """Abstract base class for audio capture"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.is_recording = False
        self._callback: Optional[Callable[[np.ndarray], None]] = None
    
    @abstractmethod
    def list_devices(self) -> List[dict]:
        """List available audio devices"""
        pass
    
    @abstractmethod
    def start_recording(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start audio capture with callback"""
        pass
    
    @abstractmethod
    def stop_recording(self) -> bool:
        """Stop audio capture"""
        pass
    
    @abstractmethod
    def get_default_device(self) -> Optional[dict]:
        """Get default input device"""
        pass


# =============================================================================
# macOS Implementation (CoreAudio via sounddevice + BlackHole for loopback)
# =============================================================================

class MacOSAudioCapture(AudioCaptureBase):
    """macOS audio capture using sounddevice with CoreAudio backend"""
    
    def __init__(self, config: AudioConfig):
        super().__init__(config)
        self._stream = None
        self._import_dependencies()
        
    def _import_dependencies(self):
        """Lazy import platform-specific dependencies"""
        try:
            import sounddevice as sd
            import soundfile as sf
            self.sd = sd
            self.sf = sf
        except ImportError as e:
            logger.error(f"macOS audio dependencies not installed: {e}")
            raise
    
    def list_devices(self) -> List[dict]:
        """List all CoreAudio devices"""
        devices = []
        for i, device in enumerate(self.sd.query_devices()):
            devices.append({
                'index': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate'],
                'is_input': device['max_input_channels'] > 0,
                'is_output': device['max_output_channels'] > 0,
                'platform': 'macOS CoreAudio'
            })
        return devices
    
    def find_blackhole_device(self) -> Optional[int]:
        """Find BlackHole virtual audio device for system audio capture"""
        devices = self.list_devices()
        for device in devices:
            if 'blackhole' in device['name'].lower() or 'blackhole' in device.get('id', '').lower():
                if device['is_input'] and device['channels'] >= 2:
                    logger.info(f"Found BlackHole device: {device['name']} (index: {device['index']})")
                    return device['index']
        logger.warning("BlackHole device not found. Install from: https://github.com/ExistentialAudio/BlackHole")
        return None
    
    def get_default_device(self) -> Optional[dict]:
        """Get default input device"""
        try:
            device_info = self.sd.query_devices(kind='input')
            return {
                'index': device_info['index'],
                'name': device_info['name'],
                'channels': device_info['max_input_channels'],
                'sample_rate': device_info['default_samplerate']
            }
        except Exception as e:
            logger.error(f"Error getting default device: {e}")
            return None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Internal callback for sounddevice"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        if self._callback is not None:
            # Convert to mono if needed
            if indata.shape[1] > 1 and self.config.channels == 1:
                indata = np.mean(indata, axis=1, keepdims=True)
            self._callback(indata.flatten())
    
    def start_recording(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start recording from microphone"""
        try:
            self._callback = callback
            device = self.config.device_index
            if device is None:
                device = self.get_default_device()['index']
            
            self._stream = self.sd.InputStream(
                device=device,
                channels=self.config.channels,
                samplerate=self.config.sample_rate,
                blocksize=self.config.chunk_size,
                dtype=self.config.format,
                callback=self._audio_callback
            )
            self._stream.start()
            self.is_recording = True
            logger.info(f"Started recording from device {device}")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """Stop recording"""
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            self.is_recording = False
            logger.info("Stopped recording")
            return True
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False


class MacOSSystemAudioCapture(MacOSAudioCapture):
    """macOS system audio capture via BlackHole"""
    
    def __init__(self, config: AudioConfig):
        super().__init__(config)
        # Force BlackHole device
        blackhole_index = self.find_blackhole_device()
        if blackhole_index is not None:
            self.config.device_index = blackhole_index
        else:
            logger.error("BlackHole not installed. System audio capture unavailable.")
    
    def setup_blackhole(self):
        """Instructions for BlackHole setup"""
        return """
        BlackHole Setup Instructions:
        1. Install BlackHole: brew install blackhole-2ch (or blackhole-16ch)
        2. Open Audio MIDI Setup (Applications > Utilities)
        3. Create Multi-Output Device:
           - Click '+' > Create Multi-Output Device
           - Check both your speakers/headphones AND BlackHole
        4. Set as default output in System Preferences > Sound
        5. This app will capture from BlackHole input
        """


# =============================================================================
# Windows Implementation (WASAPI via PyAudio)
# =============================================================================

class WindowsAudioCapture(AudioCaptureBase):
    """Windows audio capture using PyAudio with WASAPI"""
    
    def __init__(self, config: AudioConfig):
        super().__init__(config)
        self._pa = None
        self._stream = None
        self._import_dependencies()
    
    def _import_dependencies(self):
        """Lazy import platform-specific dependencies"""
        try:
            import pyaudio
            self.pyaudio = pyaudio
            self._pa = pyaudio.PyAudio()
        except ImportError as e:
            logger.error(f"Windows audio dependencies not installed: {e}")
            raise
    
    def _get_format_constant(self) -> int:
        """Convert format string to PyAudio constant"""
        format_map = {
            'int16': self.pyaudio.paInt16,
            'int32': self.pyaudio.paInt32,
            'float32': self.pyaudio.paFloat32,
            'uint8': self.pyaudio.paUInt8
        }
        return format_map.get(self.config.format, self.pyaudio.paInt16)
    
    def list_devices(self) -> List[dict]:
        """List all WASAPI devices"""
        devices = []
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            devices.append({
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': info['defaultSampleRate'],
                'is_input': info['maxInputChannels'] > 0,
                'is_output': info['maxOutputChannels'] > 0,
                'platform': 'Windows WASAPI',
                'host_api': self._pa.get_host_api_info_by_index(info['hostApi'])['name']
            })
        return devices
    
    def find_loopback_device(self) -> Optional[int]:
        """Find WASAPI loopback device for system audio capture"""
        devices = self.list_devices()
        for device in devices:
            # WASAPI loopback devices are output devices that can be opened in loopback mode
            if device['is_output'] and 'WASAPI' in device.get('host_api', ''):
                logger.info(f"Found loopback-capable device: {device['name']} (index: {device['index']})")
                return device['index']
        return None
    
    def get_default_device(self) -> Optional[dict]:
        """Get default input device"""
        try:
            info = self._pa.get_default_input_device_info()
            return {
                'index': info['index'],
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': info['defaultSampleRate']
            }
        except Exception as e:
            logger.error(f"Error getting default device: {e}")
            return None
    
    def start_recording(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start recording from microphone"""
        try:
            self._callback = callback
            device = self.config.device_index
            if device is None:
                device = self.get_default_device()['index']
            
            def stream_callback(in_data, frame_count, time_info, status):
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                callback(audio_data)
                return (in_data, self.pyaudio.paContinue)
            
            self._stream = self._pa.open(
                format=self._get_format_constant(),
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=stream_callback
            )
            self._stream.start_stream()
            self.is_recording = True
            logger.info(f"Started recording from device {device}")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """Stop recording"""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            self.is_recording = False
            logger.info("Stopped recording")
            return True
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False
    
    def __del__(self):
        """Cleanup PyAudio"""
        if self._pa:
            self._pa.terminate()


class WindowsSystemAudioCapture(WindowsAudioCapture):
    """Windows system audio capture via WASAPI loopback"""
    
    def __init__(self, config: AudioConfig):
        super().__init__(config)
        # Force loopback device
        loopback_index = self.find_loopback_device()
        if loopback_index is not None:
            self.config.device_index = loopback_index
    
    def start_recording(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start loopback recording from system audio"""
        try:
            self._callback = callback
            device = self.config.device_index
            
            # For WASAPI loopback, we need to open an output device as input
            # This requires special handling
            def stream_callback(in_data, frame_count, time_info, status):
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                callback(audio_data)
                return (in_data, self.pyaudio.paContinue)
            
            # Open stream with loopback flag (Windows-specific)
            self._stream = self._pa.open(
                format=self._get_format_constant(),
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=stream_callback,
                as_loopback=True  # WASAPI loopback mode
            )
            self._stream.start_stream()
            self.is_recording = True
            logger.info(f"Started system audio capture from device {device}")
            return True
        except Exception as e:
            logger.error(f"Failed to start system audio capture: {e}")
            logger.info("Falling back to standard capture mode")
            return super().start_recording(callback)


# =============================================================================
# Factory and Platform Detection
# =============================================================================

def get_platform() -> str:
    """Detect current platform"""
    system = platform.system()
    machine = platform.machine()
    
    if system == 'Darwin':
        if 'arm' in machine.lower() or 'aarch64' in machine.lower():
            return 'macos_apple_silicon'
        return 'macos_intel'
    elif system == 'Windows':
        return 'windows'
    else:
        return 'unknown'


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon"""
    return get_platform() == 'macos_apple_silicon'


def create_audio_capture(config: AudioConfig, capture_system_audio: bool = False) -> AudioCaptureBase:
    """Factory function to create appropriate audio capture instance"""
    platform_type = get_platform()
    
    if platform_type.startswith('macos'):
        if capture_system_audio:
            return MacOSSystemAudioCapture(config)
        return MacOSAudioCapture(config)
    
    elif platform_type == 'windows':
        if capture_system_audio:
            return WindowsSystemAudioCapture(config)
        return WindowsAudioCapture(config)
    
    else:
        raise NotImplementedError(f"Platform {platform_type} not supported")


# =============================================================================
# Unified Audio Interface
# =============================================================================

class UnifiedAudioCapture:
    """High-level unified audio capture interface"""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._microphone_capture: Optional[AudioCaptureBase] = None
        self._system_capture: Optional[AudioCaptureBase] = None
        self.platform = get_platform()
    
    def initialize(self, capture_microphone: bool = True, capture_system: bool = False):
        """Initialize audio capture sources"""
        if capture_microphone:
            self._microphone_capture = create_audio_capture(self.config, capture_system_audio=False)
        
        if capture_system:
            self._system_capture = create_audio_capture(self.config, capture_system_audio=True)
    
    def list_all_devices(self) -> dict:
        """List all available devices on the system"""
        result = {
            'platform': self.platform,
            'microphone_devices': [],
            'system_audio_devices': []
        }
        
        if self._microphone_capture:
            result['microphone_devices'] = self._microphone_capture.list_devices()
        
        if self._system_capture:
            result['system_audio_devices'] = self._system_capture.list_devices()
        
        return result
    
    def start_microphone_capture(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start microphone capture"""
        if self._microphone_capture is None:
            self._microphone_capture = create_audio_capture(self.config, capture_system_audio=False)
        return self._microphone_capture.start_recording(callback)
    
    def start_system_capture(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start system audio capture"""
        if self._system_capture is None:
            self._system_capture = create_audio_capture(self.config, capture_system_audio=True)
        return self._system_capture.start_recording(callback)
    
    def stop_all(self):
        """Stop all capture"""
        if self._microphone_capture:
            self._microphone_capture.stop_recording()
        if self._system_capture:
            self._system_capture.stop_recording()


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Detect platform
    platform_type = get_platform()
    print(f"Detected platform: {platform_type}")
    
    # Create unified audio capture
    config = AudioConfig(sample_rate=16000, channels=1, chunk_size=1024)
    audio = UnifiedAudioCapture(config)
    audio.initialize(capture_microphone=True, capture_system=False)
    
    # List devices
    devices = audio.list_all_devices()
    print(f"\nAvailable devices:")
    for device in devices['microphone_devices']:
        print(f"  [{device['index']}] {device['name']} ({device['channels']}ch @ {device['sample_rate']}Hz)")
    
    # Test capture
    def audio_callback(data: np.ndarray):
        print(f"Received {len(data)} samples, max amplitude: {np.max(np.abs(data))}")
    
    print("\nStarting 5-second test capture...")
    audio.start_microphone_capture(audio_callback)
    
    import time
    time.sleep(5)
    
    audio.stop_all()
    print("Capture stopped")
