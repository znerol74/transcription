"""
Main entry point for email voice message transcription service
"""
import argparse
import logging
import signal
import sys
import time
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Config
from app.email_client import EmailClient
from app.transcription import TranscriptionService
from app.utils import setup_logging, format_duration


class TranscriptionServiceApp:
    """Main application for email transcription service"""

    def __init__(self):
        """Initialize application"""
        # Setup logging
        self.logger = setup_logging(Config.LOG_LEVEL)
        self.logger.info("=" * 60)
        self.logger.info("Email Voice Message Transcription Service")
        self.logger.info("=" * 60)

        # Validate configuration
        try:
            Config.validate()
            self.logger.info(Config.get_summary())
        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            sys.exit(1)

        # Initialize services
        self.transcription_service: Optional[TranscriptionService] = None
        self.email_client: Optional[EmailClient] = None
        self.scheduler: Optional[BlockingScheduler] = None
        self.should_stop = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.should_stop = True
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def initialize_services(self):
        """Initialize transcription and email services"""
        self.logger.info("Initializing services...")

        # Initialize transcription service (loads model)
        try:
            self.transcription_service = TranscriptionService(Config.WHISPER_MODEL)
        except Exception as e:
            self.logger.error(f"Failed to initialize transcription service: {e}")
            sys.exit(1)

        # Initialize email client
        self.email_client = EmailClient(
            client_id=Config.CLIENT_ID,
            client_secret=Config.CLIENT_SECRET,
            tenant_id=Config.TENANT_ID,
            target_email=Config.TARGET_EMAIL
        )

        # Authenticate
        if not self.email_client.authenticate():
            self.logger.error("Email authentication failed")
            sys.exit(1)

        self.logger.info("Services initialized successfully")

    def process_emails(self):
        """Process all pending emails with WAV attachments"""
        self.logger.info("-" * 60)
        self.logger.info("Starting email processing run")
        start_time = time.time()

        try:
            # Get messages since configured start date
            messages = self.email_client.get_messages_with_wav(Config.START_DATE)

            if not messages:
                self.logger.info("No messages to process")
                return

            # Process each message
            processed = 0
            skipped = 0
            failed = 0

            for msg in messages:
                if self.should_stop:
                    self.logger.info("Stop requested, halting email processing")
                    break

                try:
                    success = self.email_client.process_message(
                        msg,
                        self.transcription_service,
                        Config.TRANSCRIPTION_MARKER
                    )

                    if success:
                        processed += 1
                    else:
                        # Check if it was skipped (already had transcription)
                        if self.email_client.has_transcription(msg, Config.TRANSCRIPTION_MARKER):
                            skipped += 1
                        else:
                            failed += 1

                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    failed += 1

            # Summary
            duration = time.time() - start_time
            self.logger.info("-" * 60)
            self.logger.info(
                f"Processing complete in {format_duration(duration)}: "
                f"{processed} processed, {skipped} skipped, {failed} failed"
            )
            self.logger.info("-" * 60)

        except Exception as e:
            self.logger.error(f"Error in email processing run: {e}")

    def run_once(self):
        """Run service once and exit (scheduled job mode)"""
        self.logger.info("Running in ONCE mode (scheduled job)")

        self.initialize_services()
        self.process_emails()

        self.logger.info("Execution complete, exiting")

    def run_daemon(self):
        """Run service as daemon with internal scheduling"""
        self.logger.info(f"Running in DAEMON mode (interval: {Config.CHECK_INTERVAL_SECONDS}s)")

        self.initialize_services()

        # Setup scheduler
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(
            self.process_emails,
            trigger=IntervalTrigger(seconds=Config.CHECK_INTERVAL_SECONDS),
            id='process_emails',
            name='Process email voice messages',
            max_instances=1  # Prevent concurrent executions
        )

        # Run first job immediately
        self.logger.info("Running initial email processing...")
        self.process_emails()

        # Start scheduler
        self.logger.info("Starting scheduler...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Email Voice Message Transcription Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  once   - Run once and exit (for cron/scheduled jobs) [DEFAULT]
  daemon - Run continuously with internal scheduler

Examples:
  # Run once (for external scheduling via cron/systemd/k8s)
  python -m app.main --mode once

  # Run as daemon (self-contained with internal scheduler)
  python -m app.main --mode daemon

Environment Variables:
  See .env.example for required configuration
        """
    )

    parser.add_argument(
        '--mode',
        choices=['once', 'daemon'],
        default='once',
        help='Execution mode (default: once)'
    )

    args = parser.parse_args()

    # Create and run application
    app = TranscriptionServiceApp()

    if args.mode == 'once':
        app.run_once()
    elif args.mode == 'daemon':
        app.run_daemon()


if __name__ == "__main__":
    main()
