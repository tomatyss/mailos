"""Utilities for handling email attachments."""

import hashlib
import mimetypes
import os
import re
from email.message import Message
from pathlib import Path
from typing import Dict, List, Optional

from mailos.utils.config_utils import get_attachment_settings
from mailos.utils.logger_utils import logger


def extract_email_address(email_string: str) -> str:
    """Extract pure email address from a string that might include a display name.

    Args:
        email_string: String that might be "Name <email>" or just "email"

    Returns:
        Pure email address
    """
    match = re.search(r"<([^>]+)>", email_string)
    if match:
        return match.group(1)

    # If no angle brackets, try to match just the email address
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", email_string)
    if match:
        return match.group(0)

    # If no email pattern found, return the original string
    return email_string


class AttachmentManager:
    """Manages email attachments including extraction, storage, and organization."""

    def __init__(self, base_storage_path: Optional[str] = None):
        """Initialize the attachment manager.

        Args:
            base_storage_path: Optional override for the base storage path
                       (used in testing)
        """
        if base_storage_path is None:
            settings = get_attachment_settings()
            self.base_path = Path(settings["base_storage_path"])
        else:
            self.base_path = Path(base_storage_path)
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """Create the base storage directory if it doesn't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_sender_directory(self, sender_email: str) -> Path:
        """Get the directory path for a specific sender.

        Args:
            sender_email: Email address of the sender (might include display name)

        Returns:
            Path object for the sender's directory
        """
        # Extract pure email address
        email = extract_email_address(sender_email)

        # Create a safe directory name from the email address
        safe_name = email.replace("@", "_at_").replace(".", "_")
        sender_dir = self.base_path / safe_name
        sender_dir.mkdir(parents=True, exist_ok=True)
        return sender_dir

    def _get_mime_type(self, filename: str, content_type: Optional[str] = None) -> str:
        """Get MIME type for a file.

        Args:
            filename: Name of the file
            content_type: Optional Content-Type from email part

        Returns:
            MIME type string
        """
        # First try the provided Content-Type
        if content_type:
            # Extract base mime type without parameters
            match = re.match(r"^([^;]+)", content_type)
            if match:
                return match.group(1).strip()

        # Then try to guess from file extension
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type

        # Default to application/octet-stream if type cannot be determined
        return "application/octet-stream"

    def save_file(
        self,
        content: bytes,
        filename: str,
        sender_email: str,
        content_type: Optional[str] = None,
    ) -> Dict:
        """Save a file to the sender's directory.

        Args:
            content: File content in bytes
            filename: Original filename
            sender_email: Email address of the sender
            content_type: Optional Content-Type from email part

        Returns:
            Dict containing file metadata
        """
        try:
            sender_dir = self._get_sender_directory(sender_email)
            unique_filename = self._generate_unique_filename(filename, content)
            file_path = sender_dir / unique_filename

            # Save the file
            with open(file_path, "wb") as f:
                f.write(content)

            # Verify file integrity
            if not self._verify_file_integrity(file_path, content):
                raise Exception("File integrity verification failed")

            # Get correct MIME type, preferring Content-Type from email
            mime_type = self._get_mime_type(filename, content_type)
            logger.debug(
                f"Determined MIME type for {filename}: {mime_type} "
                f"(from {'Content-Type header' if content_type else 'file extension'})"
            )

            return {
                "original_name": filename,
                "saved_name": unique_filename,
                "path": str(file_path),
                "size": len(content),
                "type": mime_type,
            }

        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            # Clean up failed save attempt
            if "file_path" in locals() and file_path.exists():
                file_path.unlink()
            raise

    def _generate_unique_filename(self, original_name: str, file_content: bytes) -> str:
        """Generate a unique filename using content hash to prevent duplicates.

        Args:
            original_name: Original filename
            file_content: File content in bytes

        Returns:
            Unique filename
        """
        # Get file extension
        name, ext = os.path.splitext(original_name)

        # Generate content hash
        content_hash = hashlib.sha256(file_content).hexdigest()[:8]

        # Create unique filename
        return f"{name}_{content_hash}{ext}"

    def _verify_file_integrity(self, file_path: Path, original_content: bytes) -> bool:
        """Verify the integrity of a saved file.

        Args:
            file_path: Path to the saved file
            original_content: File content in bytes

        Returns:
            True if file integrity is verified, False otherwise
        """
        try:
            with open(file_path, "rb") as f:
                saved_content = f.read()
            return (
                hashlib.sha256(saved_content).hexdigest()
                == hashlib.sha256(original_content).hexdigest()
            )
        except Exception as e:
            logger.error(f"Failed to verify file integrity: {e}")
            return False

    def _get_filename_from_headers(self, part: Message) -> Optional[str]:
        """Extract filename from message part headers.

        Args:
            part: Email message part

        Returns:
            Filename if found, None otherwise
        """
        # Try Content-Disposition first
        content_disp = part.get("Content-Disposition", "")
        filename = None

        if content_disp:
            # Look for filename in Content-Disposition
            match = re.search(r'filename=["\']?([^"\';]+)["\']?', content_disp, re.I)
            if match:
                filename = match.group(1)

        if not filename:
            # Try Content-Type if no filename in Content-Disposition
            content_type = part.get("Content-Type", "")
            # Look for name parameter in Content-Type
            match = re.search(r'name=["\']?([^"\';]+)["\']?', content_type, re.I)
            if match:
                filename = match.group(1)

        return filename

    def _is_attachment(self, part: Message) -> bool:
        """Check if the message part is an attachment.

        Args:
            part: Email message part

        Returns:
            True if the part is an attachment, False otherwise
        """
        if part.get_content_maintype() == "multipart":
            return False

        content_disp = part.get("Content-Disposition", "")
        if content_disp:
            # Check if it's explicitly marked as an attachment or inline
            if content_disp.lower().startswith(("attachment", "inline")):
                return True

        # Check for filename in either header
        filename = self._get_filename_from_headers(part)
        if filename:
            return True

        return False

    def extract_attachments(
        self, email_message: Message, sender_email: str
    ) -> List[Dict]:
        """Extract and save attachments from an email message.

        Args:
            email_message: Email message object
            sender_email: Email address of the sender

        Returns:
            List of dictionaries containing attachment metadata
        """
        saved_attachments = []
        sender_dir = self._get_sender_directory(sender_email)

        for part in email_message.walk():
            logger.debug(
                f"Processing part: Content-Type={part.get_content_type()}, "
                f"Content-Disposition={part.get('Content-Disposition')}"
            )

            if not self._is_attachment(part):
                continue

            try:
                # Get filename from headers
                filename = self._get_filename_from_headers(part)
                if not filename:
                    logger.debug("No filename found for attachment")
                    continue

                # Get content and decode if necessary
                content = part.get_payload(decode=True)
                if not content:
                    logger.debug("No content found for attachment")
                    continue

                logger.info(f"Processing attachment: {filename}")

                # Save the file using the common save_file method
                # Pass the Content-Type from the email part
                attachment_info = self.save_file(
                    content,
                    filename,
                    sender_email,
                    content_type=part.get_content_type(),
                )
                saved_attachments.append(attachment_info)

                logger.info(
                    f"Successfully saved attachment: {filename} -> "
                    f"{attachment_info['saved_name']} ({attachment_info['type']})"
                )

            except Exception as e:
                logger.error(
                    f"Failed to save attachment "
                    f"{filename if 'filename' in locals() else 'unknown'}: {e}",
                    exc_info=True,
                )

        return saved_attachments

    def manage_storage_space(self, max_size_gb: float = 10.0) -> None:
        """Manage storage space by removing old files if needed.

        Args:
            max_size_gb: Maximum allowed storage size in gigabytes
        """
        try:
            # Get total size
            total_size = sum(
                f.stat().st_size for f in self.base_path.rglob("*") if f.is_file()
            )

            # Convert to GB
            total_size_gb = total_size / (1024 * 1024 * 1024)

            if total_size_gb > max_size_gb:
                # Get all files with their modification times
                files = [
                    (f, f.stat().st_mtime)
                    for f in self.base_path.rglob("*")
                    if f.is_file()
                ]

                # Sort by modification time (oldest first)
                files.sort(key=lambda x: x[1])

                # Remove files until we're under the limit
                for file_path, _ in files:
                    if total_size_gb <= max_size_gb:
                        break

                    file_size = file_path.stat().st_size / (1024 * 1024 * 1024)
                    try:
                        file_path.unlink()
                        total_size_gb -= file_size
                        logger.info(f"Removed old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove file {file_path}: {e}")

        except Exception as e:
            logger.error(f"Failed to manage storage space: {e}")
