"""Jarvis tools layer."""

from jarvis.tools.registry import ToolRegistry, BaseTool, ToolResult, tool_registry
from jarvis.tools.projects import (
    ProjectManager,
    project_manager,
    CreateProjectTool,
    ListProjectsTool,
    RenameProjectTool,
)
from jarvis.tools.files import (
    FileManager,
    file_manager,
    ReadFileTool,
    WriteFileTool,
    CreateFileTool,
    ListFilesTool,
    SearchFilesTool,
)
from jarvis.tools.commands import (
    CommandManager,
    command_manager,
    GitStatusTool,
    RunTestsTool,
)
from jarvis.tools.search import (
    SearchManager,
    search_manager,
    SearchFilesTool,
    SearchContentTool,
)
from jarvis.tools.dispatcher import ToolDispatcher, tool_dispatcher, DispatchResult

__all__ = [
    "ToolRegistry",
    "BaseTool",
    "ToolResult",
    "tool_registry",
    "ProjectManager",
    "project_manager",
    "CreateProjectTool",
    "ListProjectsTool",
    "RenameProjectTool",
    "FileManager",
    "file_manager",
    "ReadFileTool",
    "WriteFileTool",
    "CreateFileTool",
    "ListFilesTool",
    "SearchFilesTool",
    "CommandManager",
    "command_manager",
    "GitStatusTool",
    "RunTestsTool",
    "SearchManager",
    "search_manager",
    "SearchContentTool",
    "ToolDispatcher",
    "tool_dispatcher",
    "DispatchResult",
]