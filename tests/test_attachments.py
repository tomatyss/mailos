"""Tests for the email attachment management system."""

import shutil
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from unittest import TestCase

from mailos.utils.attachment_utils import AttachmentManager


class TestAttachmentManager(TestCase):
    """Test cases for AttachmentManager functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create test directory
        self.test_dir = Path("test_attachments")
        self.test_dir.mkdir(exist_ok=True)

        # Initialize attachment manager
        self.manager = AttachmentManager(str(self.test_dir))

        # Test email data
        self.sender_email = "test@example.com"
        self.test_content = b"Test file content"

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_test_email_with_attachment(
        self, filename="test.txt", disposition="attachment"
    ):
        """Create a test email with an attachment."""
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Email"

        # Add text body
        msg.attach(MIMEText("Test email body"))

        # Add attachment
        attachment = MIMEApplication(self.test_content)
        attachment.add_header("Content-Disposition", disposition, filename=filename)
        msg.attach(attachment)

        return msg

    def test_attachment_extraction(self):
        """Test basic attachment extraction and storage."""
        # Create test email with explicit attachment
        email = self.create_test_email_with_attachment()
        attachments = self.manager.extract_attachments(email, self.sender_email)

        self.assertEqual(len(attachments), 1)
        self.assertTrue(attachments[0]["original_name"] == "test.txt")
        self.assertTrue(Path(attachments[0]["path"]).exists())

        # Verify content
        with open(attachments[0]["path"], "rb") as f:
            saved_content = f.read()
        self.assertEqual(saved_content, self.test_content)

    def test_inline_attachment(self):
        """Test extraction of inline attachments."""
        # Create test email with inline attachment
        email = self.create_test_email_with_attachment(disposition="inline")
        attachments = self.manager.extract_attachments(email, self.sender_email)

        self.assertEqual(len(attachments), 1)
        self.assertTrue(Path(attachments[0]["path"]).exists())

    def test_content_type_attachment(self):
        """Test extraction of attachment with filename in Content-Type."""
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Email"

        # Add attachment with filename in Content-Type
        attachment = MIMEApplication(self.test_content)
        # Set Content-Type with name parameter
        attachment.replace_header(
            "Content-Type", 'application/octet-stream; name="test.dat"'
        )
        # Also add a Content-Disposition without filename to test Content-Type fallback
        attachment.add_header("Content-Disposition", "attachment")
        msg.attach(attachment)

        attachments = self.manager.extract_attachments(msg, self.sender_email)

        self.assertEqual(len(attachments), 1)
        self.assertTrue(attachments[0]["original_name"] == "test.dat")
        self.assertTrue(Path(attachments[0]["path"]).exists())

    def test_multiple_attachments(self):
        """Test handling of multiple attachments."""
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Email"

        # Add multiple attachments
        filenames = ["test1.txt", "test2.txt", "test3.txt"]
        for filename in filenames:
            attachment = MIMEApplication(self.test_content)
            attachment.add_header(
                "Content-Disposition", "attachment", filename=filename
            )
            msg.attach(attachment)

        attachments = self.manager.extract_attachments(msg, self.sender_email)

        self.assertEqual(len(attachments), len(filenames))
        saved_names = [att["original_name"] for att in attachments]
        self.assertEqual(set(saved_names), set(filenames))
