#!/usr/bin/env python3
"""
Batch transcribe all voice messages in data folder
"""
import whisper
from pathlib import Path
from datetime import datetime


def main():
    """Transcribe all WAV files and save to one output file"""

    print("=" * 60)
    print("🎙️  Batch Voice Message Transcription")
    print("=" * 60)
    print()

    # Setup
    data_folder = Path("data")
    output_file = "all_transcriptions.txt"
    model_size = "large"  # Best quality

    # Find all WAV files
    wav_files = sorted(data_folder.glob("*.wav"))

    if not wav_files:
        print("❌ No WAV files found in data folder")
        return

    print(f"Found {len(wav_files)} voice messages")
    print(f"Using model: {model_size}")
    print(f"Output file: {output_file}")
    print()
    print("-" * 60)

    # Load model once
    print(f"📊 Loading Whisper {model_size} model...")
    model = whisper.load_model(model_size)
    print("✅ Model loaded")
    print()

    # Open output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write("VOICE MESSAGE TRANSCRIPTIONS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model: Whisper {model_size}\n")
        f.write(f"Total files: {len(wav_files)}\n")
        f.write("=" * 80 + "\n\n")

        # Transcribe each file
        for i, wav_file in enumerate(wav_files, 1):
            print(f"[{i}/{len(wav_files)}] Processing: {wav_file.name}")

            try:
                # Transcribe
                result = model.transcribe(
                    str(wav_file),
                    language="de",
                    fp16=False,
                    word_timestamps=True,
                    temperature=0.0,
                    compression_ratio_threshold=2.4,
                    logprob_threshold=-1.0,
                    no_speech_threshold=0.6,
                    condition_on_previous_text=False
                )

                # Write to file
                f.write("-" * 80 + "\n")
                f.write(f"FILE: {wav_file.name}\n")
                f.write(f"LANGUAGE: {result.get('language', 'unknown')}\n")
                f.write("-" * 80 + "\n")
                f.write(result["text"].strip() + "\n")
                f.write("\n\n")

                # Print preview
                print(f"   ✅ Done: {result['text'][:60]}...")
                print()

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                print(f"   {error_msg}")
                f.write(f"ERROR: {error_msg}\n\n")

    print("=" * 60)
    print(f"✅ All transcriptions saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
