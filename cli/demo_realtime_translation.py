#!/usr/bin/env python3
"""
Real-time Translation Demo - Phase 5 End-to-End Pipeline

Usage:
    python demo_realtime_translation.py --source en --target zh
    python demo_realtime_translation.py --source zh --target en --device 3

Press Ctrl+C to stop.
"""

import argparse
import sys
import signal
from src.core.pipeline.orchestrator import (
    TranslationPipeline, PipelineConfig, TranslationOutput
)
from src.audio import AudioSource


class RealtimeTranslator:
    """Simple real-time translator demo."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline = TranslationPipeline(config)
        self.running = False
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n\n🛑 Stopping...")
        self.running = False
    
    def _on_translation(self, output: TranslationOutput):
        """Handle translation output."""
        if output.translated_text:
            print(f"\n🎤 [{output.source_language}] {output.source_text}")
            print(f"🌐 [{output.target_language}] {output.translated_text}")
            print(f"⏱️  {output.processing_time_ms:.0f}ms")
            print("-" * 60)
        else:
            print(f"🎤 [{output.source_language}] {output.source_text}")
            print(f"⏱️  {output.processing_time_ms:.0f}ms")
            print("-" * 60)
    
    def run(self, device_index: int = None, duration: float = None):
        """Run the translator."""
        print("=" * 70)
        print("🌐 REAL-TIME TRANSLATION DEMO - Phase 5")
        print("=" * 70)
        print(f"\nConfiguration:")
        print(f"  Source Language: {self.config.source_language}")
        print(f"  Target Language: {self.config.target_language}")
        print(f"  ASR Model: {self.config.asr_model_size}")
        print(f"  Translator: {self.config.translator_type}")
        print(f"  Audio Device: {device_index or 'default'}")
        
        # Initialize
        print("\n🚀 Initializing pipeline...")
        if not self.pipeline.initialize():
            print("❌ Failed to initialize pipeline")
            return False
        
        # Start
        print("\n🎙️  Starting audio capture...")
        print("   Speak now! (Press Ctrl+C to stop)\n")
        
        self.running = True
        success = self.pipeline.start(
            output_callback=self._on_translation,
            audio_source=AudioSource.MICROPHONE,
            device_index=device_index
        )
        
        if not success:
            print("❌ Failed to start pipeline")
            return False
        
        # Run until stopped or duration reached
        try:
            if duration:
                import time
                time.sleep(duration)
            else:
                while self.running:
                    import time
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.pipeline.stop()
        
        print("\n✅ Demo complete!")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Real-time Translation Demo"
    )
    parser.add_argument(
        "--source", "-s",
        default="en",
        help="Source language (default: en)"
    )
    parser.add_argument(
        "--target", "-t",
        default="zh",
        help="Target language (default: zh)"
    )
    parser.add_argument(
        "--device", "-d",
        type=int,
        default=None,
        help="Audio device index (use --list-devices to see options)"
    )
    parser.add_argument(
        "--asr-model",
        default="tiny",
        choices=["tiny", "base", "small"],
        help="ASR model size (default: tiny)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Run for specified seconds (default: until Ctrl+C)"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices"
    )
    parser.add_argument(
        "--no-translation",
        action="store_true",
        help="Disable translation (ASR only)"
    )
    
    args = parser.parse_args()
    
    # List devices if requested
    if args.list_devices:
        import sounddevice as sd
        print("\nAvailable Audio Devices:")
        print("-" * 70)
        for i, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                print(f"  [{i}] {device['name']}")
        print()
        return
    
    # Create config
    config = PipelineConfig(
        source_language=args.source,
        target_language=args.target,
        asr_model_size=args.asr_model,
        enable_translation=not args.no_translation
    )
    
    # Run translator
    translator = RealtimeTranslator(config)
    success = translator.run(
        device_index=args.device,
        duration=args.duration
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
