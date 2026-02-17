"""
Base audio capture interface
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Dict, Optional
import numpy as np


class BaseAudioCapture(ABC):
    """Abstract base class for audio capture implementations"""
    
    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        self.is_capturing = False
        self._callback: Optional[Callable[[np.ndarray], None]] = None
        
    @abstractmethod
    def list_devices(self) -> List[Dict]:
        """List available audio devices"""
        pass
    
    @abstractmethod
    def start_capture(self, callback: Callable[[np.ndarray], None]) -> bool:
        """
        Start audio capture
        
        Args:
            callback: Function to call with each audio chunk
            
        Returns:
            True if started successfully
        """
        pass
    
    @abstractmethod
    def stop_capture(self):
        """Stop audio capture"""
        pass
    
    def _process_audio(self, audio_data: np.ndarray):
        """Process captured audio and call callback"""
        if self._callback is not None:
            self._callback(audio_data)
