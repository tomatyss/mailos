"""Tests for BedrockAnthropicLLM class."""

import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from mailos.vendors.bedrock_anthropic_llm import (
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_SIZE,
    BedrockAnthropicLLM,
)
from mailos.vendors.models import Content, ContentType, Message, RoleType, Tool

# Test constants
TEST_ACCESS_KEY = "test-access-key"
TEST_SECRET_KEY = "test-secret-key"
TEST_REGION = "us-east-1"
TEST_MODEL = "anthropic.claude-3-sonnet-1"


@pytest.fixture
def llm():
    """Create a BedrockAnthropicLLM instance with mocked AWS client."""
    with patch("boto3.Session") as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        llm = BedrockAnthropicLLM(
            aws_access_key=TEST_ACCESS_KEY,
            aws_secret_key=TEST_SECRET_KEY,
            aws_region=TEST_REGION,
            model=TEST_MODEL,
        )
        llm.client = mock_client
        return llm


def create_test_image(size=(100, 100), format="PNG"):
    """Create a test image with specified size and format."""
    image = Image.new("RGB", size, color="white")
    buffer = BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)  # Reset buffer position
    return buffer.getvalue()


def test_init():
    """Test BedrockAnthropicLLM initialization."""
    with patch("boto3.Session") as mock_session:
        instance = BedrockAnthropicLLM(
            aws_access_key=TEST_ACCESS_KEY,
            aws_secret_key=TEST_SECRET_KEY,
            aws_region=TEST_REGION,
            model=TEST_MODEL,
        )

        assert instance.aws_region == TEST_REGION
        assert instance.model == TEST_MODEL
        assert mock_session.called
        mock_session.assert_called_with(
            aws_access_key_id=TEST_ACCESS_KEY,
            aws_secret_access_key=TEST_SECRET_KEY,
            region_name=TEST_REGION,
        )


def test_init_with_session_token():
    """Test initialization with session token."""
    test_token = "test-session-token"
    with patch("boto3.Session") as mock_session:
        BedrockAnthropicLLM(
            aws_access_key=TEST_ACCESS_KEY,
            aws_secret_key=TEST_SECRET_KEY,
            aws_session_token=test_token,
            aws_region=TEST_REGION,
        )

        mock_session.assert_called_with(
            aws_access_key_id=TEST_ACCESS_KEY,
            aws_secret_access_key=TEST_SECRET_KEY,
            aws_session_token=test_token,
            region_name=TEST_REGION,
        )


def test_process_image_valid(llm):
    """Test processing a valid image."""
    image_data = create_test_image()
    result = llm._process_image(image_data, "image/png")

    assert result["type"] == "image"
    assert result["source"]["type"] == "base64"
    assert result["source"]["media_type"] == "image/png"
    assert "data" in result["source"]

    # Verify the base64 data is valid
    decoded = base64.b64decode(result["source"]["data"])
    assert len(decoded) > 0


def test_process_image_unsupported_format(llm):
    """Test processing an image with unsupported format."""
    with pytest.raises(ValueError, match="Unsupported image format"):
        llm._process_image(b"dummy data", "image/tiff")


def test_process_image_too_large(llm):
    """Test processing an image that exceeds size limit."""
    # Create an image that exceeds MAX_IMAGE_SIZE
    large_data = b"0" * (MAX_IMAGE_SIZE + 1)

    with pytest.raises(ValueError, match="Image size exceeds maximum"):
        llm._process_image(large_data, "image/png")


def test_process_image_auto_resize(llm):
    """Test automatic resizing of large images."""
    # Create an image larger than MAX_IMAGE_DIMENSION
    large_image = create_test_image(size=(5000, 3000))
    result = llm._process_image(large_image, "image/png")

    # Decode and verify the resized image
    decoded = base64.b64decode(result["source"]["data"])
    img = Image.open(BytesIO(decoded))
    assert max(img.size) <= MAX_IMAGE_DIMENSION

    # Verify the image is still valid and in PNG format
    assert result["source"]["media_type"] == "image/png"
    assert img.format.lower() == "png"


def test_format_tools(llm):
    """Test tool formatting."""

    def dummy_function():
        pass

    tools = [
        Tool(
            name="test_tool",
            description="A test tool",
            parameters={"properties": {"param1": {"type": "string"}}},
            required_params=["param1"],
            function=dummy_function,
        )
    ]

    formatted = llm._format_tools(tools)
    assert len(formatted) == 1
    assert formatted[0]["name"] == "test_tool"
    assert formatted[0]["description"] == "A test tool"
    assert formatted[0]["input_schema"]["properties"] == {"param1": {"type": "string"}}
    assert formatted[0]["input_schema"]["required"] == ["param1"]


def test_format_messages_simple(llm):
    """Test formatting simple text messages."""
    messages = [
        Message(
            role=RoleType.USER,
            content=[Content(type=ContentType.TEXT, data="Hello")],
        )
    ]

    formatted = llm._format_messages(messages)
    assert len(formatted["messages"]) == 1
    assert formatted["messages"][0]["role"] == "user"
    assert formatted["messages"][0]["content"][0]["text"] == "Hello"
    assert formatted["system"] is None


def test_format_messages_with_system(llm):
    """Test formatting messages with system message."""
    messages = [
        Message(
            role=RoleType.SYSTEM,
            content=[Content(type=ContentType.TEXT, data="System prompt")],
        ),
        Message(
            role=RoleType.USER,
            content=[Content(type=ContentType.TEXT, data="User message")],
        ),
    ]

    formatted = llm._format_messages(messages)
    assert formatted["system"] == "System prompt"
    assert len(formatted["messages"]) == 1
    assert formatted["messages"][0]["role"] == "user"


def test_format_messages_with_image(llm):
    """Test formatting messages with image content."""
    image_data = create_test_image()
    messages = [
        Message(
            role=RoleType.USER,
            content=[
                Content(type=ContentType.TEXT, data="Look at this image"),
                Content(type=ContentType.IMAGE, data=image_data, mime_type="image/png"),
            ],
        )
    ]

    formatted = llm._format_messages(messages)
    assert len(formatted["messages"]) == 1
    content = formatted["messages"][0]["content"]
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image"
    assert content[1]["source"]["media_type"] == "image/png"


@pytest.mark.asyncio
async def test_make_request(llm):
    """Test making a request to Bedrock."""
    messages = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
        "system": None,
    }

    mock_response = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(
                    {
                        "content": [{"type": "text", "text": "Response"}],
                        "stop_reason": "end_turn",
                    }
                ).encode()
            )
        )
    }
    llm.client.invoke_model.return_value = mock_response

    response = await llm._make_request(messages)
    assert "content" in response
    assert response["content"][0]["text"] == "Response"


@pytest.mark.asyncio
async def test_make_request_with_tools(llm):
    """Test making a request with tools."""
    messages = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "Use tool"}]}
        ],
        "system": None,
    }
    tools = [{"name": "test_tool", "description": "A test tool"}]

    mock_response = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(
                    {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "tool1",
                                "name": "test_tool",
                                "input": {"param": "value"},
                            }
                        ],
                        "stop_reason": "tool_use",
                    }
                ).encode()
            )
        )
    }
    llm.client.invoke_model.return_value = mock_response

    response = await llm._make_request(messages, tools)
    assert response["stop_reason"] == "tool_use"
    assert response["content"][0]["type"] == "tool_use"


@pytest.mark.asyncio
async def test_stream_response(llm):
    """Test streaming response handling."""
    mock_stream = {
        "body": [
            {"chunk": {"bytes": json.dumps({"content": "Hello"}).encode()}},
            {"chunk": {"bytes": json.dumps({"content": " world"}).encode()}},
        ]
    }

    responses = []
    async for response in llm._stream_response(mock_stream):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].content[0].data == "Hello"
    assert responses[1].content[0].data == " world"


@pytest.mark.asyncio
async def test_process_image_endpoint(llm):
    """Test the process_image endpoint."""
    image_data = create_test_image()
    mock_response = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(
                    {
                        "content": [{"type": "text", "text": "Image analysis"}],
                        "stop_reason": "end_turn",
                    }
                ).encode()
            )
        )
    }
    llm.client.invoke_model.return_value = mock_response

    response = await llm.process_image(image_data, "Describe this image")
    assert response.content[0].data == "Image analysis"


@pytest.mark.asyncio
async def test_process_image_unsupported_model(llm):
    """Test process_image with unsupported model."""
    llm.model = "anthropic.claude-2"
    with pytest.raises(NotImplementedError):
        await llm.process_image(b"dummy", "prompt")
