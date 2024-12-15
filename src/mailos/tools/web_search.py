"""Web search tool using DuckDuckGo."""

import asyncio
from typing import Dict, Optional
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool


async def fetch_url(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Fetch content from a URL."""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {str(e)}")
    return None


async def extract_content(html: str) -> str:
    """Extract readable content from HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text content
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return text[:2000]  # Limit content length
    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return ""


async def search_web(
    query: str, max_results: int = 5, extract_content: bool = False
) -> Dict:
    """Search the web using DuckDuckGo and optionally extract content from results.

    Args:
        query: Search query
        max_results: Maximum number of results to return (default: 5)
        extract_content: Whether to extract content from result URLs (default: False)

    Returns:
        Dict containing search results and status
    """
    try:
        # Construct DuckDuckGo search URL
        encoded_query = quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        async with aiohttp.ClientSession() as session:
            response = await session.get(search_url)
            if response.status != 200:
                return {
                    "status": "error",
                    "message": f"Search failed with status {response.status}",
                }

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            results = []
            for result in soup.select(".result")[:max_results]:
                title_elem = result.select_one(".result__title")
                snippet_elem = result.select_one(".result__snippet")
                link_elem = result.select_one(".result__url")

                if not all([title_elem, snippet_elem, link_elem]):
                    continue

                result_data = {
                    "title": title_elem.get_text().strip(),
                    "snippet": snippet_elem.get_text().strip(),
                    "url": link_elem.get_text().strip(),
                }

                if extract_content and result_data["url"]:
                    content = await fetch_url(session, result_data["url"])
                    if content:
                        result_data["extracted_content"] = await extract_content(
                            content
                        )

                results.append(result_data)

            return {
                "status": "success",
                "results": results,
                "query": query,
                "num_results": len(results),
            }

    except Exception as e:
        logger.error(f"Error performing web search: {str(e)}")
        return {"status": "error", "message": str(e)}


def web_search_sync(
    query: str, max_results: int = 5, extract_content: bool = False
) -> Dict:
    """Wrap the web search function to run synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(search_web(query, max_results, extract_content))
    finally:
        loop.close()


# Define the web search tool
web_search_tool = Tool(
    name="web_search",
    description="Search the web using DuckDuckGo and optionally extract content from results",  # noqa E501
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5)",
                "minimum": 1,
                "maximum": 10,
            },
            "extract_content": {
                "type": "boolean",
                "description": "Whether to extract content from result URLs (default: false)",  # noqa E501
            },
        },
    },
    required_params=["query"],
    function=web_search_sync,
)
