"""CSV tool for creating and manipulating CSV files."""

import csv
import io
import os
from typing import Dict, List, Union

from mailos.utils.attachment_utils import AttachmentManager
from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool

attachment_manager = AttachmentManager()


def create_csv(
    headers: List[str],
    data: List[List[str]],
    output_path: str,
    sender_email: str,
) -> Dict:
    """Create a new CSV file with the given headers and data.

    Args:
        headers: List of column headers
        data: List of rows, where each row is a list of values
        output_path: Path where to save the CSV file
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        # Create CSV in memory first
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Write headers and data
        writer.writerow(headers)
        writer.writerows(data)

        # Get the CSV content
        csv_content = buffer.getvalue()
        buffer.close()

        # Save using attachment manager
        result = attachment_manager.save_file(
            csv_content.encode("utf-8"),
            output_path,
            sender_email,
        )

        return {
            "status": "success",
            "message": f"CSV created successfully at {result['path']}",
            "path": result["path"],
        }
    except Exception as e:
        error_msg = f"Error creating CSV: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


def read_csv(input_path: str) -> Dict:
    """Read data from an existing CSV file.

    Args:
        input_path: Path to the CSV file to read

    Returns:
        Dict with operation status and CSV data
    """
    try:
        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}"}

        with open(input_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)  # Get headers
            data = list(reader)  # Get all rows

        return {
            "status": "success",
            "headers": headers,
            "data": data,
            "num_rows": len(data),
            "num_columns": len(headers),
        }
    except Exception as e:
        error_msg = f"Error reading CSV: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


def update_csv(
    input_path: str,
    updates: List[Dict[str, Union[int, str, List[str]]]],
    output_path: str,
    sender_email: str,
) -> Dict:
    """Update an existing CSV file with new data.

    Args:
        input_path: Path to the input CSV file
        updates: List of update operations, each containing:
            - row: Row index to update (0-based, after headers)
            - col: Column index or name to update
            - value: New value to set
            OR
            - row: Row index to update
            - values: List of values to update entire row
        output_path: Path to save the updated CSV
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}"}

        # Read existing CSV
        with open(input_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            data = list(reader)

        # Apply updates
        for update in updates:
            row_idx = update.get("row")
            if row_idx is None or row_idx < 0 or row_idx >= len(data):
                continue

            if "values" in update:
                # Update entire row
                values = update["values"]
                if len(values) == len(headers):
                    data[row_idx] = values
            elif "col" in update and "value" in update:
                # Update specific cell
                col = update["col"]
                value = update["value"]

                # Convert column name to index if needed
                if isinstance(col, str):
                    try:
                        col = headers.index(col)
                    except ValueError:
                        continue

                if isinstance(col, int) and 0 <= col < len(headers):
                    # Ensure row has enough columns
                    while len(data[row_idx]) < len(headers):
                        data[row_idx].append("")
                    data[row_idx][col] = str(value)

        # Write updated CSV to memory
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(data)

        # Get the CSV content
        csv_content = buffer.getvalue()
        buffer.close()

        # Save using attachment manager
        result = attachment_manager.save_file(
            csv_content.encode("utf-8"),
            output_path,
            sender_email,
        )

        return {
            "status": "success",
            "message": f"CSV updated successfully at {result['path']}",
            "path": result["path"],
            "num_updates": len(updates),
        }
    except Exception as e:
        error_msg = f"Error updating CSV: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


def append_to_csv(
    input_path: str,
    new_rows: List[List[str]],
    output_path: str,
    sender_email: str,
) -> Dict:
    """Append new rows to an existing CSV file.

    Args:
        input_path: Path to the input CSV file
        new_rows: List of rows to append, where each row is a list of values
        output_path: Path to save the updated CSV
        sender_email: Email address of the sender

    Returns:
        Dict with operation status and details
    """
    try:
        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}"}

        # Read existing CSV
        with open(input_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            data = list(reader)

        # Validate and pad new rows if needed
        padded_rows = []
        for row in new_rows:
            # Pad or truncate row to match header length
            padded_row = (row + [""] * len(headers))[: len(headers)]
            padded_rows.append(padded_row)

        # Combine existing data with new rows
        data.extend(padded_rows)

        # Write updated CSV to memory
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(data)

        # Get the CSV content
        csv_content = buffer.getvalue()
        buffer.close()

        # Save using attachment manager
        result = attachment_manager.save_file(
            csv_content.encode("utf-8"),
            output_path,
            sender_email,
        )

        return {
            "status": "success",
            "message": f"CSV updated successfully at {result['path']}",
            "path": result["path"],
            "rows_added": len(new_rows),
            "total_rows": len(data),
        }
    except Exception as e:
        error_msg = f"Error appending to CSV: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


# Define the CSV tools
create_csv_tool = Tool(
    name="create_csv",
    description="Create a new CSV file with the given headers and data",
    parameters={
        "type": "object",
        "properties": {
            "headers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of column headers",
            },
            "data": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "description": "List of rows, where each row is a list of values",
            },
            "output_path": {
                "type": "string",
                "description": "Path where to save the CSV file",
            },
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["headers", "data", "output_path", "sender_email"],
    function=create_csv,
)

read_csv_tool = Tool(
    name="read_csv",
    description="Read data from an existing CSV file",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the CSV file to read",
            },
        },
    },
    required_params=["input_path"],
    function=read_csv,
)

update_csv_tool = Tool(
    name="update_csv",
    description="Update an existing CSV file with new data",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the input CSV file",
            },
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "row": {"type": "integer"},
                        "col": {"type": ["integer", "string"]},
                        "value": {"type": "string"},
                        "values": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "description": "List of update operations",
            },
            "output_path": {
                "type": "string",
                "description": "Path to save the updated CSV",
            },
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["input_path", "updates", "output_path", "sender_email"],
    function=update_csv,
)

append_csv_tool = Tool(
    name="append_csv",
    description="Append new rows to an existing CSV file",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the input CSV file",
            },
            "new_rows": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "description": "List of rows to append",
            },
            "output_path": {
                "type": "string",
                "description": "Path to save the updated CSV",
            },
            "sender_email": {
                "type": "string",
                "description": "Email address of the sender",
            },
        },
    },
    required_params=["input_path", "new_rows", "output_path", "sender_email"],
    function=append_to_csv,
)
