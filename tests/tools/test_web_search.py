"""Tests for web search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mailos.tools.web_search import search_web, web_search_sync


@pytest.mark.asyncio
async def test_search_web_success():
    """Test successful web search."""
    # Create mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(
        return_value="""
        <div class="result">
            <h2 class="result__title">Test Title</h2>
            <div class="result__snippet">Test Snippet</div>
            <div class="result__url">https://test.com</div>
        </div>
    """
    )

    # Create mock session
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Patch ClientSession to return our mock
    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await search_web("test query")

        assert result["status"] == "success"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Title"
        assert result["results"][0]["snippet"] == "Test Snippet"
        assert result["results"][0]["url"] == "https://test.com"


@pytest.mark.asyncio
async def test_search_web_error():
    """Test web search error handling."""
    # Create mock response
    mock_response = MagicMock()
    mock_response.status = 500

    # Create mock session
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await search_web("test query")

        assert result["status"] == "error"
        assert "message" in result


def test_web_search_sync():
    """Test synchronous web search wrapper."""
    mock_result = {
        "status": "success",
        "results": [
            {
                "title": "Test Title",
                "snippet": "Test Snippet",
                "url": "https://test.com",
            }
        ],
    }

    with patch(
        "mailos.tools.web_search.search_web", AsyncMock(return_value=mock_result)
    ):
        result = web_search_sync("test query")

        assert result == mock_result
