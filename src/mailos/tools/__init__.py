"""Tools package for MailOS."""

from .arxiv_tool import arxiv_tool
from .bash_command import bash_command_tool
from .pdf_tool import (
    create_pdf_tool,
    edit_pdf_tool,
    extract_text_tool,
    merge_pdfs_tool,
    split_pdf_tool,
)
from .planner import planner_tool, set_llm_instance
from .python_interpreter import python_interpreter_tool
from .weather import weather_tool
from .web_search import web_search_tool

# List of all available tools with their display names
AVAILABLE_TOOLS = [
    ("weather_tool", "Weather Information"),
    ("create_pdf_tool", "Create PDF"),
    ("edit_pdf_tool", "Edit PDF"),
    ("merge_pdfs_tool", "Merge PDFs"),
    ("extract_text_tool", "Extract PDF Text"),
    ("split_pdf_tool", "Split PDF"),
    ("python_interpreter_tool", "Python Code Execution"),
    ("bash_command_tool", "Bash Command Execution"),
    ("web_search_tool", "Web Search"),
    ("arxiv_tool", "ArXiv Paper Search"),
    ("planner_tool", "Task Planner"),
]

# Map of tool names to actual tool objects
TOOL_MAP = {
    "weather_tool": weather_tool,
    "create_pdf_tool": create_pdf_tool,
    "edit_pdf_tool": edit_pdf_tool,
    "merge_pdfs_tool": merge_pdfs_tool,
    "extract_text_tool": extract_text_tool,
    "split_pdf_tool": split_pdf_tool,
    "python_interpreter_tool": python_interpreter_tool,
    "bash_command_tool": bash_command_tool,
    "web_search_tool": web_search_tool,
    "arxiv_tool": arxiv_tool,
    "planner_tool": planner_tool,
}

__all__ = [
    "weather_tool",
    "create_pdf_tool",
    "edit_pdf_tool",
    "merge_pdfs_tool",
    "extract_text_tool",
    "split_pdf_tool",
    "python_interpreter_tool",
    "bash_command_tool",
    "web_search_tool",
    "arxiv_tool",
    "planner_tool",
    "set_llm_instance",
    "AVAILABLE_TOOLS",
    "TOOL_MAP",
]
