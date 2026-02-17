"""
Voice Translation Application - Main Entry Point
Cross-platform real-time voice translation with ML
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from platform_utils import (
    detect_platform, 
    get_platform_info, 
    setup_environment,
    DependencyChecker,
    PlatformPaths
)
from audio_platform import (
    AudioConfig, 
    UnifiedAudioCapture,
    create_audio_capture
)
from ml_platform import (
    MLPlatformConfig,
    create_optimizer,
    print_system_info
)


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Real-time Voice Translation Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run with default settings
  %(prog)s --list-devices            # List available audio devices
  %(prog)s --device 1                # Use specific audio device
  %(prog)s --model base              # Use specific Whisper model
  %(prog)s --system-audio            # Capture system audio (requires setup)
  %(prog)s --verbose                 # Enable verbose logging
        """
    )
    
    # Audio options
    audio_group = parser.add_argument_group('Audio Options')
    audio_group.add_argument(
        '--list-devices', 
        action='store_true',
        help='List available audio devices and exit'
    )
    audio_group.add_argument(
        '--device', 
        type=int, 
        default=None,
        help='Audio device index to use'
    )
    audio_group.add_argument(
        '--sample-rate', 
        type=int, 
        default=16000,
        help='Audio sample rate (default: 16000)'
    )
    audio_group.add_argument(
        '--system-audio',
        action='store_true',
        help='Capture system audio instead of microphone'
    )
    
    # Model options
    model_group = parser.add_argument_group('Model Options')
    model_group.add_argument(
        '--model',
        type=str,
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )
    model_group.add_argument(
        '--language',
        type=str,
        default='auto',
        help='Source language (auto for auto-detect)'
    )
    model_group.add_argument(
        '--target-language',
        type=str,
        default='en',
        help='Target language for translation'
    )
    
    # Performance options
    perf_group = parser.add_argument_group('Performance Options')
    perf_group.add_argument(
        '--device-type',
        type=str,
        default='auto',
        choices=['auto', 'cpu', 'cuda', 'mps', 'directml'],
        help='Compute device (default: auto)'
    )
    perf_group.add_argument(
        '--precision',
        type=str,
        default='fp32',
        choices=['fp32', 'fp16', 'int8'],
        help='Model precision (default: fp32)'
    )
    
    # General options
    parser.add_argument(
        '--verbose', 
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check dependencies and exit'
    )
    
    return parser.parse_args()


def list_devices():
    """List all available audio devices"""
    print("\n" + "=" * 60)
    print("AVAILABLE AUDIO DEVICES")
    print("=" * 60)
    
    config = AudioConfig()
    
    # List microphone devices
    print("\n🎤 Microphone Devices:")
    try:
        mic_capture = create_audio_capture(config, capture_system_audio=False)
        devices = mic_capture.list_devices()
        for device in devices:
            if device['is_input']:
                print(f"  [{device['index']}] {device['name']}")
                print(f"       Channels: {device['channels']}, Sample Rate: {int(device['sample_rate'])} Hz")
    except Exception as e:
        print(f"  Error listing microphone devices: {e}")
    
    # List system audio devices (platform-specific)
    print("\n🔊 System Audio Devices:")
    try:
        sys_capture = create_audio_capture(config, capture_system_audio=True)
        devices = sys_capture.list_devices()
        for device in devices:
            if device['is_input'] or 'loopback' in device.get('name', '').lower():
                print(f"  [{device['index']}] {device['name']}")
                print(f"       Channels: {device['channels']}, Sample Rate: {int(device['sample_rate'])} Hz")
    except Exception as e:
        print(f"  Error listing system audio devices: {e}")
    
    print("\n" + "=" * 60)


def check_dependencies():
    """Check all dependencies and print report"""
    print("\n" + "=" * 60)
    print("DEPENDENCY CHECK")
    print("=" * 60)
    
    checker = DependencyChecker()
    results = checker.check_all()
    
    print(f"\n✓ Python Version: {'PASS' if results['python_version'] else 'FAIL'}")
    print(f"✓ PyTorch: {'PASS' if results['pytorch'] else 'FAIL'}")
    print(f"✓ Audio Libraries: {'PASS' if results['audio'] else 'FAIL'}")
    print(f"✓ ML Libraries: {'PASS' if results['ml'] else 'FAIL'}")
    print(f"✓ Platform Specific: {'PASS' if results['platform_specific'] else 'FAIL'}")
    
    if results['missing']:
        print(f"\n❌ Missing Dependencies:")
        for dep in results['missing']:
            print(f"   - {dep}")
    
    if results['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in results['warnings']:
            print(f"   - {warning}")
    
    if results['all_ok']:
        print("\n✅ All dependencies satisfied!")
    else:
        print("\n❌ Some dependencies are missing. Please install them.")
    
    print("=" * 60)
    return results['all_ok']


def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Setup environment
    setup_environment()
    
    # Print system info
    if args.verbose:
        print_system_info()
    
    # Handle special commands
    if args.list_devices:
        list_devices()
        return 0
    
    if args.check_deps:
        ok = check_dependencies()
        return 0 if ok else 1
    
    # Check dependencies
    logger.info("Checking dependencies...")
    checker = DependencyChecker()
    deps_ok = checker.check_all()
    if not deps_ok:
        logger.error("Missing dependencies. Run with --check-deps for details.")
        return 1
    
    # Get platform info
    platform_info = get_platform_info()
    logger.info(f"Platform: {platform_info.platform_type.value}")
    
    # Setup ML optimizer
    logger.info("Setting up ML optimizer...")
    ml_config = MLPlatformConfig(
        device=args.device_type,
        precision=args.precision
    )
    optimizer = create_optimizer(ml_config)
    device_info = optimizer.get_device_info()
    logger.info(f"Using device: {device_info['device']}")
    
    # Setup audio capture
    logger.info("Setting up audio capture...")
    audio_config = AudioConfig(
        sample_rate=args.sample_rate,
        device_index=args.device
    )
    audio_capture = UnifiedAudioCapture(audio_config)
    audio_capture.initialize(
        capture_microphone=not args.system_audio,
        capture_system=args.system_audio
    )
    
    # Print startup message
    print("\n" + "=" * 60)
    print("🎙️  Voice Translation Application")
    print("=" * 60)
    print(f"Platform: {platform_info.platform_type.value}")
    print(f"Model: Whisper {args.model}")
    print(f"Source: {'System Audio' if args.system_audio else 'Microphone'}")
    print(f"Device: {device_info['device']}")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # TODO: Initialize translation pipeline and start capture
    # This is where you would:
    # 1. Load Whisper model
    # 2. Load translation model
    # 3. Start audio capture with callback
    # 4. Process audio chunks through pipeline
    
    try:
        import numpy as np
        
        def audio_callback(data: np.ndarray):
            """Process audio data"""
            # Placeholder for actual processing
            amplitude = np.max(np.abs(data))
            if amplitude > 1000:  # Threshold for speech detection
                print(f"Audio level: {amplitude:.0f}", end='\r')
        
        if args.system_audio:
            audio_capture.start_system_capture(audio_callback)
        else:
            audio_capture.start_microphone_capture(audio_callback)
        
        # Keep running
        import time
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        audio_capture.stop_all()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
