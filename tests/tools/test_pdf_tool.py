"""Test the PDF tool functionality."""

import io
import os
import re

import pytest
from PyPDF2 import PdfReader

from mailos.tools.pdf_tool import (
    create_pdf,
    edit_pdf,
    extract_text,
    merge_pdfs,
    split_pdf,
)


def verify_pdf_content(pdf_bytes, expected_content=None):
    """Verify PDF content without printing bytes."""
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(pdf_reader.pages) > 0
    if expected_content:
        extracted_text = pdf_reader.pages[0].extract_text()
        # Normalize both texts for comparison
        extracted_text = re.sub(r"\s+", " ", extracted_text).strip()
        expected_text = re.sub(r"\s+", " ", expected_content).strip()
        # Handle special characters by comparing normalized versions
        if any(char in expected_content for char in "®©™€"):
            # Keep punctuation but normalize whitespace
            assert expected_text in extracted_text
        else:
            assert expected_text in extracted_text
    return True


def test_create_pdf_success(mock_attachment_manager, tmp_path):
    """Test successful PDF creation with content verification."""
    content = "Test PDF Content\nLine 2\nLine 3"
    output_path = str(tmp_path / "output.pdf")
    sender_email = "test@example.com"

    # Mock the saved file content
    pdf_bytes = None

    def mock_save(content_bytes, *args):
        nonlocal pdf_bytes
        pdf_bytes = content_bytes
        # Actually write the file for other tests that might need it
        with open(output_path, "wb") as f:
            f.write(content_bytes)
        return {"path": output_path}

    mock_attachment_manager.save_file.side_effect = mock_save

    result = create_pdf(content, output_path, sender_email)

    assert result["status"] == "success"
    assert "PDF created successfully" in result["message"]
    mock_attachment_manager.save_file.assert_called_once()
    assert verify_pdf_content(pdf_bytes, content)


def test_create_pdf_with_special_chars(mock_attachment_manager, tmp_path):
    """Test PDF creation with special characters and content verification."""
    content = "Special chars: àéîøü\n€$¥£\nSymbols: ©®™"
    output_path = str(tmp_path / "special.pdf")
    sender_email = "test@example.com"

    # Mock the saved file content
    pdf_bytes = None

    def mock_save(content_bytes, *args):
        nonlocal pdf_bytes
        pdf_bytes = content_bytes
        # Actually write the file for other tests that might need it
        with open(output_path, "wb") as f:
            f.write(content_bytes)
        return {"path": output_path}

    mock_attachment_manager.save_file.side_effect = mock_save

    result = create_pdf(content, output_path, sender_email)

    assert result["status"] == "success"
    mock_attachment_manager.save_file.assert_called_once()
    assert verify_pdf_content(pdf_bytes, content)


def test_create_pdf_error_handling(mock_attachment_manager, tmp_path):
    """Test error handling in PDF creation."""
    mock_attachment_manager.save_file.side_effect = Exception("Save error")
    output_path = str(tmp_path / "error.pdf")

    result = create_pdf("content", output_path, "test@example.com")

    assert result["status"] == "error"
    assert "Save error" in result["message"]


def test_edit_pdf_success(mock_attachment_manager, temp_pdf):
    """Test successful PDF editing with content verification."""
    modifications = {0: "New content for first page"}
    output_path = "edited.pdf"
    sender_email = "test@example.com"

    # Mock the saved file content
    pdf_bytes = None

    def mock_save(content_bytes, *args):
        nonlocal pdf_bytes
        pdf_bytes = content_bytes
        return {"path": output_path}

    mock_attachment_manager.save_file.side_effect = mock_save

    result = edit_pdf(temp_pdf, modifications, output_path, sender_email)

    assert result["status"] == "success"
    assert "PDF modified successfully" in result["message"]
    assert verify_pdf_content(pdf_bytes, "New content for first page")


def test_edit_pdf_invalid_page(mock_attachment_manager, temp_pdf):
    """Test editing PDF with invalid page number."""
    modifications = {999: "Content for nonexistent page"}
    output_path = "invalid_page.pdf"

    result = edit_pdf(temp_pdf, modifications, output_path, "test@example.com")

    assert result["status"] == "error"


def test_merge_pdfs_success(mock_attachment_manager, temp_pdf, tmp_path):
    """Test successful PDF merging with content verification."""
    # Create a second PDF with distinct content
    second_pdf = str(tmp_path / "second.pdf")
    second_content = "Second PDF content"

    # Create the second PDF file
    create_result = create_pdf(second_content, second_pdf, "test@example.com")
    assert create_result["status"] == "success"
    assert os.path.exists(create_result["path"])

    # Mock the saved file content for merge
    pdf_bytes = None
    merged_path = str(tmp_path / "merged.pdf")

    def mock_save(content_bytes, *args):
        nonlocal pdf_bytes
        pdf_bytes = content_bytes
        # Actually write the file
        with open(merged_path, "wb") as f:
            f.write(content_bytes)
        return {"path": merged_path}

    mock_attachment_manager.save_file.side_effect = mock_save

    # Use the paths from the create_pdf results
    result = merge_pdfs(
        [temp_pdf, create_result["path"]], merged_path, "test@example.com"
    )

    assert result["status"] == "success"
    assert "PDFs merged successfully" in result["message"]
    mock_attachment_manager.save_file.assert_called()
    assert verify_pdf_content(pdf_bytes)


def test_merge_pdfs_invalid_input(mock_attachment_manager):
    """Test merging with invalid input files."""
    result = merge_pdfs(
        ["nonexistent1.pdf", "nonexistent2.pdf"], "merged.pdf", "test@example.com"
    )

    assert result["status"] == "error"


def test_extract_text_success(temp_pdf):
    """Test successful text extraction with content verification."""
    result = extract_text(temp_pdf)

    assert result["status"] == "success"
    assert "text" in result
    assert isinstance(result["text"], str)
    assert result["num_pages"] > 0
    assert len(result["text"].strip()) > 0


def test_extract_text_specific_page(temp_pdf):
    """Test extracting text from specific page with content verification."""
    result = extract_text(temp_pdf, pages=1)

    assert result["status"] == "success"
    assert "text" in result
    assert len(result["text"].strip()) > 0


def test_extract_text_multiple_pages(temp_pdf):
    """Test extracting text from multiple pages with content verification."""
    result = extract_text(temp_pdf, pages=[1])

    assert result["status"] == "success"
    assert "text" in result
    assert len(result["text"].strip()) > 0


def test_extract_text_invalid_file():
    """Test text extraction from invalid file."""
    result = extract_text("nonexistent.pdf")

    assert result["status"] == "error"


def test_split_pdf_success(mock_attachment_manager, temp_pdf):
    """Test successful PDF splitting with content verification."""
    # Mock the saved file content
    saved_pdfs = []

    def mock_save(content_bytes, *args):
        saved_pdfs.append(content_bytes)
        return {"path": f"page_{len(saved_pdfs)}.pdf"}

    mock_attachment_manager.save_file.side_effect = mock_save

    result = split_pdf(temp_pdf, "split_output", "test@example.com")

    assert result["status"] == "success"
    assert "PDF split successfully" in result["message"]
    assert "output_paths" in result
    assert isinstance(result["output_paths"], list)

    # Verify each split PDF is valid
    for pdf_bytes in saved_pdfs:
        assert verify_pdf_content(pdf_bytes)


def test_split_pdf_invalid_file(mock_attachment_manager):
    """Test splitting invalid PDF file."""
    result = split_pdf("nonexistent.pdf", "split_output", "test@example.com")

    assert result["status"] == "error"


@pytest.mark.parametrize(
    "content,expected_success",
    [
        ("Simple text", True),
        ("Multi\nline\ntext", True),
        ("", True),  # Empty content
        ("A" * 100, True),  # Moderate size content
        ("Special chars: ®©™€", True),  # Special characters
        ("Mixed content: 123 !@# αβγ", True),  # Mixed content
    ],
)
def test_create_pdf_various_content(
    mock_attachment_manager, tmp_path, content, expected_success
):
    """Test PDF creation with various types of content and content verification."""
    output_path = str(tmp_path / "test.pdf")

    # Mock the saved file content
    pdf_bytes = None

    def mock_save(content_bytes, *args):
        nonlocal pdf_bytes
        pdf_bytes = content_bytes
        # Actually write the file
        with open(output_path, "wb") as f:
            f.write(content_bytes)
        return {"path": output_path}

    mock_attachment_manager.save_file.side_effect = mock_save

    result = create_pdf(content, output_path, "test@example.com")

    assert (result["status"] == "success") == expected_success
    if expected_success:
        assert verify_pdf_content(pdf_bytes, content)


def test_pdf_tools_integration(mock_attachment_manager, tmp_path):
    """Test integration between different PDF operations with content verification."""
    # Mock the saved file content
    saved_pdfs = {}

    def mock_save(content_bytes, filename, *args):
        saved_pdfs[filename] = content_bytes
        # Actually write the file
        file_path = str(tmp_path / filename)
        with open(file_path, "wb") as f:
            f.write(content_bytes)
        return {"path": file_path}

    mock_attachment_manager.save_file.side_effect = mock_save

    # Create initial PDFs with distinct content
    pdf1_content = "Content 1 - Unique identifier A"
    pdf2_content = "Content 2 - Unique identifier B"

    pdf1_result = create_pdf(pdf1_content, "pdf1.pdf", "test@example.com")
    pdf2_result = create_pdf(pdf2_content, "pdf2.pdf", "test@example.com")

    assert pdf1_result["status"] == "success"
    assert pdf2_result["status"] == "success"
    assert os.path.exists(pdf1_result["path"])
    assert os.path.exists(pdf2_result["path"])

    # Verify created PDFs
    assert verify_pdf_content(saved_pdfs["pdf1.pdf"], pdf1_content)
    assert verify_pdf_content(saved_pdfs["pdf2.pdf"], pdf2_content)

    # Merge PDFs using the paths from create_pdf results
    merge_result = merge_pdfs(
        [pdf1_result["path"], pdf2_result["path"]],
        "merged.pdf",
        "test@example.com",
    )
    assert merge_result["status"] == "success"
    assert verify_pdf_content(saved_pdfs["merged.pdf"])

    # Split merged PDF
    split_result = split_pdf(merge_result["path"], str(tmp_path), "test@example.com")
    assert split_result["status"] == "success"

    # Verify split PDFs
    split_files = [name for name in saved_pdfs if name.startswith("page_")]
    for filename in split_files:
        assert verify_pdf_content(saved_pdfs[filename])
