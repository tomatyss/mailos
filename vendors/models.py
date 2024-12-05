from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any, AsyncIterator, Dict, List, Optional, Union, 
    Callable, TypeVar, Generic, Protocol
)
from datetime import datetime
import json

class RoleType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"
    EMBEDDING = "embedding"

@dataclass
class Content:
    type: ContentType
    data: Any
    mime_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "data": self.data,
            "mime_type": self.mime_type
        }

@dataclass
class Message:
    role: RoleType
    content: List[Content]
    name: Optional[str] = None
    function_call: Optional[Dict] = None
    timestamp: datetime = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "role": self.role.value,
            "content": [c.to_dict() for c in self.content],
            "name": self.name,
            "function_call": self.function_call,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict
    function: Callable
    required_params: List[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "required": self.required_params or []
        }

@dataclass
class ModelConfig:
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None 