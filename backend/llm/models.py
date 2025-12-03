"""
Data models for LLM abstraction layer
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class LLMMessage:
    """Standardized message format"""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: Optional[str] = None  # For tool responses


@dataclass
class LLMToolCall:
    """Standardized tool call format"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """Standardized response format"""
    content: str
    tool_calls: Optional[List[LLMToolCall]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # tokens_used, etc.


@dataclass
class ToolDefinition:
    """Standardized tool definition format (platform-agnostic)"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

