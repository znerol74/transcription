"""
Microsoft 365 email client for voice message processing
"""
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from O365 import Account
from app.config import Config
from app.utils import format_email_summary, parse_iso_date


class EmailClient:
    """Client for Microsoft 365 email operations"""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str, target_email: str):
        """
        Initialize email client

        Args:
            client_id: Microsoft 365 app client ID
            client_secret: Microsoft 365 app client secret
            tenant_id: Microsoft 365 tenant ID
            target_email: Target mailbox email address
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.target_email = target_email
        self.logger = logging.getLogger("transcription_service")

        self.account = None
        self.mailbox = None

    def authenticate(self) -> bool:
        """
        Authenticate with Microsoft 365

        Returns:
            True if authentication successful, False otherwise
        """
        self.logger.info(f"Authenticating with Microsoft 365 for {self.target_email}")

        try:
            credentials = (self.client_id, self.client_secret)
            self.account = Account(
                credentials,
                auth_flow_type='credentials',
                tenant_id=self.tenant_id
            )

            if self.account.authenticate():
                self.logger.info("Authentication successful")
                self.mailbox = self.account.mailbox(resource=self.target_email)
                return True
            else:
                self.logger.error("Authentication failed")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def get_messages_with_wav(self, since_date: str = None) -> List:
        """
        Get messages with WAV attachments

        Args:
            since_date: ISO format date string (optional, not used - kept for compatibility)

        Returns:
            List of email messages
        """
        if not self.mailbox:
            self.logger.error("Mailbox not initialized. Call authenticate() first.")
            return []

        self.logger.info("Fetching recent messages with attachments")

        try:
            # Fetch recent messages like the test script does
            messages = self.mailbox.get_messages(
                query='isRead eq false',
                order_by='receivedDateTime desc',
                limit=2
                )

            # Filter for messages with attachments and WAV files
            messages_list = list(messages)
            self.logger.info(f"Total messages fetched: {len(messages_list)}")

            wav_messages = []

            for msg in messages_list:
                # Skip messages without attachments
                if not msg.has_attachments:
                    continue

                # Download attachments to check them (like the test script does)
                msg.attachments.download_attachments()

                for attachment in msg.attachments:
                    if attachment.name.lower().endswith('.wav'):
                        wav_messages.append(msg)
                        break

            self.logger.info(f"Found {len(wav_messages)} messages with WAV attachments")
            return wav_messages

        except Exception as e:
            self.logger.error(f"Error fetching messages: {e}")
            return []

    def _has_wav_attachment(self, message) -> bool:
        """
        Check if message has WAV attachments

        Args:
            message: O365 message object

        Returns:
            True if message has WAV attachments
        """
        if not message.has_attachments:
            return False

        try:
            for attachment in message.attachments:
                if attachment.name.lower().endswith('.wav'):
                    return True
        except:
            pass

        return False

    def has_transcription(self, message, marker: str) -> bool:
        """
        Check if message already has transcription marker

        Args:
            message: O365 message object
            marker: Transcription marker string

        Returns:
            True if marker exists in message body
        """
        try:
            body = message.body or ""
            return marker in body
        except Exception as e:
            self.logger.error(f"Error checking transcription marker: {e}")
            return False

    def download_wav_attachments(self, message) -> List[Tuple[str, bytes]]:
        """
        Download WAV attachments from message

        Args:
            message: O365 message object

        Returns:
            List of (filename, wav_data) tuples
        """
        wav_files = []

        try:
            if not message.has_attachments:
                return wav_files

            # Attachments already downloaded in get_messages_with_wav, just iterate
            seen_files = set()
            for attachment in message.attachments:
                if attachment.name.lower().endswith('.wav'):
                    # Skip duplicates
                    if attachment.name in seen_files:
                        continue
                    seen_files.add(attachment.name)

                    # Get attachment data - content may be base64 string or bytes
                    content = attachment.content
                    if isinstance(content, str):
                        import base64
                        content = base64.b64decode(content)
                    wav_files.append((attachment.name, content))
                    self.logger.debug(f"Downloaded WAV: {attachment.name} ({len(content)} bytes)")

        except Exception as e:
            self.logger.error(f"Error downloading attachments: {e}")

        return wav_files

    def append_transcription(self, message, transcription_text: str, marker: str) -> bool:
        """
        Reply to the email with the transcription (sends to ourselves, grouped as thread)

        Args:
            message: O365 message object
            transcription_text: Transcription text to append
            marker: Transcription marker

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a reply (this keeps the conversation thread)
            reply = message.reply()

            # Clear the default recipients (which would be the sender)
            reply.to.clear()

            # Send to ourselves instead
            reply.to.add(self.target_email)

            # Set the reply body with transcription
            reply_body = f"{marker}\n\n{transcription_text}"
            reply.body = reply_body

            # Send the reply
            reply.send()

            self.logger.info(f"Transcription reply sent to {self.target_email}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending transcription reply: {e}")
            return False

    def process_message(self, message, transcription_service, marker: str) -> bool:
        """
        Complete processing workflow for a single message

        Args:
            message: O365 message object
            transcription_service: TranscriptionService instance
            marker: Transcription marker

        Returns:
            True if processing successful, False otherwise
        """
        try:
            # Log message details
            summary = format_email_summary(
                message.subject or "(No Subject)",
                str(message.sender),
                message.received
            )
            self.logger.info(f"Processing message: {summary}")

            # Check if already transcribed
            if self.has_transcription(message, marker):
                self.logger.info("Message already has transcription, skipping")
                return True

            # Download WAV attachments
            wav_files = self.download_wav_attachments(message)

            if not wav_files:
                self.logger.warning("No WAV attachments found in message")
                return False

            # Transcribe all WAV files
            transcriptions = []
            for filename, wav_data in wav_files:
                text = transcription_service.transcribe_wav(wav_data, filename)
                if text:
                    transcriptions.append(text)

            if not transcriptions:
                self.logger.error("All transcriptions failed")
                return False

            # Combine transcriptions
            combined_text = "\n\n".join(transcriptions)

            # Append to email
            success = self.append_transcription(message, combined_text, marker)

            if success:
                self.logger.info(f"Successfully processed message with {len(wav_files)} WAV file(s)")
            else:
                self.logger.error("Failed to append transcription to message")

            return success

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return False
