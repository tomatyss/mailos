"""Utilities for handling email attachments."""

import hashlib
import os
import re
from email.message import Message
from pathlib import Path
from typing import Dict, List, Optional

from mailos.utils.logger_utils import logger


class AttachmentManager:
    """Manages email attachments including extraction, storage, and organization."""

    def __init__(self, base_storage_path: str = "attachments"):
        """Initialize the attachment manager.

        Args:
            base_storage_path: Base directory for storing attachments
        """
        self.base_path = Path(base_storage_path)
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """Create the base storage directory if it doesn't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_sender_directory(self, sender_email: str) -> Path:
        """Get the directory path for a specific sender.

        Args:
            sender_email: Email address of the sender

        Returns:
            Path object for the sender's directory
        """
        # Create a safe directory name from the email address
        safe_name = sender_email.replace("@", "_at_").replace(".", "_")
        sender_dir = self.base_path / safe_name
        sender_dir.mkdir(parents=True, exist_ok=True)
        return sender_dir

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

                # Generate unique filename
                unique_filename = self._generate_unique_filename(filename, content)
                file_path = sender_dir / unique_filename

                # Save the file
                with open(file_path, "wb") as f:
                    f.write(content)

                # Verify file integrity
                if not self._verify_file_integrity(file_path, content):
                    raise Exception("File integrity verification failed")

                # Record successful save
                saved_attachments.append(
                    {
                        "original_name": filename,
                        "saved_name": unique_filename,
                        "path": str(file_path),
                        "size": len(content),
                        "type": part.get_content_type(),
                    }
                )

                logger.info(
                    f"Successfully saved attachment: {filename} -> {unique_filename}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to save attachment "
                    f"{filename if 'filename' in locals() else 'unknown'}: {e}",
                    exc_info=True,
                )
                # Clean up failed save attempt
                if "file_path" in locals() and file_path.exists():
                    file_path.unlink()

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
