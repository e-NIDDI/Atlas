"""Simple intent detection for when small models fail to output proper JSON."""

import re
from typing import Optional

from jarvis.brain.parser import ToolRequest


def detect_tool_intent(message: str) -> Optional[ToolRequest]:
    """
    Detect tool intent from natural language.

    Fallback for small models that can't reliably produce JSON.
    """
    text = message.strip()
    lower = text.lower()

    # list projects
    if re.search(r"\b(list|show|what|see|display)\b.*\bprojects?\b", lower):
        return ToolRequest(
            type="tool", tool="list_projects", args={},
            reason="User asked to list projects",
        )
    if re.search(r"\bprojects?\b.*\b(list|show|have)\b", lower):
        return ToolRequest(
            type="tool", tool="list_projects", args={},
            reason="User asked to list projects",
        )

    # Create projects/directories. Check the destination before the generic
    # name-only pattern so "named app on the php directory" keeps its parent.
    m = re.search(
        r"\b(?:create|make|start|new)\b.*?\bproject\b.*?"
        r"\bin\s+(?:the\s+)?([\w-]+)(?:\s+folder|\s+directory)?\s+named\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(2), "parent": m.group(1)},
            reason=f"User asked to create project {m.group(2)} in {m.group(1)}/",
        )

    m = re.search(
        r"\b(?:create|make|start|new)\b.*?\bproject\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?\s+"
        r"(?:in|on|under|inside)\s+(?:the\s+)?([\w./-]+)"
        r"(?:\s+(?:folder|directory))?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(1), "parent": m.group(2)},
            reason=f"User asked to create project {m.group(1)} in {m.group(2)}/",
        )

    m = re.search(
        r"\b(?:create|make|start|new)\b.*?\bproject\b.*?(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(1)},
            reason=f"User asked to create project {m.group(1)}",
        )

    # TinyLlama often responds with shell advice for directory/folder requests,
    # so route them directly through the approved creation tool.
    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"\bin\s+(?:the\s+)?([\w./-]+)(?:\s+(?:folder|directory))?\s+"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(2), "parent": m.group(1)},
            reason=f"User asked to create directory {m.group(2)} in {m.group(1)}/",
        )

    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?\s+"
        r"(?:in|on|under|inside)\s+(?:the\s+)?([\w./-]+)"
        r"(?:\s+(?:folder|directory))?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(1), "parent": m.group(2)},
            reason=f"User asked to create directory {m.group(1)} in {m.group(2)}/",
        )

    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(1)},
            reason=f"User asked to create directory {m.group(1)}",
        )

    # read file
    m = re.search(
        r"\b(?:read|show|open|display|cat)\b.*?(?:file\s+)?['\"]?([\w./-]+\.\w+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="read_file",
            args={"path": m.group(1)},
            reason=f"User asked to read {m.group(1)}",
        )

    # list files
    if re.search(r"\b(list|show)\b.*\bfiles?\b", lower):
        return ToolRequest(
            type="tool", tool="list_files", args={},
            reason="User asked to list files",
        )

    # git status
    if re.search(r"\bgit\s+status\b", lower):
        return ToolRequest(
            type="tool", tool="git_status", args={},
            reason="User asked for git status",
        )

    return None


def casual_help_response() -> str:
    """Response for 'what can you do' style questions."""
    return (
        "I can help you manage a local workspace! Here's what I can do:\n"
        "  • Create and list projects\n"
        "  • Read, write, and search files\n"
        "  • Check git status and run tests\n\n"
        "Just ask naturally, like \"list my projects\" or \"create a project called my-app\"."
    )
