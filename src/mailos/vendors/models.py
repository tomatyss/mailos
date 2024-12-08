"""Data models for vendor integrations and LLM interactions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RoleType(str, Enum):
    """Enumeration of possible message role types."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ContentType(str, Enum):
    """Enumeration of supported content types."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"
    EMBEDDING = "embedding"


@dataclass
class Content:
    """Represents content in a message with type and value."""

    type: ContentType
    data: Any
    mime_type: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert content to a dictionary."""
        return {"type": self.type.value, "data": self.data, "mime_type": self.mime_type}


@dataclass
class Message:
    """Represents a message in a conversation with role and content."""

    role: RoleType
    content: List[Content]
    name: Optional[str] = None
    function_call: Optional[Dict] = None
    timestamp: datetime = datetime.now()

    def to_dict(self) -> Dict:
        """Convert message to a dictionary."""
        return {
            "role": self.role.value,
            "content": [c.to_dict() for c in self.content],
            "name": self.name,
            "function_call": self.function_call,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Tool:
    """Represents a tool or function that can be called by the LLM."""

    name: str
    description: str
    parameters: Dict
    function: Callable
    required_params: List[str] = None

    def to_dict(self) -> Dict:
        """Convert tool to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "required": self.required_params or [],
        }


@dataclass
class ModelConfig:
    """Configuration settings for LLM model behavior and parameters."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None


@dataclass
class LLMResponse:
    """Unified response model for all LLM providers."""

    content: List[Content]
    role: RoleType = RoleType.ASSISTANT
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    system_fingerprint: Optional[str] = None
    created_at: datetime = datetime.now()

    def to_message(self) -> Message:
        """Convert response to a Message object."""
        return Message(
            role=self.role,
            content=self.content,
            function_call=self.tool_calls[0] if self.tool_calls else None,
            timestamp=self.created_at,
        )

    def to_dict(self) -> Dict:
        """Convert response to a dictionary."""
        return {
            "content": [c.to_dict() for c in self.content],
            "role": self.role.value,
            "finish_reason": self.finish_reason,
            "tool_calls": self.tool_calls,
            "usage": self.usage,
            "model": self.model,
            "system_fingerprint": self.system_fingerprint,
            "created_at": self.created_at.isoformat(),
        }
