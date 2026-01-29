"""
Microsoft 365 email client for voice message processing
"""
import logging
import re
import base64
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

    def get_or_create_parent_folder(self):
        """Get or create the parent transcription folder"""
        folder_name = Config.TRANSCRIPTION_FOLDER
        try:
            # Try to get existing folder at top level
            for folder in self.mailbox.get_folders():
                if folder.name == folder_name:
                    self.logger.debug(f"Found existing parent folder: {folder_name}")
                    return folder
            # Create at top level if not exists
            new_folder = self.mailbox.create_child_folder(folder_name)
            self.logger.info(f"Created parent folder: {folder_name}")
            return new_folder
        except Exception as e:
            self.logger.error(f"Error with parent folder: {e}")
            return None

    def get_or_create_processing_folder(self):
        """Get or create the processing folder for safe message handling"""
        parent = self.get_or_create_parent_folder()
        if not parent:
            return None

        folder_name = Config.PROCESSING_FOLDER
        try:
            # Try to get existing folder within parent
            for folder in parent.get_folders():
                if folder.name == folder_name:
                    self.logger.debug(f"Found existing processing folder: {folder_name}")
                    return folder
            # Create as child of parent if not exists
            new_folder = parent.create_child_folder(folder_name)
            self.logger.info(f"Created processing folder: {folder_name}")
            return new_folder
        except Exception as e:
            self.logger.error(f"Error with processing folder: {e}")
            return None

    def move_to_processing(self, message) -> bool:
        """Move message to processing folder before processing"""
        folder = self.get_or_create_processing_folder()
        if folder:
            try:
                message.move(folder)
                self.logger.info(f"Moved message to processing folder: {message.subject}")
                return True
            except Exception as e:
                self.logger.error(f"Error moving message to processing folder: {e}")
                return False
        return False

    def get_or_create_done_folder(self):
        """Get or create the done folder for processed messages"""
        parent = self.get_or_create_parent_folder()
        if not parent:
            return None

        folder_name = Config.DONE_FOLDER
        try:
            # Try to get existing folder within parent
            for folder in parent.get_folders():
                if folder.name == folder_name:
                    self.logger.debug(f"Found existing done folder: {folder_name}")
                    return folder
            # Create as child of parent if not exists
            new_folder = parent.create_child_folder(folder_name)
            self.logger.info(f"Created done folder: {folder_name}")
            return new_folder
        except Exception as e:
            self.logger.error(f"Error with done folder: {e}")
            return None

    def move_to_done(self, message) -> bool:
        """Move message to done folder after processing and mark as read"""
        folder = self.get_or_create_done_folder()
        if folder:
            try:
                # Mark as read before moving
                message.mark_as_read()
                message.move(folder)
                self.logger.info(f"Moved message to done folder (marked as read): {message.subject}")
                return True
            except Exception as e:
                self.logger.error(f"Error moving message to done folder: {e}")
                return False
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
            # Fetch unread messages from voicemail system only
            # Note: We can't use $orderby with complex $filter (causes "restriction too complex" error)
            # So we filter by sender and skip ordering - messages come in default order
            query = f"isRead eq false and from/emailAddress/address eq '{Config.VOICEMAIL_SENDER}'"
            self.logger.info(f"Query: {query}")
            messages = self.mailbox.get_messages(
                query=query,
                limit=Config.MAX_EMAILS_PER_RUN
                )

            # Filter for messages with attachments and WAV files
            messages_list = list(messages)
            self.logger.info(f"Total messages fetched: {len(messages_list)}")

            wav_messages = []

            for msg in messages_list:
                self.logger.info(f"Checking message: {msg.subject}, isRead: {msg.is_read}")

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

        except IndexError as e:
            import traceback
            self.logger.error(f"IndexError fetching messages (O365 library bug): {e}\n{traceback.format_exc()}")
            return []
        except Exception as e:
            import traceback
            self.logger.error(f"Error fetching messages: {e}\n{traceback.format_exc()}")
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
        Delete original email and create new one with transcription

        Args:
            message: O365 message object
            transcription_text: Transcription text to append
            marker: Transcription marker

        Returns:
            True if successful, False otherwise
        """
        try:
            # 1. Extract phone number from subject
            subject = message.subject or ""
            phone_match = re.search(r'\+\d+', subject)
            phone_number = phone_match.group() if phone_match else "Unbekannt"

            # 2. Get WAV attachment data (already downloaded)
            wav_attachments = []
            for attachment in message.attachments:
                if attachment.name.lower().endswith('.wav'):
                    content = attachment.content
                    if isinstance(content, str):
                        content = base64.b64decode(content)
                    wav_attachments.append((attachment.name, content))

            # 3. Format received date/time
            received_dt = message.received
            if received_dt:
                received_str = received_dt.strftime("%d.%m.%Y um %H:%M Uhr")
            else:
                received_str = "Unbekannt"

            # 4. Create new message FIRST
            new_msg = self.mailbox.new_message()
            new_msg.to.add(self.target_email)
            new_msg.subject = f"Transkribierte Sprachnachricht von {phone_number}"
            new_msg.body = f"Eingangsdatum Original: {received_str}<br><br>{marker}<br><br>{transcription_text}"

            # 4. Attach WAV files (save to temp file first, as O365 expects file path)
            import tempfile
            import os
            temp_files = []
            for filename, wav_data in wav_attachments:
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                with open(temp_path, 'wb') as f:
                    f.write(wav_data)
                temp_files.append(temp_path)
                new_msg.attachments.add(temp_path)

            # 5. Send new message - if this fails, original stays intact
            new_msg.send()
            self.logger.info(f"New message sent for {phone_number}")

            # 6. Wait for sync, then delete from Sent folder
            import time
            time.sleep(3)
            target_subject = f"Transkribierte Sprachnachricht von {phone_number}"

            # 6a. New message contains marker in body, so it will be filtered out by query

            # 6b. Delete from Sent folder
            try:
                sent_folder = self.mailbox.sent_folder()
                sent_messages = list(sent_folder.get_messages(limit=10, order_by='sentDateTime desc'))
                for sent_msg in sent_messages:
                    if sent_msg.subject == target_subject:
                        sent_msg.delete()
                        self.logger.info(f"Deleted message from Sent folder")
                        break
            except Exception as e:
                self.logger.warning(f"Could not delete from Sent folder: {e}")

            # 7. Clean up temp files
            for temp_path in temp_files:
                try:
                    os.remove(temp_path)
                except:
                    pass

            # 8. Move original to done folder AFTER successful send
            self.move_to_done(message)
            return True

        except Exception as e:
            self.logger.error(f"Error replacing message with transcription: {e}")
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

            # Move to processing folder first (prevents re-processing and data loss)
            if not self.move_to_processing(message):
                self.logger.error("Failed to move message to processing folder, skipping")
                return False

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
