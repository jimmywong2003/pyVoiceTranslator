"""
Voice Translation System - Main Entry Point

Example usage:
    # Real-time translation (macOS with whisper.cpp)
    python main.py --mode realtime --source zh --target en --asr whisper.cpp

    # Batch video translation
    python main.py --mode batch --input video.mp4 --source zh --target en

    # Hybrid edge-cloud translation
    python main.py --mode hybrid --input audio.wav --source ja --target en
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.asr import WhisperCppASR, FasterWhisperASR
from src.translation import NLLBTranslator, MarianTranslator
from src.pipeline import RealtimeTranslator, BatchVideoTranslator, HybridTranslator
from src.audio import VideoExtractor


def create_asr(args):
    """Create ASR instance based on arguments."""
    if args.asr == "whisper.cpp":
        return WhisperCppASR(
            model_path=args.model_path or "models/ggml-medium.bin",
            executable_path=args.whisper_cpp_path or "./whisper.cpp/main",
            threads=args.threads,
            use_metal=args.use_metal
        )
    elif args.asr == "faster-whisper":
        return FasterWhisperASR(
            model_size=args.model_size or "medium",
            device=args.device,
            compute_type=args.compute_type
        )
    else:
        raise ValueError(f"Unknown ASR: {args.asr}")


def create_translator(args):
    """Create translator instance based on arguments."""
    if args.translator == "nllb":
        return NLLBTranslator(
            model_name=args.translation_model or "facebook/nllb-200-distilled-600M",
            device=args.device
        )
    elif args.translator == "marian":
        return MarianTranslator(
            source_lang=args.source,
            target_lang=args.target
        )
    else:
        raise ValueError(f"Unknown translator: {args.translator}")


def realtime_mode(args):
    """Run in real-time translation mode."""
    print(f"Starting real-time translation: {args.source} -> {args.target}")
    
    asr = create_asr(args)
    translator = create_translator(args)
    
    pipeline = RealtimeTranslator(
        asr=asr,
        translator=translator,
        source_lang=args.source,
        target_lang=args.target
    )
    
    def on_result(result):
        if result.is_success:
            print(f"\n[{result.source_language}] {result.source_text}")
            print(f"[{result.target_language}] {result.translated_text}")
        else:
            print(f"Error: {result.errors}")
    
    print("Listening... (Press Ctrl+C to stop)")
    try:
        pipeline.process_microphone(callback=on_result)
    except KeyboardInterrupt:
        print("\nStopping...")
        pipeline.stop()


def batch_mode(args):
    """Run in batch video translation mode."""
    print(f"Processing video: {args.input}")
    print(f"Translation: {args.source} -> {args.target}")
    
    asr = create_asr(args)
    translator = create_translator(args)
    
    pipeline = BatchVideoTranslator(
        asr=asr,
        translator=translator,
        source_lang=args.source,
        target_lang=args.target,
        progress_callback=lambda p, m: print(f"[{p*100:.0f}%] {m}")
    )
    
    result = pipeline.process(args.input)
    
    if result.is_success:
        print("\n--- Transcription ---")
        print(result.source_text)
        print("\n--- Translation ---")
        print(result.translated_text)
        
        # Save subtitles
        if args.output:
            srt_path = Path(args.output).with_suffix('.srt')
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(result.to_srt())
            print(f"\nSubtitles saved to: {srt_path}")
    else:
        print(f"Error: {result.errors}")


def hybrid_mode(args):
    """Run in hybrid edge-cloud mode."""
    print(f"Hybrid translation: {args.source} -> {args.target}")
    
    edge_asr = create_asr(args)
    edge_translator = create_translator(args)
    
    # TODO: Add cloud ASR/translator if API keys provided
    cloud_asr = None
    cloud_translator = None
    
    pipeline = HybridTranslator(
        edge_asr=edge_asr,
        edge_translator=edge_translator,
        cloud_asr=cloud_asr,
        cloud_translator=cloud_translator,
        source_lang=args.source,
        target_lang=args.target,
        confidence_threshold=args.confidence_threshold
    )
    
    result = pipeline.process(args.input)
    
    if result.is_success:
        print("\n--- Source ---")
        print(result.source_text)
        print("\n--- Translation ---")
        print(result.translated_text)
        print(f"\nConfidence: {result.confidence:.2f}")
    else:
        print(f"Error: {result.errors}")


def main():
    parser = argparse.ArgumentParser(
        description="Voice Translation System"
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["realtime", "batch", "hybrid"],
        default="batch",
        help="Processing mode"
    )
    
    # Input/Output
    parser.add_argument(
        "--input", "-i",
        help="Input audio/video file (for batch/hybrid mode)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path"
    )
    
    # Language settings
    parser.add_argument(
        "--source", "-s",
        default="zh",
        choices=["zh", "en", "ja", "fr", "auto"],
        help="Source language"
    )
    parser.add_argument(
        "--target", "-t",
        default="en",
        choices=["zh", "en", "ja", "fr"],
        help="Target language"
    )
    
    # ASR settings
    parser.add_argument(
        "--asr",
        choices=["whisper.cpp", "faster-whisper", "mlx-whisper"],
        default="faster-whisper",
        help="ASR implementation"
    )
    parser.add_argument(
        "--model-path",
        help="Path to ASR model file"
    )
    parser.add_argument(
        "--model-size",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo", "distil-large-v3"],
        help="Model size for faster-whisper"
    )
    parser.add_argument(
        "--whisper-cpp-path",
        help="Path to whisper.cpp executable"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for whisper.cpp"
    )
    parser.add_argument(
        "--use-metal",
        action="store_true",
        help="Use Metal GPU acceleration (macOS)"
    )
    
    # Translation settings
    parser.add_argument(
        "--translator",
        choices=["nllb", "marian"],
        default="nllb",
        help="Translation implementation"
    )
    parser.add_argument(
        "--translation-model",
        help="Translation model name"
    )
    
    # Device settings
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Device for inference"
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        choices=["int8", "float16", "float32"],
        help="Computation precision"
    )
    
    # Hybrid settings
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Confidence threshold for cloud fallback"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode in ["batch", "hybrid"] and not args.input:
        parser.error("--input is required for batch/hybrid mode")
    
    # Run selected mode
    if args.mode == "realtime":
        realtime_mode(args)
    elif args.mode == "batch":
        batch_mode(args)
    elif args.mode == "hybrid":
        hybrid_mode(args)


if __name__ == "__main__":
    main()
