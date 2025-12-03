"""
Abstract base class for LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Callable
import json
from .models import LLMMessage, LLMResponse, LLMToolCall, ToolDefinition


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize provider with API key and model"""
        self.api_key = api_key
        self.model = model
        if not api_key:
            raise ValueError(f"API key is required for {self.__class__.__name__}")
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Union[ToolDefinition, Dict[str, Any]]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make a direct LLM call (no tool execution)
        
        Args:
            messages: List of messages in conversation
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Tool definitions (standardized format)
            tool_choice: "auto", "none", or specific tool name
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with content and optional tool_calls
        """
        pass
    
    @abstractmethod
    async def chat_completion_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Union[ToolDefinition, Dict[str, Any]]],
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        max_iterations: int = 10,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make LLM call with tool execution loop (agentic)
        
        Args:
            messages: Initial messages
            tools: Tool definitions in standardized format
            tool_executor: Function that takes (tool_name, arguments) and returns result
            max_iterations: Maximum tool call iterations
            temperature: Sampling temperature
            max_tokens: Maximum tokens per call
            **kwargs: Provider-specific parameters
            
        Returns:
            Final LLMResponse after tool execution loop
        """
        pass
    
    @abstractmethod
    def normalize_tool_definitions(
        self, 
        tools: List[Union[ToolDefinition, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standardized tool definitions to provider-specific format
        
        Args:
            tools: List of ToolDefinition objects or dicts in standard format
            
        Returns:
            Provider-specific tool format
        """
        pass
    
    @abstractmethod
    def parse_response(self, raw_response: Any) -> LLMResponse:
        """
        Parse provider-specific response to standardized format
        
        Args:
            raw_response: Provider's raw response object
            
        Returns:
            Standardized LLMResponse
        """
        pass
    
    def _normalize_tool_input(
        self, 
        tool: Union[ToolDefinition, Dict[str, Any]]
    ) -> ToolDefinition:
        """
        Helper to convert dict to ToolDefinition if needed
        """
        if isinstance(tool, ToolDefinition):
            return tool
        elif isinstance(tool, dict):
            # Handle both standard format and provider-specific formats
            if "function" in tool:
                # OpenAI/Groq format
                func = tool["function"]
                return ToolDefinition(
                    name=func["name"],
                    description=func.get("description", ""),
                    parameters=func.get("parameters", {})
                )
            elif "name" in tool:
                # Standard format or Anthropic format
                return ToolDefinition(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=tool.get("parameters", tool.get("input_schema", {}))
                )
            else:
                raise ValueError(f"Invalid tool format: {tool}")
        else:
            raise ValueError(f"Invalid tool type: {type(tool)}")
    
    def _convert_messages_to_dict(
        self, 
        messages: List[LLMMessage]
    ) -> List[Dict[str, str]]:
        """Convert LLMMessage list to dict format (for backward compatibility)"""
        result = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            result.append(msg_dict)
        return result

