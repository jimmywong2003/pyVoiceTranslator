#!/usr/bin/env python3
"""
Microphone Test Script - Check if audio is being captured
"""

import sounddevice as sd
import numpy as np
import time

print("="*60)
print("🎤 MICROPHONE TEST")
print("="*60)

# List devices
print("\nAvailable Input Devices:")
input_devices = []
for i, device in enumerate(sd.query_devices()):
    if device['max_input_channels'] > 0:
        input_devices.append((i, device))
        print(f"  [{i}] {device['name']}")

if not input_devices:
    print("❌ No input devices found!")
    exit(1)

# Ask user to select
print("\nSelect microphone device:")
for idx, (i, device) in enumerate(input_devices):
    print(f"  {idx}: {device['name']} [{i}]")

selection = int(input("\nEnter number: "))
device_id = input_devices[selection][0]
device_name = input_devices[selection][1]['name']

print(f"\n🎙️  Testing: {device_name} (device {device_id})")
print("   Speak into your microphone...")
print("   Press Ctrl+C to stop\n")

# Test callback
def callback(indata, frames, time_info, status):
    if status:
        print(f"Status: {status}")
    
    # Calculate audio level
    volume_norm = np.linalg.norm(indata) * 10
    db = 20 * np.log10(volume_norm + 1e-10)
    
    # Visual bar
    bar = "█" * int(volume_norm)
    print(f"\rAudio Level: {bar:<30} {volume_norm:.1f} ({db:.1f} dB)", end='', flush=True)

# Start recording
try:
    with sd.InputStream(
        device=device_id,
        channels=1,
        samplerate=16000,
        callback=callback
    ):
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\n✅ Test complete!")
    print("\nIf you saw the audio level changing, your microphone is working.")
    print("If it stayed at 0.0, check macOS microphone permissions.")
