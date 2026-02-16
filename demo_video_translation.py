#!/usr/bin/env python3
"""
Video Translation Demo - Phase 7

Translates video files and exports subtitles in SRT/VTT formats.

Usage:
    python demo_video_translation.py <video_file> --source en --target zh
    python demo_video_translation.py <video_file> --export-srt --export-vtt
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def progress_callback(progress: float, message: str):
    """Display progress bar."""
    bar_length = 30
    filled = int(bar_length * progress)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\r[{bar}] {progress*100:5.1f}% {message}", end='', flush=True)
    if progress >= 1.0:
        print()  # New line on completion


def translate_video(
    video_path: str,
    source_lang: str,
    target_lang: str,
    asr_model: str = "base",
    export_srt: bool = False,
    export_vtt: bool = False,
    output_dir: Optional[str] = None
):
    """
    Translate a video file.
    
    Args:
        video_path: Path to video file
        source_lang: Source language code
        target_lang: Target language code
        asr_model: ASR model size (tiny/base/small)
        export_srt: Export SRT subtitles
        export_vtt: Export VTT subtitles
        output_dir: Output directory for subtitles
    """
    from voice_translation.src.asr.faster_whisper import FasterWhisperASR
    from voice_translation.src.translation.marian import MarianTranslator
    from voice_translation.src.pipeline.batch import BatchVideoTranslator
    
    video_path = Path(video_path)
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return 1
    
    print(f"🎬 Video: {video_path.name}")
    print(f"🌐 {source_lang.upper()} → {target_lang.upper()}")
    print(f"🤖 ASR Model: {asr_model}")
    print("-" * 50)
    
    # Initialize components
    print("Initializing...")
    asr = FasterWhisperASR(
        model_size=asr_model,
        device="cpu",
        compute_type="int8",
        language=source_lang
    )
    asr.initialize()
    
    translator = MarianTranslator(
        source_lang=source_lang,
        target_lang=target_lang,
        device="auto"
    )
    translator.initialize()
    
    # Create pipeline
    pipeline = BatchVideoTranslator(
        asr=asr,
        translator=translator,
        source_lang=source_lang,
        target_lang=target_lang,
        progress_callback=progress_callback
    )
    
    # Process video
    print("\nProcessing...")
    result = pipeline.process(str(video_path))
    
    if not result.is_success:
        logger.error(f"Processing failed: {result.errors}")
        return 1
    
    # Display results
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"Duration: {result.source_duration:.1f}s")
    print(f"Processing time: {result.processing_time:.1f}s")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"\nSource ({source_lang}):")
    print(f"  {result.source_text[:200]}...")
    print(f"\nTranslation ({target_lang}):")
    print(f"  {result.translated_text[:200]}...")
    
    # Export subtitles
    output_path = Path(output_dir) if output_dir else video_path.parent
    output_path.mkdir(parents=True, exist_ok=True)
    
    base_name = video_path.stem
    exports = []
    
    if export_srt:
        srt_content = result.to_srt()
        srt_file = output_path / f"{base_name}_{target_lang}.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        exports.append(f"SRT: {srt_file}")
    
    if export_vtt:
        vtt_content = result.to_vtt()
        vtt_file = output_path / f"{base_name}_{target_lang}.vtt"
        vtt_file.write_text(vtt_content, encoding='utf-8')
        exports.append(f"VTT: {vtt_file}")
    
    if exports:
        print("\n📁 Exports:")
        for export in exports:
            print(f"   {export}")
    
    print("\n✅ Done!")
    return 0


def batch_translate(
    video_paths: list,
    source_lang: str,
    target_lang: str,
    asr_model: str = "base",
    export_srt: bool = False,
    export_vtt: bool = False,
    output_dir: Optional[str] = None
):
    """Translate multiple videos."""
    from voice_translation.src.asr.faster_whisper import FasterWhisperASR
    from voice_translation.src.translation.marian import MarianTranslator
    from voice_translation.src.pipeline.batch import BatchVideoTranslator
    
    print(f"🎬 Batch Processing: {len(video_paths)} videos")
    print(f"🌐 {source_lang.upper()} → {target_lang.upper()}")
    print("-" * 50)
    
    # Initialize components once for all videos
    print("Initializing...")
    asr = FasterWhisperASR(
        model_size=asr_model,
        device="cpu",
        compute_type="int8",
        language=source_lang
    )
    asr.initialize()
    
    translator = MarianTranslator(
        source_lang=source_lang,
        target_lang=target_lang,
        device="auto"
    )
    translator.initialize()
    
    pipeline = BatchVideoTranslator(
        asr=asr,
        translator=translator,
        source_lang=source_lang,
        target_lang=target_lang,
        progress_callback=progress_callback
    )
    
    # Process all videos
    print("\nProcessing videos...")
    results = pipeline.batch_process(video_paths)
    
    # Export results
    output_path = Path(output_dir) if output_dir else Path(".")
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 50)
    print("BATCH RESULTS")
    print("=" * 50)
    
    for i, (video_path, result) in enumerate(zip(video_paths, results)):
        video_name = Path(video_path).name
        print(f"\n{i+1}. {video_name}")
        
        if result.is_success:
            print(f"   ✅ Success (confidence: {result.confidence:.2f})")
            
            base_name = Path(video_path).stem
            
            if export_srt:
                srt_file = output_path / f"{base_name}_{target_lang}.srt"
                srt_file.write_text(result.to_srt(), encoding='utf-8')
                print(f"   📄 {srt_file.name}")
            
            if export_vtt:
                vtt_file = output_path / f"{base_name}_{target_lang}.vtt"
                vtt_file.write_text(result.to_vtt(), encoding='utf-8')
                print(f"   📄 {vtt_file.name}")
        else:
            print(f"   ❌ Failed: {result.errors}")
    
    print("\n✅ Batch processing complete!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Video Translation Demo - Phase 7"
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="Video file(s) to translate"
    )
    parser.add_argument(
        "--source", "-s",
        default="en",
        help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target", "-t",
        default="zh",
        help="Target language code (default: zh)"
    )
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=["tiny", "base", "small"],
        help="ASR model size (default: base)"
    )
    parser.add_argument(
        "--export-srt",
        action="store_true",
        help="Export SRT subtitle file"
    )
    parser.add_argument(
        "--export-vtt",
        action="store_true",
        help="Export WebVTT subtitle file"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for subtitle files"
    )
    
    args = parser.parse_args()
    
    # Check if we have a single video or multiple
    if len(args.input) == 1:
        return translate_video(
            args.input[0],
            args.source,
            args.target,
            args.model,
            args.export_srt,
            args.export_vtt,
            args.output_dir
        )
    else:
        return batch_translate(
            args.input,
            args.source,
            args.target,
            args.model,
            args.export_srt,
            args.export_vtt,
            args.output_dir
        )


if __name__ == "__main__":
    sys.exit(main())
