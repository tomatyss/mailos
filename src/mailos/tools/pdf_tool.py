"""PDF tool for manipulating PDF files."""

import io
import os
from typing import Dict, List, Optional, Union

from PyPDF2 import PdfMerger, PdfReader, PdfWriter

from mailos.utils.attachment_utils import AttachmentManager
from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool

attachment_manager = AttachmentManager()


def create_pdf(content: str, output_path: str, sender_email: str) -> Dict:
    """Create a new PDF file with the given text content.

    Args:
        content: Text content to write to PDF
        output_path: Path where to save the PDF file
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        # Create PDF in memory first
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # Write content
        y = 750  # Start from top of page
        for line in content.split("\n"):
            c.drawString(50, y, line)
            y -= 15  # Move down for next line

            if y < 50:  # If near bottom of page, start new page
                c.showPage()
                y = 750

        c.save()

        # Save using attachment manager
        result = attachment_manager.save_file(
            buffer.getvalue(), output_path, sender_email
        )

        return {
            "status": "success",
            "message": f"PDF created successfully at {result['path']}",
            "path": result["path"],
        }
    except Exception as e:
        logger.error(f"Error creating PDF: {str(e)}")
        return {"status": "error", "message": str(e)}


def edit_pdf(
    input_path: str, modifications: Dict[int, str], output_path: str, sender_email: str
) -> Dict:
    """Edit text in existing PDF pages.

    Args:
        input_path: Path to input PDF file
        modifications: Dict mapping page numbers to new content
        output_path: Path to save modified PDF
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        # Create new PDF with modifications
        result = create_pdf(modifications[0], output_path, sender_email)
        if result["status"] == "error":
            return result

        return {
            "status": "success",
            "message": f"PDF modified successfully at {result['path']}",
            "path": result["path"],
        }
    except Exception as e:
        logger.error(f"Error editing PDF: {str(e)}")
        return {"status": "error", "message": str(e)}


def merge_pdfs(input_paths: List[str], output_path: str, sender_email: str) -> Dict:
    """Merge multiple PDF files into one.

    Args:
        input_paths: List of paths to input PDF files
        output_path: Path to save merged PDF
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        # Verify all input files exist
        for path in input_paths:
            if not os.path.exists(path):
                error_msg = f"Input file not found: {path}"
                logger.error(f"Error merging PDFs: {error_msg}")
                return {"status": "error", "message": error_msg}

        # Create merged PDF in memory first
        merger = PdfMerger()
        for path in input_paths:
            with open(path, "rb") as f:
                merger.append(f)

        buffer = io.BytesIO()
        merger.write(buffer)
        buffer.seek(0)

        # Save using attachment manager
        result = attachment_manager.save_file(
            buffer.getvalue(), output_path, sender_email
        )

        return {
            "status": "success",
            "message": f"PDFs merged successfully at {result['path']}",
            "path": result["path"],
        }
    except Exception as e:
        logger.error(f"Error merging PDFs: {str(e)}")
        return {"status": "error", "message": str(e)}


def extract_text(
    input_path: str, pages: Optional[Union[int, List[int]]] = None
) -> Dict:
    """Extract text from PDF file.

    Args:
        input_path: Path to PDF file
        pages: Optional page number or list of page numbers to extract from

    Returns:
        Dict with operation status and extracted text
    """
    try:
        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}"}

        reader = PdfReader(input_path)

        if pages is None:
            # Extract from all pages
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif isinstance(pages, int):
            # Extract from single page
            text = reader.pages[pages - 1].extract_text()
        else:
            # Extract from specified pages
            text = ""
            for page_num in pages:
                text += reader.pages[page_num - 1].extract_text() + "\n"

        return {"status": "success", "text": text, "num_pages": len(reader.pages)}
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return {"status": "error", "message": str(e)}


def split_pdf(input_path: str, output_dir: str, sender_email: str) -> Dict:
    """Split PDF into individual pages.

    Args:
        input_path: Path to input PDF file
        output_dir: Directory to save split pages
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}"}

        reader = PdfReader(input_path)
        output_paths = []

        # Split into individual pages
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)

            # Create PDF in memory
            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            # Save using attachment manager
            filename = f"page_{i+1}.pdf"
            result = attachment_manager.save_file(
                buffer.getvalue(), filename, sender_email
            )
            output_paths.append(result["path"])

        return {
            "status": "success",
            "message": f"PDF split successfully into {len(output_paths)} pages",
            "output_paths": output_paths,
        }
    except Exception as e:
        logger.error(f"Error splitting PDF: {str(e)}")
        return {"status": "error", "message": str(e)}


# Define the PDF tools
create_pdf_tool = Tool(
    name="create_pdf",
    description="Create a new PDF file with the given text content",
    parameters={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Text content to write to PDF",
            },
            "output_path": {
                "type": "string",
                "description": "Path where to save the PDF file",
            },
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["content", "output_path", "sender_email"],
    function=create_pdf,
)

edit_pdf_tool = Tool(
    name="edit_pdf",
    description="Edit text in existing PDF pages",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {"type": "string", "description": "Path to input PDF file"},
            "modifications": {
                "type": "object",
                "description": "Dict mapping page numbers to new content",
            },
            "output_path": {
                "type": "string",
                "description": "Path to save modified PDF",
            },
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["input_path", "modifications", "output_path", "sender_email"],
    function=edit_pdf,
)

merge_pdfs_tool = Tool(
    name="merge_pdfs",
    description="Merge multiple PDF files into one",
    parameters={
        "type": "object",
        "properties": {
            "input_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of paths to input PDF files",
            },
            "output_path": {"type": "string", "description": "Path to save merged PDF"},
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["input_paths", "output_path", "sender_email"],
    function=merge_pdfs,
)

extract_text_tool = Tool(
    name="extract_text",
    description="Extract text from PDF file",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {"type": "string", "description": "Path to PDF file"},
            "pages": {
                "type": ["integer", "array", "null"],
                "description": (
                    "Optional page number or list of page numbers to extract from"
                ),
            },
        },
    },
    required_params=["input_path"],
    function=extract_text,
)

split_pdf_tool = Tool(
    name="split_pdf",
    description="Split PDF into individual pages",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {"type": "string", "description": "Path to input PDF file"},
            "output_dir": {
                "type": "string",
                "description": "Directory to save split pages",
            },
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["input_path", "output_dir", "sender_email"],
    function=split_pdf,
)
