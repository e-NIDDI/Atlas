"""Tool registry for Jarvis."""

from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

from jarvis.logger import logger


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Base class for all tools."""
    
    name: str = "base_tool"
    description: str = "Base tool"
    requires_confirmation: bool = False
    
    def __init__(self) -> None:
        """Initialize the tool."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            ToolResult object
        """
        pass
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate tool arguments.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
    
    def get_required_args(self) -> List[str]:
        """
        Get list of required arguments.
        
        Returns:
            List of required argument names
        """
        return []
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.name})"


class ToolRegistry:
    """Registry for all available tools."""
    
    def __init__(self) -> None:
        """Initialize the tool registry."""
        self.tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
        logger.debug(f"Tool registered: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """
        List all registered tools.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a tool.
        
        Args:
            name: Tool name
            
        Returns:
            Tool information dictionary or None
        """
        tool = self.tools.get(name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "requires_confirmation": tool.requires_confirmation,
            "required_args": tool.get_required_args(),
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Tool name
            **kwargs: Tool arguments
            
        Returns:
            ToolResult object
        """
        tool = self.tools.get(tool_name)
        
        if not tool:
            error = f"Tool not found: {tool_name}"
            logger.error(error)
            return ToolResult(
                success=False,
                message=f"Tool '{tool_name}' not found",
                error=error
            )
        
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
        
        try:
            # Validate arguments
            is_valid, error_msg = tool.validate_args(**kwargs)
            if not is_valid:
                logger.error(f"Invalid arguments for {tool_name}: {error_msg}")
                return ToolResult(
                    success=False,
                    message=f"Invalid arguments: {error_msg}",
                    error=error_msg
                )
            
            # Execute tool
            result = await tool.execute(**kwargs)
            logger.info(f"Tool {tool_name} executed: success={result.success}")
            return result
            
        except Exception as e:
            error = f"Error executing tool {tool_name}: {e}"
            logger.error(error, exc_info=True)
            return ToolResult(
                success=False,
                message=f"Error executing tool: {e}",
                error=error
            )
    
    def get_tools_requiring_confirmation(self) -> List[str]:
        """
        Get list of tools that require confirmation.
        
        Returns:
            List of tool names requiring confirmation
        """
        return [
            name for name, tool in self.tools.items()
            if tool.requires_confirmation
        ]


# Global tool registry instance
tool_registry = ToolRegistry()