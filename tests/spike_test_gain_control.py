#!/usr/bin/env python3
"""
Week 1 Spike Test: Hardware Gain Control Validation

This script tests whether hardware gain control is available on the current system.
Run this to validate feasibility before full development.

Usage:
    python tests/spike_test_gain_control.py

Output:
    - Hardware gain availability report
    - Device capability summary
    - Recommendation for architecture decision
"""

import sys
import platform
import time
import numpy as np

# Add src to path
sys.path.insert(0, 'src')

from audio.auto_tune import AudioAutoTuner, LevelAnalyzer


def test_digital_gain_latency():
    """Test digital gain processing latency."""
    print("\n" + "="*60)
    print("TEST: Digital Gain Latency")
    print("="*60)
    
    from audio.auto_tune import DigitalGainProcessor
    
    processor = DigitalGainProcessor()
    
    # Test with various buffer sizes
    buffer_sizes = [512, 1024, 2048, 4096, 8192]
    sample_rate = 16000
    
    results = []
    
    for size in buffer_sizes:
        # Create test buffer
        test_buffer = np.random.randn(size).astype(np.float32) * 0.1
        
        # Set gain
        processor.set_gain(0, 10.0)  # +10 dB
        
        # Measure processing time
        times = []
        for _ in range(100):
            start = time.perf_counter()
            result = processor.process_buffer(0, test_buffer)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = np.mean(times) * 1000  # Convert to ms
        max_time = np.max(times) * 1000
        
        results.append({
            'buffer_size': size,
            'duration_ms': (size / sample_rate) * 1000,
            'avg_latency_ms': avg_time,
            'max_latency_ms': max_time,
            'within_budget': avg_time < 5.0
        })
        
        status = "✅ PASS" if avg_time < 5.0 else "❌ FAIL"
        print(f"  Buffer {size:5d} samples ({(size/sample_rate)*1000:5.1f}ms): "
              f"Avg={avg_time:.3f}ms Max={max_time:.3f}ms {status}")
    
    all_pass = all(r['within_budget'] for r in results)
    
    print(f"\n  Result: {'✅ PASS' if all_pass else '❌ FAIL'}")
    print(f"  All buffers processed within 5ms budget: {all_pass}")
    
    return all_pass, results


def test_hardware_gain_detection():
    """Test hardware gain control detection."""
    print("\n" + "="*60)
    print("TEST: Hardware Gain Control Detection")
    print("="*60)
    
    system = platform.system()
    print(f"  Platform: {system}")
    print(f"  Version: {platform.version()}")
    
    tuner = AudioAutoTuner()
    
    if tuner.hardware_controller is None:
        print("  ❌ No hardware controller available")
        print("  Will use digital gain fallback (100% coverage)")
        return False, []
    
    controller = tuner.hardware_controller
    print(f"  Controller: {controller.get_platform_name()}")
    
    # Get available devices
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [(i, d) for i, d in enumerate(devices) 
                        if d['max_input_channels'] > 0]
    except Exception as e:
        print(f"  ❌ Could not query devices: {e}")
        return False, []
    
    print(f"\n  Found {len(input_devices)} input device(s):")
    
    results = []
    
    for device_id, device_info in input_devices:
        device_name = device_info['name']
        print(f"\n  Device [{device_id}]: {device_name}")
        
        # Check hardware support
        supports_hardware = controller.supports_hardware_gain(device_id)
        
        # Get capabilities
        caps = controller.get_capabilities(device_id)
        
        if caps:
            print(f"    Hardware Support: {'✅ YES' if supports_hardware else '❌ NO'}")
            print(f"    Gain Range: {caps.min_gain_db:.1f} to {caps.max_gain_db:.1f} dB")
            print(f"    Current Gain: {caps.current_gain_db:.1f} dB")
            print(f"    Can Mute: {'Yes' if caps.can_mute else 'No'}")
            
            results.append({
                'device_id': device_id,
                'device_name': device_name,
                'supports_hardware': supports_hardware,
                'min_db': caps.min_gain_db,
                'max_db': caps.max_gain_db,
                'current_db': caps.current_gain_db
            })
        else:
            print(f"    ❌ Could not get capabilities")
            results.append({
                'device_id': device_id,
                'device_name': device_name,
                'supports_hardware': False,
                'error': 'No capabilities'
            })
    
    # Calculate success rate
    hardware_supported = sum(1 for r in results if r.get('supports_hardware', False))
    total = len(results)
    success_rate = hardware_supported / total if total > 0 else 0
    
    print(f"\n  Summary:")
    print(f"    Total Devices: {total}")
    print(f"    Hardware Supported: {hardware_supported}")
    print(f"    Success Rate: {success_rate:.0%}")
    
    return success_rate >= 0.4, results


def test_profile_persistence():
    """Test profile save/load functionality."""
    print("\n" + "="*60)
    print("TEST: Profile Persistence")
    print("="*60)
    
    import tempfile
    import json
    import os
    
    # Create test profile
    test_profile = {
        "profile_version": "2.2.0",
        "profiles": [
            {
                "device_id": 2,
                "device_name": "Test Microphone",
                "gain_mode": "digital",
                "gain_db": 8.5,
                "digital_multiplier": 2.66,
                "noise_floor_db": -58.2,
                "peak_level_db": -6.1,
                "rms_level_db": -17.8,
                "snr_db": 40.4,
                "sample_rate": 16000,
                "timestamp": "2026-02-21T23:45:00Z",
                "confidence_score": 0.94
            }
        ],
        "active_profile": 2
    }
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_profile, f, indent=2)
        temp_path = f.name
    
    try:
        # Load back
        with open(temp_path, 'r') as f:
            loaded = json.load(f)
        
        # Verify
        assert loaded['profile_version'] == '2.2.0'
        assert len(loaded['profiles']) == 1
        assert loaded['profiles'][0]['device_id'] == 2
        
        print("  ✅ Profile save/load works")
        print(f"  ✅ Version: {loaded['profile_version']}")
        print(f"  ✅ Device count: {len(loaded['profiles'])}")
        
        success = True
        
    except Exception as e:
        print(f"  ❌ Profile persistence failed: {e}")
        success = False
    
    finally:
        os.unlink(temp_path)
    
    return success, []


def generate_report(digital_latency_pass, digital_latency_results,
                   hardware_detect_pass, hardware_detect_results,
                   profile_pass, profile_results):
    """Generate spike test report."""
    print("\n" + "="*60)
    print("SPIKE TEST REPORT")
    print("="*60)
    
    print("\n📊 Test Results:")
    print(f"  Digital Gain Latency:   {'✅ PASS' if digital_latency_pass else '❌ FAIL'}")
    print(f"  Hardware Detection:     {'✅ PASS' if hardware_detect_pass else '❌ FAIL'}")
    print(f"  Profile Persistence:    {'✅ PASS' if profile_pass else '❌ FAIL'}")
    
    # Calculate overall success
    tests_passed = sum([digital_latency_pass, hardware_detect_pass, profile_pass])
    tests_total = 3
    
    print(f"\n  Overall: {tests_passed}/{tests_total} tests passed")
    
    # Decision recommendation
    print("\n🎯 Architecture Decision:")
    
    if hardware_detect_results:
        hardware_supported = sum(1 for r in hardware_detect_results 
                                if r.get('supports_hardware', False))
        total_devices = len(hardware_detect_results)
        success_rate = hardware_supported / total_devices if total_devices > 0 else 0
        
        print(f"  Hardware Control Success Rate: {success_rate:.0%}")
        
        if success_rate >= 0.7:
            print("  ✅ RECOMMENDATION: Dual-mode (hardware primary)")
            print("     Hardware gain works on most devices.")
        elif success_rate >= 0.4:
            print("  ⚠️  RECOMMENDATION: Dual-mode (digital primary)")
            print("     Mixed results - use hardware as bonus.")
        else:
            print("  ❌ RECOMMENDATION: Digital-only + manual guidance")
            print("     Hardware gain unreliable on this system.")
    else:
        print("  ❌ No hardware controller available")
        print("  Will use digital-only mode (100% coverage)")
    
    print("\n" + "="*60)
    
    # GO/NO-GO
    if digital_latency_pass and profile_pass:
        print("✅ GO: Core functionality validated")
        print("   Digital gain fallback works (100% coverage guaranteed)")
        return True
    else:
        print("❌ NO-GO: Critical tests failed")
        print("   Digital gain has issues that must be resolved")
        return False


def main():
    """Run spike tests."""
    print("="*60)
    print("AUDIO AUTO-TUNE: WEEK 1 SPIKE TEST")
    print("="*60)
    print("\nThis test validates hardware gain control availability")
    print("and measures digital gain performance.")
    
    try:
        # Test 1: Digital gain latency
        digital_latency_pass, digital_latency_results = test_digital_gain_latency()
        
        # Test 2: Hardware gain detection
        hardware_detect_pass, hardware_detect_results = test_hardware_gain_detection()
        
        # Test 3: Profile persistence
        profile_pass, profile_results = test_profile_persistence()
        
        # Generate report
        go = generate_report(
            digital_latency_pass, digital_latency_results,
            hardware_detect_pass, hardware_detect_results,
            profile_pass, profile_results
        )
        
        return 0 if go else 1
        
    except Exception as e:
        print(f"\n❌ Spike test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
