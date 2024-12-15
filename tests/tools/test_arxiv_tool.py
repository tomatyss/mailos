"""Tests for the ArXiv tool."""

import pytest

from mailos.tools.arxiv_tool import search_arxiv_sync


def test_arxiv_search_basic():
    """Test basic ArXiv search functionality."""
    result = search_arxiv_sync(
        query="quantum computing",
        max_results=2,
        sort_by="relevance",
        include_abstract=True,
    )

    assert result["status"] == "success"
    assert len(result["results"]) <= 2
    assert result["query"] == "quantum computing"

    # Check paper data structure
    paper = result["results"][0]
    assert "title" in paper
    assert "authors" in paper
    assert "published" in paper
    assert "abstract" in paper
    assert "links" in paper
    assert "pdf" in paper["links"]
    assert "abstract" in paper["links"]


def test_arxiv_search_no_abstract():
    """Test ArXiv search without abstracts."""
    result = search_arxiv_sync(
        query="machine learning",
        max_results=1,
        include_abstract=False,
    )

    assert result["status"] == "success"
    assert len(result["results"]) <= 1
    assert "abstract" not in result["results"][0]


def test_arxiv_search_sort_by():
    """Test ArXiv search with different sort options."""
    result = search_arxiv_sync(
        query="physics",
        max_results=1,
        sort_by="submittedDate",
    )

    assert result["status"] == "success"
    assert len(result["results"]) <= 1


def test_arxiv_search_invalid_query():
    """Test ArXiv search with invalid query."""
    result = search_arxiv_sync(
        query="",  # Empty query
        max_results=1,
    )

    assert result["status"] == "error"
    assert "message" in result


def test_arxiv_search_max_results():
    """Test ArXiv search with different max_results values."""
    result = search_arxiv_sync(
        query="neural networks",
        max_results=3,
    )

    assert result["status"] == "success"
    assert len(result["results"]) <= 3


@pytest.mark.parametrize(
    "sort_by",
    ["relevance", "lastUpdatedDate", "submittedDate"],
)
def test_arxiv_search_all_sort_options(sort_by):
    """Test ArXiv search with all sort options."""
    result = search_arxiv_sync(
        query="deep learning",
        max_results=1,
        sort_by=sort_by,
    )

    assert result["status"] == "success"
    assert len(result["results"]) > 0
