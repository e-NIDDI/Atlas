"""Tool registration for Jarvis."""

from jarvis.tools.registry import tool_registry
from jarvis.tools.projects import CreateProjectTool, ListProjectsTool, RenameProjectTool
from jarvis.tools.files import ReadFileTool, WriteFileTool, CreateFileTool, ListFilesTool, SearchFilesTool
from jarvis.tools.commands import GitStatusTool, RunTestsTool
from jarvis.tools.search import SearchFilesTool, SearchContentTool

from jarvis.logger import logger


def register_all_tools() -> None:
    """Register all available tools with the tool registry."""
    logger.info("Registering all tools...")
    
    # Project tools
    tool_registry.register(CreateProjectTool())
    tool_registry.register(ListProjectsTool())
    tool_registry.register(RenameProjectTool())
    
    # File tools
    tool_registry.register(ReadFileTool())
    tool_registry.register(WriteFileTool())
    tool_registry.register(CreateFileTool())
    tool_registry.register(ListFilesTool())
    tool_registry.register(SearchFilesTool())
    
    # Command tools
    tool_registry.register(GitStatusTool())
    tool_registry.register(RunTestsTool())
    
    # Search tools
    tool_registry.register(SearchContentTool())
    
    logger.info(f"Registered {len(tool_registry.tools)} tools")
    logger.debug(f"Available tools: {tool_registry.list_tools()}")


# Auto-register tools on import
register_all_tools()