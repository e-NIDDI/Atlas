"""Parser for extracting structured actions from Ollama responses."""

import json
import re
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ValidationError

from jarvis.logger import logger


class ToolRequest(BaseModel):
    """Structured tool request from the model."""
    type: str
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    reason: str


class MessageResponse(BaseModel):
    """Normal chat message response."""
    type: str
    content: str


class ParseResult:
    """Result of parsing a model response."""
    
    def __init__(
        self,
        is_tool_request: bool,
        tool_request: Optional[ToolRequest] = None,
        message: Optional[str] = None,
        raw_response: str = ""
    ) -> None:
        """
        Initialize parse result.
        
        Args:
            is_tool_request: Whether this is a tool request
            tool_request: Parsed tool request if applicable
            message: Parsed message if applicable
            raw_response: Raw response from model
        """
        self.is_tool_request = is_tool_request
        self.tool_request = tool_request
        self.message = message
        self.raw_response = raw_response
    
    def __repr__(self) -> str:
        """String representation."""
        if self.is_tool_request:
            return f"ParseResult(tool={self.tool_request.tool}, args={self.tool_request.args})"
        return f"ParseResult(message={self.message[:50]}...)" if self.message else "ParseResult(empty)"


class ResponseParser:
    """Parser for Ollama model responses."""
    
    def __init__(self) -> None:
        """Initialize the parser."""
        self.tool_pattern = re.compile(
            r'\{[^{}]*"type"\s*:\s*"tool"[^{}]*\}',
            re.DOTALL | re.IGNORECASE
        )
        self.json_pattern = re.compile(
            r'\{.*\}',
            re.DOTALL
        )
    
    def parse(self, response: str) -> ParseResult:
        """
        Parse a model response.
        
        Args:
            response: Raw response from the model
            
        Returns:
            ParseResult object
        """
        logger.debug(f"Parsing response: {response[:200]}...")
        
        if not response or not response.strip():
            logger.warning("Empty response from model")
            return ParseResult(
                is_tool_request=False,
                message="I didn't receive a response. Please try again.",
                raw_response=response
            )
        
        # Try to find JSON in the response
        json_match = self._extract_json(response)
        
        if not json_match:
            # No JSON found, treat as normal message
            logger.debug("No JSON found, treating as normal message")
            return ParseResult(
                is_tool_request=False,
                message=response.strip(),
                raw_response=response
            )
        
        json_str = json_match
        logger.debug(f"Found JSON: {json_str[:200]}...")
        
        # Try to parse as ToolRequest
        try:
            data = json.loads(json_str)

            # Ollama error payloads: {"error": "..."}
            if "error" in data and "type" not in data:
                from jarvis.brain.errors import format_ollama_error
                return ParseResult(
                    is_tool_request=False,
                    message=format_ollama_error(data["error"]),
                    raw_response=response,
                )
            
            # Check if it's a tool request
            if data.get("type") == "tool":
                tool_request = ToolRequest(**data)
                logger.info(f"Parsed tool request: {tool_request.tool}")
                return ParseResult(
                    is_tool_request=True,
                    tool_request=tool_request,
                    raw_response=response
                )
            
            # Check if it's a message
            elif data.get("type") == "message":
                message_response = MessageResponse(**data)
                logger.debug("Parsed message response")
                return ParseResult(
                    is_tool_request=False,
                    message=message_response.content,
                    raw_response=response
                )
            
            else:
                # Unknown type, treat as normal message
                logger.warning(f"Unknown response type: {data.get('type')}")
                return ParseResult(
                    is_tool_request=False,
                    message=response.strip(),
                    raw_response=response
                )
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return ParseResult(
                is_tool_request=False,
                message=response.strip(),
                raw_response=response
            )
        except ValidationError as e:
            logger.warning(f"JSON validation failed: {e}")
            return ParseResult(
                is_tool_request=False,
                message=response.strip(),
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return ParseResult(
                is_tool_request=False,
                message=response.strip(),
                raw_response=response
            )
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON from text.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Extracted JSON string or None
        """
        # Strip markdown code fences (common with llama2 and similar models)
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 2:
                # Remove opening ```json or ``` line and closing ```
                inner_lines = lines[1:]
                if inner_lines and inner_lines[-1].strip() == "```":
                    inner_lines = inner_lines[:-1]
                stripped = "\n".join(inner_lines).strip()
                try:
                    json.loads(stripped)
                    return stripped
                except json.JSONDecodeError:
                    pass

        # First, try to find JSON with "type": "tool" or "type": "message"
        tool_match = self.tool_pattern.search(text)
        if tool_match:
            json_str = tool_match.group(0)
            # Validate it's valid JSON
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object
        json_matches = list(self.json_pattern.finditer(text))
        
        # Try each match from the end (most likely to be the actual response)
        for match in reversed(json_matches):
            json_str = match.group(0)
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                continue
        
        return None
    
    def validate_tool_request(self, tool_request: ToolRequest) -> Tuple[bool, Optional[str]]:
        """
        Validate a tool request.
        
        Args:
            tool_request: Tool request to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check tool name
        valid_tools = {
            "create_project",
            "list_projects",
            "rename_project",
            "read_file",
            "write_file",
            "create_file",
            "list_files",
            "search_files",
            "search_content",
            "git_status",
            "run_tests",
        }
        
        if tool_request.tool not in valid_tools:
            error = f"Invalid tool name: {tool_request.tool}. Valid tools: {', '.join(valid_tools)}"
            logger.warning(error)
            return False, error
        
        # Check required arguments for each tool
        required_args = {
            "create_project": ["name"],
            "rename_project": ["old_name", "new_name"],
            "read_file": ["path"],
            "write_file": ["path", "content"],
            "create_file": ["path"],
            "search_files": ["pattern"],
            "search_content": ["query"],
        }
        
        if tool_request.tool in required_args:
            missing = [arg for arg in required_args[tool_request.tool] if arg not in tool_request.args]
            if missing:
                error = f"Missing required arguments for {tool_request.tool}: {', '.join(missing)}"
                logger.warning(error)
                return False, error
        
        logger.debug(f"Tool request validated: {tool_request.tool}")
        return True, None


# Global parser instance
response_parser = ResponseParser()