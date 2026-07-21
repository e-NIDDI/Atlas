"""Tool registration for Jarvis.

Registers ALL tools with the tool registry.
This is the single source of truth for what tools are available.
"""

from jarvis.tools.registry import tool_registry
from jarvis.tools.projects import CreateProjectTool, ListProjectsTool, RenameProjectTool
from jarvis.tools.filesystem import (
    ReadFileTool,
    WriteFileTool,
    AppendFileTool,
    DeleteFileTool,
    CreateFolderTool,
    DeleteFolderTool,
    RenameItemTool,
    MoveItemTool,
    CopyItemTool,
    ListDirectoryTool,
    SearchFilesTool,
    SearchContentTool,
    GetMetadataTool,
)
from jarvis.tools.documents import (
    ReadDocumentTool,
    SummarizeDocumentTool,
    LocateInDocumentTool,
)
from jarvis.tools.secretary import (
    CreateNoteTool,
    SearchNotesTool,
    ListNotesTool,
    CreateTaskTool,
    ListTasksTool,
    CompleteTaskTool,
    RememberProjectContextTool,
    GetProjectContextTool,
    SearchMemoryTool,
)
from jarvis.tools.commands import GitStatusTool, RunTestsTool
from jarvis.tools.executor import ExecuteFileTool, ExecuteCodeTool
from jarvis.tools.scaffold import ScaffoldProjectTool, ListTemplatesTool
from jarvis.tools.analyzer import LintCodeTool, FormatCodeTool, TypeCheckTool, CountLinesTool
from jarvis.tools.refactor import SearchReplaceTool, EditLinesTool, RenameSymbolTool

from jarvis.logger import logger


def register_all_tools() -> None:
    """Register all available tools with the tool registry."""
    logger.info("Registering all tools...")

    # ── Project tools ──────────────────────────
    tool_registry.register(CreateProjectTool())
    tool_registry.register(ListProjectsTool())
    tool_registry.register(RenameProjectTool())

    # ── Filesystem tools ───────────────────────
    tool_registry.register(ReadFileTool())
    tool_registry.register(WriteFileTool())
    tool_registry.register(AppendFileTool())
    tool_registry.register(DeleteFileTool())
    tool_registry.register(CreateFolderTool())
    tool_registry.register(DeleteFolderTool())
    tool_registry.register(RenameItemTool())
    tool_registry.register(MoveItemTool())
    tool_registry.register(CopyItemTool())
    tool_registry.register(ListDirectoryTool())
    tool_registry.register(SearchFilesTool())
    tool_registry.register(SearchContentTool())
    tool_registry.register(GetMetadataTool())

    # ── Code Execution tools ───────────────────
    tool_registry.register(ExecuteFileTool())
    tool_registry.register(ExecuteCodeTool())

    # ── Code Analysis tools ────────────────────
    tool_registry.register(LintCodeTool())
    tool_registry.register(FormatCodeTool())
    tool_registry.register(TypeCheckTool())
    tool_registry.register(CountLinesTool())

    # ── Code Refactoring tools ─────────────────
    tool_registry.register(SearchReplaceTool())
    tool_registry.register(EditLinesTool())
    tool_registry.register(RenameSymbolTool())

    # ── Scaffolding tools ──────────────────────
    tool_registry.register(ScaffoldProjectTool())
    tool_registry.register(ListTemplatesTool())

    # ── Document tools ─────────────────────────
    tool_registry.register(ReadDocumentTool())
    tool_registry.register(SummarizeDocumentTool())
    tool_registry.register(LocateInDocumentTool())

    # ── Secretary tools ────────────────────────
    tool_registry.register(CreateNoteTool())
    tool_registry.register(SearchNotesTool())
    tool_registry.register(ListNotesTool())
    tool_registry.register(CreateTaskTool())
    tool_registry.register(ListTasksTool())
    tool_registry.register(CompleteTaskTool())
    tool_registry.register(RememberProjectContextTool())
    tool_registry.register(GetProjectContextTool())
    tool_registry.register(SearchMemoryTool())

    # ── Command tools ──────────────────────────
    tool_registry.register(GitStatusTool())
    tool_registry.register(RunTestsTool())

    logger.info(f"Registered {len(tool_registry.tools)} tools")
    logger.debug(f"Available tools: {tool_registry.list_tools()}")


# Auto-register tools on import
register_all_tools()