"""
Whisper transcription service for voice messages
"""
import io
import logging
import whisper
from typing import Optional
import time


class TranscriptionService:
    """Service for transcribing audio files using Whisper"""

    def __init__(self, model_name: str = "small"):
        """
        Initialize transcription service and load Whisper model

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.logger = logging.getLogger("transcription_service")
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load Whisper model into memory"""
        self.logger.info(f"Loading Whisper model: {self.model_name}")
        start_time = time.time()

        try:
            self.model = whisper.load_model(self.model_name)
            load_time = time.time() - start_time
            self.logger.info(f"Model loaded successfully in {load_time:.2f}s")
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe_wav(self, wav_data: bytes, filename: str = "audio.wav") -> Optional[str]:
        """
        Transcribe WAV audio data

        Args:
            wav_data: WAV file bytes
            filename: Original filename (for logging)

        Returns:
            Transcribed text or None if transcription fails
        """
        if self.model is None:
            self.logger.error("Whisper model not loaded")
            return None

        self.logger.info(f"Transcribing: {filename} ({len(wav_data)} bytes)")
        start_time = time.time()

        try:
            # Save WAV data to temporary file-like object
            # Whisper expects a file path, so we'll save temporarily
            temp_path = f"/tmp/{filename}"
            with open(temp_path, 'wb') as f:
                f.write(wav_data)

            # Transcribe with optimized settings
            result = self.model.transcribe(
                temp_path,
                language="de",  # German
                fp16=False,  # CPU compatibility
                word_timestamps=True,  # Word-level timestamps
                temperature=0.0,  # Deterministic output
                compression_ratio_threshold=2.4,  # Stricter quality
                logprob_threshold=-1.0,  # Confidence requirement
                no_speech_threshold=0.6,  # Better silence detection
                condition_on_previous_text=False  # Don't skip initial audio
            )

            transcription_time = time.time() - start_time
            text = result["text"].strip()

            self.logger.info(
                f"Transcription complete in {transcription_time:.2f}s: "
                f"{text[:60]}{'...' if len(text) > 60 else ''}"
            )

            # Clean up temporary file
            import os
            try:
                os.remove(temp_path)
            except:
                pass

            return text

        except Exception as e:
            self.logger.error(f"Transcription failed for {filename}: {e}")
            return None

    def transcribe_multiple(self, wav_files: list[tuple[str, bytes]]) -> dict[str, Optional[str]]:
        """
        Transcribe multiple WAV files

        Args:
            wav_files: List of (filename, wav_data) tuples

        Returns:
            Dictionary mapping filename to transcription text
        """
        results = {}

        for filename, wav_data in wav_files:
            text = self.transcribe_wav(wav_data, filename)
            results[filename] = text

        return results
