"""
Anthropic Claude LLM Provider Implementation
"""
import json
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from anthropic import AsyncAnthropic
from .base import BaseLLMProvider
from .models import LLMMessage, LLMResponse, LLMToolCall, ToolDefinition


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider implementation"""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Union[ToolDefinition, Dict[str, Any]]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Make a direct LLM call using Anthropic SDK"""
        # Extract system messages and convert remaining messages to Anthropic format
        system_content, anthropic_messages = self._convert_messages_to_anthropic_format(messages)
        
        # Prepare Anthropic API call parameters
        params = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        
        # Add system parameter if system messages were found
        if system_content:
            params["system"] = system_content
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # Handle tools - Anthropic uses different format
        if tools:
            anthropic_tools = self.normalize_tool_definitions(tools)
            params["tools"] = anthropic_tools
            
            # Anthropic tool_choice options: "auto", "any", "tool" (with tool name), or None
            if tool_choice:
                if tool_choice == "auto":
                    params["tool_choice"] = {"type": "auto"}
                elif tool_choice == "none":
                    params["tool_choice"] = {"type": "none"}
                else:
                    # Specific tool name
                    params["tool_choice"] = {"type": "tool", "name": tool_choice}
            else:
                params["tool_choice"] = {"type": "auto"}
        
        # Make API call (now truly async!)
        try:
            response = await self.client.messages.create(**params)
            return self.parse_response(response)
        except Exception as e:
            # Re-raise with context
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise ValueError("Invalid ANTHROPIC_API_KEY. Please check your API key.")
            elif "429" in error_str or "rate limit" in error_str:
                raise ValueError("Rate limit exceeded. Please try again later.")
            elif "400" in error_str or "bad request" in error_str:
                raise ValueError(f"Bad request to Anthropic API: {str(e)}")
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
            
            # Build assistant message with content blocks for Anthropic
            # Anthropic assistant messages can have both text and tool_use blocks
            assistant_content_blocks = []
            
            # Add text content if present
            if response.content:
                assistant_content_blocks.append({
                    "type": "text",
                    "text": response.content
                })
            
            # Add tool_use blocks if present
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    assistant_content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.arguments
                    })
            
            # Add assistant message to conversation
            # Store content blocks as JSON string for Anthropic format
            if assistant_content_blocks:
                assistant_msg = LLMMessage(
                    role="assistant",
                    content=json.dumps(assistant_content_blocks)
                )
                conversation_messages.append(assistant_msg)
            elif response.content:
                # Just text, no tool calls
                assistant_msg = LLMMessage(
                    role="assistant",
                    content=response.content
                )
                conversation_messages.append(assistant_msg)
            
            # If no tool calls, return final response
            if not response.tool_calls:
                return response
            
            # Execute tool calls
            tool_result_blocks = []
            for tool_call in response.tool_calls:
                try:
                    # Execute tool
                    tool_result = tool_executor(tool_call.name, tool_call.arguments)
                    
                    # Format tool result as string
                    if isinstance(tool_result, dict):
                        tool_result_str = json.dumps(tool_result, indent=2)
                    else:
                        tool_result_str = str(tool_result)
                    
                    # Add tool result block
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": tool_result_str
                    })
                except Exception as e:
                    # Add error message
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Error executing tool {tool_call.name}: {str(e)}"
                    })
            
            # Add tool results as user message with content blocks
            if tool_result_blocks:
                tool_msg = LLMMessage(
                    role="user",  # Anthropic uses "user" role for tool results
                    content=json.dumps(tool_result_blocks)
                )
                conversation_messages.append(tool_msg)
        
        return response
    
    def normalize_tool_definitions(
        self, 
        tools: List[Union[ToolDefinition, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standardized tools to Anthropic format
        
        Anthropic format:
        {
            "name": "...",
            "description": "...",
            "input_schema": {...}  # Note: "input_schema" not "parameters"
        }
        """
        anthropic_tools = []
        for tool in tools:
            # Normalize to ToolDefinition
            tool_def = self._normalize_tool_input(tool)
            
            # Convert to Anthropic format
            anthropic_tool = {
                "name": tool_def.name,
                "description": tool_def.description,
                "input_schema": tool_def.parameters  # Anthropic uses "input_schema"
            }
            anthropic_tools.append(anthropic_tool)
        return anthropic_tools
    
    def parse_response(self, raw_response: Any) -> LLMResponse:
        """Parse Anthropic response to standardized format"""
        # Anthropic response structure:
        # response.content is a list of content blocks
        # Each block can be {"type": "text", "text": "..."} or {"type": "tool_use", ...}
        
        content = ""
        tool_calls = None
        
        # Parse content blocks
        if hasattr(raw_response, 'content') and raw_response.content:
            for block in raw_response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    # This is a tool call
                    if tool_calls is None:
                        tool_calls = []
                    
                    # Anthropic tool_use has: id, name, input (not arguments)
                    tool_calls.append(LLMToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input  # Anthropic uses "input" not "arguments"
                    ))
        
        # Parse usage
        usage = None
        if hasattr(raw_response, 'usage') and raw_response.usage:
            usage = {
                "prompt_tokens": getattr(raw_response.usage, 'input_tokens', 0),
                "completion_tokens": getattr(raw_response.usage, 'output_tokens', 0),
                "total_tokens": getattr(raw_response.usage, 'input_tokens', 0) + getattr(raw_response.usage, 'output_tokens', 0)
            }
        
        # Get stop reason
        finish_reason = None
        if hasattr(raw_response, 'stop_reason'):
            finish_reason = raw_response.stop_reason
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage
        )
    
    def _convert_messages_to_anthropic_format(
        self, 
        messages: List[LLMMessage]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert standardized messages to Anthropic format
        
        Anthropic format:
        - Messages have "role" and "content"
        - Content can be a string (for text) or list of content blocks
        - Tool results use "user" role with content blocks of type "tool_result"
        - Assistant messages with tool calls have content blocks of type "tool_use"
        - System messages are extracted and returned separately as a top-level system parameter
        
        Returns:
            tuple: (system_content, anthropic_messages)
                - system_content: Combined system message content (None if no system messages)
                - anthropic_messages: List of messages without system messages
        """
        system_messages = []
        anthropic_messages = []
        
        for msg in messages:
            # Extract system messages separately
            if msg.role == "system":
                system_messages.append(str(msg.content))
                continue
            
            if msg.role == "tool":
                # Anthropic uses "user" role for tool results with content blocks
                # Content should already be in JSON format from chat_completion_with_tools
                try:
                    # Try to parse as JSON (list of content blocks)
                    if isinstance(msg.content, str):
                        content_blocks = json.loads(msg.content)
                    else:
                        content_blocks = msg.content
                    
                    # Ensure it's a list
                    if not isinstance(content_blocks, list):
                        content_blocks = [content_blocks]
                    
                    anthropic_messages.append({
                        "role": "user",
                        "content": content_blocks
                    })
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, wrap in tool_result block
                    anthropic_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "",
                            "content": str(msg.content)
                        }]
                    })
            elif msg.role == "assistant" and msg.content and isinstance(msg.content, str) and msg.content.strip().startswith("["):
                # Assistant message might have content blocks (from previous tool calls)
                try:
                    content_blocks = json.loads(msg.content)
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": content_blocks
                    })
                except (json.JSONDecodeError, TypeError):
                    # Regular text content
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": msg.content
                    })
            elif msg.role == "user":
                # User message - could be regular text or tool results
                # Check if content is a JSON string representing tool_result blocks
                if isinstance(msg.content, str) and msg.content.strip().startswith("["):
                    try:
                        # Try to parse as JSON (might be tool_result blocks)
                        content_blocks = json.loads(msg.content)
                        # Check if it looks like tool_result blocks
                        if isinstance(content_blocks, list) and len(content_blocks) > 0:
                            if isinstance(content_blocks[0], dict) and content_blocks[0].get("type") == "tool_result":
                                # It's tool_result blocks - use as content blocks array
                                anthropic_messages.append({
                                    "role": "user",
                                    "content": content_blocks
                                })
                            else:
                                # Not tool_result blocks, treat as regular text
                                anthropic_messages.append({
                                    "role": "user",
                                    "content": msg.content
                                })
                        else:
                            # Not a valid list, treat as regular text
                            anthropic_messages.append({
                                "role": "user",
                                "content": msg.content
                            })
                    except (json.JSONDecodeError, TypeError):
                        # Not valid JSON, treat as regular text
                        anthropic_messages.append({
                            "role": "user",
                            "content": msg.content
                        })
                else:
                    # Regular user message (text)
                    anthropic_messages.append({
                        "role": "user",
                        "content": msg.content
                    })
            elif msg.role == "assistant":
                # Regular assistant message
                anthropic_messages.append({
                    "role": "assistant",
                    "content": msg.content
                })
            # Skip unsupported roles
        
        # Combine system messages into a single string
        system_content = None
        if system_messages:
            # If multiple system messages, join them with newlines
            system_content = "\n".join(system_messages)
        
        return system_content, anthropic_messages

