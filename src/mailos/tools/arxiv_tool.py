"""ArXiv tool for searching and fetching academic papers."""

import asyncio
from typing import Dict

import arxiv

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


def _map_sort_criterion(sort_by: str) -> arxiv.SortCriterion:
    """Map sort_by string to arxiv.SortCriterion enum.

    Args:
        sort_by: Sort order ('relevance', 'lastUpdatedDate', 'submittedDate')

    Returns:
        Corresponding arxiv.SortCriterion value
    """
    sort_map = {
        "relevance": arxiv.SortCriterion.Relevance,
        "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
        "submittedDate": arxiv.SortCriterion.SubmittedDate,
    }
    return sort_map.get(sort_by, arxiv.SortCriterion.Relevance)


def search_arxiv(
    query: str,
    max_results: int = 5,
    sort_by: str = "relevance",
    include_abstract: bool = True,
) -> Dict:
    """Search ArXiv for papers matching the query.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        sort_by: Sort order ('relevance', 'lastUpdatedDate', 'submittedDate')
        include_abstract: Whether to include paper abstracts (default: True)

    Returns:
        Dict containing search results and status
    """
    try:
        if not query.strip():
            return {"status": "error", "message": "Query cannot be empty"}

        # Configure client
        client = arxiv.Client(
            page_size=100,
            delay_seconds=3,
            num_retries=3,
        )

        # Build search
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=_map_sort_criterion(sort_by),
        )

        # Execute search
        results = []
        for paper in client.results(search):
            paper_data = {
                "title": paper.title,
                "authors": [author.name for author in paper.authors],
                "published": paper.published.isoformat(),
                "updated": paper.updated.isoformat() if paper.updated else None,
                "doi": paper.doi,
                "primary_category": paper.primary_category,
                "categories": paper.categories,
                "links": {
                    "abstract": paper.entry_id,
                    "pdf": paper.pdf_url,
                    "html": paper.html_url if hasattr(paper, "html_url") else None,
                },
            }

            if include_abstract:
                paper_data["abstract"] = paper.summary

            results.append(paper_data)

        return {
            "status": "success",
            "query": query,
            "num_results": len(results),
            "results": results,
        }

    except Exception as e:
        error_msg = f"Error searching ArXiv: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


def search_arxiv_sync(
    query: str,
    max_results: int = 5,
    sort_by: str = "relevance",
    include_abstract: bool = True,
) -> Dict:
    """Wrap ArXiv search in a synchronous function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return search_arxiv(query, max_results, sort_by, include_abstract)
    finally:
        loop.close()


# Define the ArXiv search tool
arxiv_tool = Tool(
    name="search_arxiv",
    description="Search ArXiv for academic papers and research articles",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'quantum computing', 'machine learning')",  # noqa E501
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5)",
                "minimum": 1,
                "maximum": 100,
            },
            "sort_by": {
                "type": "string",
                "description": "Sort order for results",
                "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
            },
            "include_abstract": {
                "type": "boolean",
                "description": "Whether to include paper abstracts (default: true)",
            },
        },
    },
    required_params=["query"],
    function=search_arxiv_sync,
)
