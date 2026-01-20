#!/usr/bin/env python3
"""
Simple voice message transcription tool using Whisper
"""
import whisper
from pathlib import Path
import argparse
import sys


def transcribe_file(filename: str, model_size: str = "base"):
    """
    Transcribe a voice message file from the data folder

    Args:
        filename: Name of the file in the data folder (e.g., "VoiceMessage_1.wav")
        model_size: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Dictionary with transcription results
    """
    # Construct full path
    data_folder = Path("data")
    file_path = data_folder / filename

    # Check if file exists
    if not file_path.exists():
        print(f"❌ Error: File '{filename}' not found in data folder")
        return None

    print(f"📁 File: {filename}")
    print(f"📊 Loading Whisper model: {model_size}...")

    # Load model
    model = whisper.load_model(model_size)

    print(f"🎤 Transcribing audio...")

    # Transcribe with settings for most accurate 1:1 transcription
    result = model.transcribe(
        str(file_path),
        language="de",  # Set to German, change if needed
        fp16=False,  # Set to False for CPU compatibility
        word_timestamps=True,  # Get word-level timestamps
        temperature=0.0,  # Deterministic output, no randomness
        compression_ratio_threshold=2.4,  # Stricter quality threshold
        logprob_threshold=-1.0,  # More strict confidence requirement
        no_speech_threshold=0.6,  # Better silence detection
        condition_on_previous_text=False,  # Don't skip initial audio based on context
    )

    return result


def main():
    """Main function with CLI argument support"""
    parser = argparse.ArgumentParser(
        description="Transcribe voice messages using Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py VoiceMessage_1.wav
  python3 main.py VoiceMessage_1.wav --model small
  python3 main.py VoiceMessage_1.wav --model large --save
  python3 main.py  (interactive mode)
        """
    )

    parser.add_argument(
        'filename',
        nargs='?',
        help='Voice message file from data folder (e.g., VoiceMessage_1.wav)'
    )
    parser.add_argument(
        '--model', '-m',
        default='small',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: small)'
    )
    parser.add_argument(
        '--save', '-s',
        action='store_true',
        help='Automatically save transcription to file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: transcription_<filename>.txt)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🎙️  Voice Message Transcription Tool")
    print("=" * 60)
    print()

    # Interactive mode if no filename provided
    if not args.filename:
        filename = input("Enter filename from data folder (e.g., VoiceMessage_1.wav): ").strip()
        if not filename:
            print("❌ No filename provided")
            sys.exit(1)
        print("\nAvailable models: tiny, base, small, medium, large")
        model_size = input(f"Choose model size (press Enter for '{args.model}'): ").strip() or args.model
    else:
        filename = args.filename
        model_size = args.model

    print("-" * 60)

    # Transcribe
    result = transcribe_file(filename, model_size)

    if result:
        print("\n" + "=" * 60)
        print("📝 TRANSCRIPTION RESULT:")
        print("=" * 60)
        print(result["text"])
        print("=" * 60)

        # Show detected language
        print(f"\n🌍 Detected language: {result.get('language', 'unknown')}")

        # Save to file
        if args.save or args.output:
            output_file = args.output or f"transcription_{filename}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result["text"])
            print(f"✅ Saved to {output_file}")
        elif not args.filename:  # Only ask in interactive mode
            save = input("\n💾 Save transcription to file? (y/n): ").strip().lower()
            if save == 'y':
                output_file = f"transcription_{filename}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result["text"])
                print(f"✅ Saved to {output_file}")


if __name__ == "__main__":
    main()
