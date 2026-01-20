"""
Utility functions for email transcription service
"""
import logging
import sys
from datetime import datetime
from typing import Optional


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure structured logging for the service

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("transcription_service")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 30s" or "45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.1f}s"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to max length with ellipsis

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with "..." if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def parse_iso_date(date_string: str) -> datetime:
    """
    Parse ISO format date string to datetime

    Args:
        date_string: ISO format date (e.g., "2024-01-01T00:00:00Z")

    Returns:
        datetime object

    Raises:
        ValueError: If date string is invalid
    """
    # Handle Z (UTC) timezone
    if date_string.endswith("Z"):
        date_string = date_string.replace("Z", "+00:00")

    return datetime.fromisoformat(date_string)


def format_email_summary(subject: str, sender: str, received: datetime) -> str:
    """
    Format email details for logging

    Args:
        subject: Email subject
        sender: Email sender
        received: Received datetime

    Returns:
        Formatted summary string
    """
    return f"'{truncate_text(subject, 50)}' from {sender} ({received.strftime('%Y-%m-%d %H:%M')})"
