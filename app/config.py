"""
Configuration management for email transcription service
"""
import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration loaded from environment variables"""

    # Microsoft 365 Authentication
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    TENANT_ID: str = os.getenv("TENANT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
    TARGET_EMAIL: str = os.getenv("TARGET_EMAIL", "")

    # Service Configuration
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "120"))
    MAX_EMAILS_PER_RUN: int = int(os.getenv("MAX_EMAILS_PER_RUN", "25"))
    VOICEMAIL_SENDER: str = os.getenv("VOICEMAIL_SENDER", "unityconnection@hosted-comm-service.a1.net")
    TRANSCRIPTION_FOLDER: str = os.getenv("TRANSCRIPTION_FOLDER", "Transkription")
    PROCESSING_FOLDER: str = os.getenv("PROCESSING_FOLDER", "In Bearbeitung")
    DONE_FOLDER: str = os.getenv("DONE_FOLDER", "Bereits transkripiert")
    START_DATE: str = os.getenv("START_DATE", "2024-01-01T00:00:00Z")

    # Whisper Model Configuration
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
    TRANSCRIPTION_MARKER: str = os.getenv(
        "TRANSCRIPTION_MARKER", "--- AUTOMATISCHES TRANSKRIPT ---"
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        """
        Validate required configuration parameters

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        errors = []

        # Required O365 credentials
        if not cls.CLIENT_ID:
            errors.append("CLIENT_ID is required")
        if not cls.TENANT_ID:
            errors.append("TENANT_ID is required")
        if not cls.CLIENT_SECRET:
            errors.append("CLIENT_SECRET is required")
        if not cls.TARGET_EMAIL:
            errors.append("TARGET_EMAIL is required")

        # Validate Whisper model choice
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if cls.WHISPER_MODEL not in valid_models:
            errors.append(
                f"WHISPER_MODEL must be one of {valid_models}, got '{cls.WHISPER_MODEL}'"
            )

        # Validate check interval
        if cls.CHECK_INTERVAL_SECONDS < 1:
            errors.append("CHECK_INTERVAL_SECONDS must be >= 1")

        # Validate START_DATE format
        try:
            datetime.fromisoformat(cls.START_DATE.replace("Z", "+00:00"))
        except ValueError:
            errors.append(
                f"START_DATE must be in ISO format (e.g., 2024-01-01T00:00:00Z), got '{cls.START_DATE}'"
            )

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    @classmethod
    def get_summary(cls) -> str:
        """Get configuration summary for logging (without secrets)"""
        return f"""
Configuration:
  Target Email: {cls.TARGET_EMAIL}
  Voicemail Sender: {cls.VOICEMAIL_SENDER}
  Transcription Folder: {cls.TRANSCRIPTION_FOLDER}
  Processing Folder: {cls.TRANSCRIPTION_FOLDER}/{cls.PROCESSING_FOLDER}
  Done Folder: {cls.TRANSCRIPTION_FOLDER}/{cls.DONE_FOLDER}
  Whisper Model: {cls.WHISPER_MODEL}
  Check Interval: {cls.CHECK_INTERVAL_SECONDS}s
  Max Emails per Run: {cls.MAX_EMAILS_PER_RUN}
  Start Date: {cls.START_DATE}
  Log Level: {cls.LOG_LEVEL}
  Transcription Marker: {cls.TRANSCRIPTION_MARKER}
"""
