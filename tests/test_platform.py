"""
Cross-platform unit tests for Voice Translation Application
"""

import unittest
import sys
import os
import platform
from unittest.mock import patch, MagicMock

from src.app.platform_utils import (
    detect_platform,
    get_platform_info,
    PlatformType,
    PlatformInfo,
    PlatformPaths,
    AudioPlatformHelper,
    DependencyChecker,
    macos_only,
    windows_only,
    apple_silicon_only
)


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection functionality"""
    
    def test_detect_platform_returns_valid_type(self):
        """Test that platform detection returns a valid PlatformType"""
        result = detect_platform()
        self.assertIsInstance(result, PlatformType)
        self.assertIn(result, list(PlatformType))
    
    @patch('platform.system', return_value='Darwin')
    @patch('platform.machine', return_value='arm64')
    def test_detect_apple_silicon(self, mock_machine, mock_system):
        """Test detection of Apple Silicon Mac"""
        result = detect_platform()
        self.assertEqual(result, PlatformType.MACOS_APPLE_SILICON)
    
    @patch('platform.system', return_value='Darwin')
    @patch('platform.machine', return_value='x86_64')
    def test_detect_macos_intel(self, mock_machine, mock_system):
        """Test detection of Intel Mac"""
        result = detect_platform()
        self.assertEqual(result, PlatformType.MACOS_INTEL)
    
    @patch('platform.system', return_value='Windows')
    def test_detect_windows(self, mock_system):
        """Test detection of Windows"""
        result = detect_platform()
        self.assertEqual(result, PlatformType.WINDOWS)


class TestPlatformInfo(unittest.TestCase):
    """Test PlatformInfo dataclass"""
    
    def test_platform_info_creation(self):
        """Test creating PlatformInfo instance"""
        info = PlatformInfo(
            platform_type=PlatformType.MACOS_APPLE_SILICON,
            system='Darwin',
            machine='arm64',
            processor='arm',
            architecture='64bit',
            python_version='3.11.0',
            python_implementation='CPython',
            is_64bit=True,
            is_conda=False,
            is_virtualenv=False
        )
        
        self.assertTrue(info.is_macos)
        self.assertFalse(info.is_windows)
        self.assertTrue(info.is_apple_silicon)
    
    def test_get_platform_info(self):
        """Test getting platform info"""
        info = get_platform_info()
        self.assertIsInstance(info, PlatformInfo)
        self.assertIsNotNone(info.platform_type)
        self.assertIsNotNone(info.system)


class TestPlatformDecorators(unittest.TestCase):
    """Test platform-specific decorators"""
    
    @patch('platform_utils.detect_platform', return_value=PlatformType.MACOS_APPLE_SILICON)
    def test_macos_only_decorator(self, mock_detect):
        """Test macOS-only decorator"""
        @macos_only
        def macos_function():
            return "macos"
        
        result = macos_function()
        self.assertEqual(result, "macos")
    
    @patch('platform_utils.detect_platform', return_value=PlatformType.WINDOWS)
    def test_macos_only_decorator_skips_on_windows(self, mock_detect):
        """Test macOS-only decorator skips on Windows"""
        @macos_only
        def macos_function():
            return "macos"
        
        result = macos_function()
        self.assertIsNone(result)
    
    @patch('platform_utils.detect_platform', return_value=PlatformType.WINDOWS)
    def test_windows_only_decorator(self, mock_detect):
        """Test Windows-only decorator"""
        @windows_only
        def windows_function():
            return "windows"
        
        result = windows_function()
        self.assertEqual(result, "windows")
    
    @patch('platform_utils.detect_platform', return_value=PlatformType.MACOS_APPLE_SILICON)
    def test_apple_silicon_only_decorator(self, mock_detect):
        """Test Apple Silicon-only decorator"""
        @apple_silicon_only
        def apple_silicon_function():
            return "apple_silicon"
        
        result = apple_silicon_function()
        self.assertEqual(result, "apple_silicon")


class TestPlatformPaths(unittest.TestCase):
    """Test PlatformPaths functionality"""
    
    def setUp(self):
        self.paths = PlatformPaths("TestApp")
    
    @patch('platform_utils.detect_platform', return_value=PlatformType.MACOS_APPLE_SILICON)
    def test_macos_config_dir(self, mock_detect):
        """Test macOS config directory"""
        self.paths.platform = PlatformType.MACOS_APPLE_SILICON
        config_dir = self.paths.get_config_dir()
        self.assertIn('Library/Application Support', config_dir)
        self.assertIn('TestApp', config_dir)
    
    @patch('platform_utils.detect_platform', return_value=PlatformType.WINDOWS)
    @patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'})
    def test_windows_config_dir(self, mock_detect):
        """Test Windows config directory"""
        self.paths.platform = PlatformType.WINDOWS
        config_dir = self.paths.get_config_dir()
        self.assertIn('TestApp', config_dir)


class TestAudioPlatformHelper(unittest.TestCase):
    """Test AudioPlatformHelper functionality"""
    
    def test_get_recommended_sample_rate(self):
        """Test recommended sample rate"""
        helper = AudioPlatformHelper()
        rate = helper.get_recommended_sample_rate()
        self.assertEqual(rate, 16000)
    
    def test_get_recommended_buffer_size_apple_silicon(self):
        """Test buffer size for Apple Silicon"""
        helper = AudioPlatformHelper()
        helper.platform = PlatformType.MACOS_APPLE_SILICON
        size = helper.get_recommended_buffer_size()
        self.assertEqual(size, 512)
    
    def test_get_recommended_buffer_size_windows(self):
        """Test buffer size for Windows"""
        helper = AudioPlatformHelper()
        helper.platform = PlatformType.WINDOWS
        size = helper.get_recommended_buffer_size()
        self.assertEqual(size, 1024)


class TestDependencyChecker(unittest.TestCase):
    """Test DependencyChecker functionality"""
    
    def test_checker_initialization(self):
        """Test DependencyChecker initialization"""
        checker = DependencyChecker()
        self.assertEqual(checker.missing, [])
        self.assertEqual(checker.warnings, [])
    
    @patch('sys.version_info', (3, 11, 0, 'final', 0))
    def test_python_version_check_pass(self):
        """Test Python version check passes"""
        checker = DependencyChecker()
        result = checker._check_python_version()
        self.assertTrue(result)
        self.assertEqual(checker.missing, [])
    
    @patch('sys.version_info', (3, 8, 0, 'final', 0))
    def test_python_version_check_fail(self):
        """Test Python version check fails"""
        checker = DependencyChecker()
        result = checker._check_python_version()
        self.assertFalse(result)
        self.assertTrue(any('Python 3.9+' in msg for msg in checker.missing))


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility"""
    
    def test_all_platform_types_have_values(self):
        """Test all platform types have string values"""
        for pt in PlatformType:
            self.assertIsInstance(pt.value, str)
            self.assertTrue(len(pt.value) > 0)
    
    def test_platform_info_properties(self):
        """Test PlatformInfo boolean properties"""
        # macOS Apple Silicon
        info = PlatformInfo(
            platform_type=PlatformType.MACOS_APPLE_SILICON,
            system='Darwin', machine='arm64', processor='arm',
            architecture='64bit', python_version='3.11.0',
            python_implementation='CPython', is_64bit=True,
            is_conda=False, is_virtualenv=False
        )
        self.assertTrue(info.is_macos)
        self.assertTrue(info.is_apple_silicon)
        self.assertFalse(info.is_windows)
        
        # Windows
        info = PlatformInfo(
            platform_type=PlatformType.WINDOWS,
            system='Windows', machine='AMD64', processor='Intel64',
            architecture='64bit', python_version='3.11.0',
            python_implementation='CPython', is_64bit=True,
            is_conda=False, is_virtualenv=False
        )
        self.assertFalse(info.is_macos)
        self.assertFalse(info.is_apple_silicon)
        self.assertTrue(info.is_windows)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformDecorators))
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformPaths))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioPlatformHelper))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestCrossPlatformCompatibility))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
