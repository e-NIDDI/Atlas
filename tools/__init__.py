"""Jarvis tools layer.

All tools are registered via register_tools.py.
This module re-exports the key classes for convenience.
"""

from jarvis.tools.registry import ToolRegistry, BaseTool, ToolResult, tool_registry
from jarvis.tools.filesystem import FileSystemManager, fs
from jarvis.tools.documents import DocumentManager, document_manager
from jarvis.tools.secretary import SecretaryManager, secretary
from jarvis.tools.projects import (
    ProjectManager,
    project_manager,
    CreateProjectTool,
    ListProjectsTool,
    RenameProjectTool,
)
from jarvis.tools.commands import CommandManager, command_manager, GitStatusTool, RunTestsTool
from jarvis.tools.dispatcher import ToolDispatcher, tool_dispatcher, DispatchResult

__all__ = [
    "ToolRegistry",
    "BaseTool",
    "ToolResult",
    "tool_registry",
    "FileSystemManager",
    "fs",
    "DocumentManager",
    "document_manager",
    "SecretaryManager",
    "secretary",
    "ProjectManager",
    "project_manager",
    "CreateProjectTool",
    "ListProjectsTool",
    "RenameProjectTool",
    "CommandManager",
    "command_manager",
    "GitStatusTool",
    "RunTestsTool",
    "ToolDispatcher",
    "tool_dispatcher",
    "DispatchResult",
]