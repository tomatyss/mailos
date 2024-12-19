"""Tests for CSV tool functionality."""

import os
from typing import List

import pytest

from mailos.tools.csv_tool import (
    append_csv_tool,
    create_csv_tool,
    read_csv_tool,
    update_csv_tool,
)


@pytest.fixture
def sample_csv_path(tmp_path) -> str:
    """Create a temporary path for CSV files."""
    return str(tmp_path / "test.csv")


@pytest.fixture
def sample_headers() -> List[str]:
    """Sample CSV headers for testing."""
    return ["Name", "Age", "City"]


@pytest.fixture
def sample_data() -> List[List[str]]:
    """Sample CSV data for testing."""
    return [
        ["John", "30", "New York"],
        ["Alice", "25", "London"],
    ]


def test_create_csv(sample_csv_path, sample_headers, sample_data):
    """Test creating a new CSV file."""
    result = create_csv_tool.function(
        headers=sample_headers,
        data=sample_data,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )

    assert result["status"] == "success"
    assert os.path.exists(result["path"])

    # Verify content
    read_result = read_csv_tool.function(input_path=result["path"])
    assert read_result["status"] == "success"
    assert read_result["headers"] == sample_headers
    assert read_result["data"] == sample_data
    assert read_result["num_rows"] == len(sample_data)
    assert read_result["num_columns"] == len(sample_headers)


def test_read_csv_nonexistent_file(sample_csv_path):
    """Test reading a non-existent CSV file."""
    result = read_csv_tool.function(input_path=sample_csv_path)
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_update_csv(sample_csv_path, sample_headers, sample_data):
    """Test updating an existing CSV file."""
    # First create a CSV
    create_result = create_csv_tool.function(
        headers=sample_headers,
        data=sample_data,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert create_result["status"] == "success"

    # Update specific cells
    updates = [
        {"row": 0, "col": "Age", "value": "31"},  # Update by column name
        {"row": 1, "col": 2, "value": "Paris"},  # Update by column index
    ]

    update_result = update_csv_tool.function(
        input_path=create_result["path"],
        updates=updates,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert update_result["status"] == "success"

    # Verify updates
    read_result = read_csv_tool.function(input_path=update_result["path"])
    assert read_result["status"] == "success"
    assert read_result["data"][0][1] == "31"  # Age updated
    assert read_result["data"][1][2] == "Paris"  # City updated


def test_update_csv_entire_row(sample_csv_path, sample_headers, sample_data):
    """Test updating an entire row in a CSV file."""
    # First create a CSV
    create_result = create_csv_tool.function(
        headers=sample_headers,
        data=sample_data,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert create_result["status"] == "success"

    # Update entire row
    updates = [
        {"row": 1, "values": ["Bob", "35", "Berlin"]},
    ]

    update_result = update_csv_tool.function(
        input_path=create_result["path"],
        updates=updates,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert update_result["status"] == "success"

    # Verify updates
    read_result = read_csv_tool.function(input_path=update_result["path"])
    assert read_result["status"] == "success"
    assert read_result["data"][1] == ["Bob", "35", "Berlin"]


def test_append_csv(sample_csv_path, sample_headers, sample_data):
    """Test appending rows to a CSV file."""
    # First create a CSV
    create_result = create_csv_tool.function(
        headers=sample_headers,
        data=sample_data,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert create_result["status"] == "success"

    # Append new rows
    new_rows = [
        ["Bob", "35", "Berlin"],
        ["Carol", "28", "Tokyo"],
    ]

    append_result = append_csv_tool.function(
        input_path=create_result["path"],
        new_rows=new_rows,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert append_result["status"] == "success"
    assert append_result["rows_added"] == len(new_rows)
    assert append_result["total_rows"] == len(sample_data) + len(new_rows)

    # Verify appended data
    read_result = read_csv_tool.function(input_path=append_result["path"])
    assert read_result["status"] == "success"
    assert len(read_result["data"]) == len(sample_data) + len(new_rows)
    assert read_result["data"][-2:] == new_rows


def test_append_csv_with_missing_columns(sample_csv_path, sample_headers, sample_data):
    """Test appending rows with missing columns."""
    # First create a CSV
    create_result = create_csv_tool.function(
        headers=sample_headers,
        data=sample_data,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert create_result["status"] == "success"

    # Append rows with missing columns
    new_rows = [
        ["Bob", "35"],  # Missing City
        ["Carol"],  # Missing Age and City
    ]

    append_result = append_csv_tool.function(
        input_path=create_result["path"],
        new_rows=new_rows,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert append_result["status"] == "success"

    # Verify appended data (should have empty strings for missing values)
    read_result = read_csv_tool.function(input_path=append_result["path"])
    assert read_result["status"] == "success"
    assert read_result["data"][-2] == ["Bob", "35", ""]
    assert read_result["data"][-1] == ["Carol", "", ""]


def test_update_csv_invalid_indices(sample_csv_path, sample_headers, sample_data):
    """Test updating CSV with invalid row/column indices."""
    # First create a CSV
    create_result = create_csv_tool.function(
        headers=sample_headers,
        data=sample_data,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert create_result["status"] == "success"

    # Try updates with invalid indices
    updates = [
        {"row": -1, "col": 0, "value": "Invalid"},  # Invalid row
        {"row": 999, "col": 0, "value": "Invalid"},  # Row out of range
        {"row": 0, "col": -1, "value": "Invalid"},  # Invalid column
        {"row": 0, "col": 999, "value": "Invalid"},  # Column out of range
        {"row": 0, "col": "InvalidColumn", "value": "Invalid"},  # Invalid column name
    ]

    update_result = update_csv_tool.function(
        input_path=create_result["path"],
        updates=updates,
        output_path=sample_csv_path,
        sender_email="test@example.com",
    )
    assert (
        update_result["status"] == "success"
    )  # Should succeed but skip invalid updates

    # Verify data remains unchanged
    read_result = read_csv_tool.function(input_path=update_result["path"])
    assert read_result["status"] == "success"
    assert read_result["data"] == sample_data
