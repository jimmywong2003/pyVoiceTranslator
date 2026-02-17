"""
Audio detection testing

Test functionality to verify audio input sources are working correctly.
"""

import platform
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Audio test result"""
    test_name: str
    passed: bool
    message: str
    metrics: Optional[Dict] = None
    duration_ms: float = 0.0
    
    def __str__(self) -> str:
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"[{status}] {self.test_name}: {self.message}"


class AudioDetectionTester:
    """
    Test functionality for audio input sources
    
    Provides tests for:
    - Microphone input
    - System audio capture (loopback)
    
    Usage:
        tester = AudioDetectionTester()
        
        # Test microphone
        mic_result = tester.test_microphone()
        print(mic_result)
        
        # Test system audio
        sys_result = tester.test_system_audio()
        print(sys_result)
        
        # Run all tests
        results = tester.run_all_tests()
        for result in results:
            print(result)
    """
    
    def __init__(self, sample_rate: int = 16000, test_duration: float = 3.0):
        """
        Initialize audio tester
        
        Args:
            sample_rate: Sample rate for testing
            test_duration: Duration of test recording in seconds
        """
        self.sample_rate = sample_rate
        self.test_duration = test_duration
        self.platform = platform.system()
        
        logger.info(f"AudioDetectionTester initialized ({self.platform})")
    
    def test_microphone(self) -> TestResult:
        """
        Test microphone input
        
        Records audio and checks if signal is present.
        
        Returns:
            TestResult with pass/fail status
        """
        start_time = time.time()
        
        try:
            import sounddevice as sd
            
            # Query devices
            devices = sd.query_devices()
            input_devices = [
                d for d in devices 
                if d['max_input_channels'] > 0
            ]
            
            if not input_devices:
                return TestResult(
                    test_name="microphone",
                    passed=False,
                    message="No input devices found",
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Try to record
            logger.info(f"Recording {self.test_duration}s from microphone...")
            recording = sd.rec(
                int(self.test_duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16
            )
            sd.wait()
            
            # Analyze recording
            metrics = self._analyze_audio(recording)
            
            # Check if signal is present
            if metrics['rms'] < 10:
                return TestResult(
                    test_name="microphone",
                    passed=False,
                    message=f"Microphone signal too weak (RMS: {metrics['rms']:.2f}). Check if muted.",
                    metrics=metrics,
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            if metrics['max'] < 100:
                return TestResult(
                    test_name="microphone",
                    passed=False,
                    message=f"Microphone level very low (max: {metrics['max']}). Speak louder or check settings.",
                    metrics=metrics,
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            return TestResult(
                test_name="microphone",
                passed=True,
                message=f"Microphone working. RMS: {metrics['rms']:.2f}, Max: {metrics['max']}",
                metrics=metrics,
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            return TestResult(
                test_name="microphone",
                passed=False,
                message=f"Microphone test failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def test_system_audio(self) -> TestResult:
        """
        Test system audio capture (loopback)
        
        Returns:
            TestResult with pass/fail status
        """
        start_time = time.time()
        
        try:
            if self.platform == "Windows":
                return self._test_windows_loopback()
            elif self.platform == "Darwin":
                return self._test_macos_loopback()
            else:
                return TestResult(
                    test_name="system_audio",
                    passed=False,
                    message=f"System audio not supported on {self.platform}",
                    duration_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            logger.error(f"System audio test failed: {e}")
            return TestResult(
                test_name="system_audio",
                passed=False,
                message=f"System audio test failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def _test_windows_loopback(self) -> TestResult:
        """Test Windows WASAPI loopback"""
        try:
            import pyaudiowpatch as pyaudio
            
            p = pyaudio.PyAudio()
            try:
                # Get default WASAPI info
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = p.get_device_info_by_index(
                    wasapi_info["defaultOutputDevice"]
                )
                
                # Check for loopback capability
                if not default_speakers.get("isLoopbackDevice"):
                    # Try to find loopback device
                    found = False
                    loopback_name = None
                    for loopback in p.get_loopback_device_info_generator():
                        if default_speakers["name"] in loopback["name"]:
                            found = True
                            loopback_name = loopback["name"]
                            break
                    
                    if not found:
                        return TestResult(
                            test_name="system_audio",
                            passed=False,
                            message="No loopback device found. Install VB-Cable or enable Stereo Mix.",
                            metrics={"default_device": default_speakers["name"]}
                        )
                    
                    return TestResult(
                        test_name="system_audio",
                        passed=True,
                        message=f"Windows loopback available: {loopback_name}",
                        metrics={
                            "default_device": default_speakers["name"],
                            "loopback_device": loopback_name
                        }
                    )
                
                return TestResult(
                    test_name="system_audio",
                    passed=True,
                    message=f"Windows loopback available: {default_speakers['name']}",
                    metrics={"device": default_speakers["name"]}
                )
                
            finally:
                p.terminate()
                
        except ImportError:
            return TestResult(
                test_name="system_audio",
                passed=False,
                message="pyaudiowpatch not installed. Run: pip install pyaudiowpatch"
            )
    
    def _test_macos_loopback(self) -> TestResult:
        """Test macOS loopback via BlackHole"""
        try:
            import sounddevice as sd
            
            devices = sd.query_devices()
            blackhole = None
            
            for idx, device in enumerate(devices):
                if "BlackHole" in device["name"] and device["max_input_channels"] > 0:
                    blackhole = device
                    break
            
            if blackhole is None:
                return TestResult(
                    test_name="system_audio",
                    passed=False,
                    message="BlackHole not found. Install from https://github.com/ExistentialAudio/BlackHole",
                    metrics={
                        "install_command": "brew install blackhole-2ch"
                    }
                )
            
            return TestResult(
                test_name="system_audio",
                passed=True,
                message=f"BlackHole found: {blackhole['name']}",
                metrics={
                    "device": blackhole["name"],
                    "channels": blackhole["max_input_channels"],
                    "sample_rate": blackhole["default_samplerate"]
                }
            )
            
        except ImportError:
            return TestResult(
                test_name="system_audio",
                passed=False,
                message="sounddevice not installed. Run: pip install sounddevice"
            )
    
    def _analyze_audio(self, audio: np.ndarray) -> Dict:
        """Analyze audio signal"""
        # Convert to float for analysis
        float_audio = audio.astype(np.float32) / 32768.0
        
        return {
            "rms": float(np.sqrt(np.mean(float_audio ** 2)) * 32768),
            "max": int(np.max(np.abs(audio))),
            "min": int(np.min(np.abs(audio))),
            "mean": float(np.mean(np.abs(float_audio)) * 32768),
            "samples": len(audio),
            "duration": len(audio) / self.sample_rate
        }
    
    def run_all_tests(self) -> List[TestResult]:
        """
        Run all audio detection tests
        
        Returns:
            List of test results
        """
        logger.info("Running all audio tests...")
        
        tests = [
            self.test_microphone(),
            self.test_system_audio()
        ]
        
        passed = sum(1 for t in tests if t.passed)
        logger.info(f"Tests complete: {passed}/{len(tests)} passed")
        
        return tests
    
    def print_results(self, results: List[TestResult]):
        """Pretty print test results"""
        print("\n" + "=" * 60)
        print("AUDIO DETECTION TEST RESULTS")
        print("=" * 60)
        
        for result in results:
            print(result)
            if result.metrics:
                print(f"  Metrics: {result.metrics}")
        
        passed = sum(1 for r in results if r.passed)
        print("-" * 60)
        print(f"Summary: {passed}/{len(results)} tests passed")
        print("=" * 60 + "\n")
