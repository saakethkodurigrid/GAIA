"""
Groq LLM Provider Implementation
"""
import json
import time
from typing import List, Dict, Any, Optional, Union, Callable
from groq import Groq
from .base import BaseLLMProvider
from .models import LLMMessage, LLMResponse, LLMToolCall, ToolDefinition


class GroqProvider(BaseLLMProvider):
    """Groq LLM provider implementation"""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = Groq(api_key=api_key)
    
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Union[ToolDefinition, Dict[str, Any]]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Make a direct LLM call using Groq SDK"""
        # Convert standardized messages to Groq format
        groq_messages = self._convert_messages_to_dict(messages)
        
        # Prepare Groq API call parameters
        params = {
            "model": self.model,
            "messages": groq_messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # Add provider-specific parameters
        if "top_p" in kwargs:
            params["top_p"] = kwargs["top_p"]
        
        # Handle tools
        if tools:
            groq_tools = self.normalize_tool_definitions(tools)
            params["tools"] = groq_tools
            params["tool_choice"] = tool_choice or "auto"
        
        # Make API call
        try:
            response = self.client.chat.completions.create(**params)
            return self.parse_response(response)
        except Exception as e:
            # Re-raise with context
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise ValueError("Invalid GROQ_API_KEY. Please check your API key.")
            elif "429" in error_str or "rate limit" in error_str:
                raise ValueError("Rate limit exceeded. Please try again later.")
            elif "400" in error_str or "bad request" in error_str:
                raise ValueError(f"Bad request to Groq API: {str(e)}")
            else:
                raise
    
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
        """Make LLM call with tool execution loop"""
        conversation_messages = messages.copy()
        
        for iteration in range(max_iterations):
            # Call LLM
            response = await self.chat_completion(
                messages=conversation_messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Add assistant response to conversation
            assistant_msg = LLMMessage(
                role="assistant",
                content=response.content or ""
            )
            conversation_messages.append(assistant_msg)
            
            # If no tool calls, return final response
            if not response.tool_calls:
                return response
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                try:
                    # Execute tool
                    tool_result = tool_executor(tool_call.name, tool_call.arguments)
                    
                    # Format tool result as string
                    if isinstance(tool_result, dict):
                        tool_result_str = json.dumps(tool_result, indent=2)
                    else:
                        tool_result_str = str(tool_result)
                    
                    # Add tool result to conversation
                    tool_msg = LLMMessage(
                        role="tool",
                        content=tool_result_str,
                        tool_call_id=tool_call.id
                    )
                    conversation_messages.append(tool_msg)
                except Exception as e:
                    # Add error message
                    error_msg = LLMMessage(
                        role="tool",
                        content=f"Error executing tool {tool_call.name}: {str(e)}",
                        tool_call_id=tool_call.id
                    )
                    conversation_messages.append(error_msg)
        
        return response
    
    def normalize_tool_definitions(
        self, 
        tools: List[Union[ToolDefinition, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standardized tools to Groq/OpenAI format
        
        Groq uses OpenAI-compatible format:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        groq_tools = []
        for tool in tools:
            # Normalize to ToolDefinition
            tool_def = self._normalize_tool_input(tool)
            
            # Convert to Groq format
            groq_tool = {
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.parameters
                }
            }
            groq_tools.append(groq_tool)
        return groq_tools
    
    def parse_response(self, raw_response: Any) -> LLMResponse:
        """Parse Groq response to standardized format"""
        message = raw_response.choices[0].message
        content = message.content or ""
        
        # Parse tool calls if present
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                # Groq returns arguments as JSON string
                arguments_str = tc.function.arguments
                if isinstance(arguments_str, str):
                    try:
                        arguments = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        arguments = {}
                else:
                    arguments = arguments_str
                
                tool_calls.append(LLMToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments
                ))
        
        # Parse usage
        usage = None
        if hasattr(raw_response, 'usage') and raw_response.usage:
            usage = {
                "prompt_tokens": getattr(raw_response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(raw_response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(raw_response.usage, 'total_tokens', 0)
            }
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=raw_response.choices[0].finish_reason,
            usage=usage
        )

