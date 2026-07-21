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

    # ════ NEW: Code operations ════════════════

    # execute code / run file
    m = re.search(
        r"\b(?:run|execute|start)\b.*?\b(file|script|code)\b.*?['\"]?([\w./-]+\.\w+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="execute_file",
            args={"path": m.group(2), "language": "python"},
            reason=f"User asked to execute {m.group(2)}",
        )

    # scaffold / generate project
    _TEMPLATE_MAP = {
        "python": "python-package",
        "node": "node-package",
        "react": "node-package",
        "web": "node-package",
        "go": "go-module",
        "rust": "rust-project",
        "shell": "shell-script",
    }
    m = re.search(
        r"\b(scaffold|generate|create|make|new)\b.*?\b(python|node|react|go|rust|shell|web)\b.*?\b(project|app|package|module)\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        lang = m.group(2)
        template = _TEMPLATE_MAP.get(lang, "python-package")
        return ToolRequest(
            type="tool", tool="scaffold_project",
            args={"name": m.group(4), "template": template},
            reason=f"User asked to scaffold a {lang} project",
        )

    # lint / check code
    if re.search(r"\b(lint|check|analyze)\b.*\b(code|file|project)\b", lower):
        return ToolRequest(
            type="tool", tool="lint_code", args={"path": "."},
            reason="User asked to lint code",
        )

    # format code
    if re.search(r"\b(format|beautify|prettify)\b.*\b(code|file|project)\b", lower):
        return ToolRequest(
            type="tool", tool="format_code", args={"path": "."},
            reason="User asked to format code",
        )

    # count lines of code
    if re.search(r"\b(count|lines? of code|loc|cloc)\b", lower):
        return ToolRequest(
            type="tool", tool="count_lines", args={"path": "."},
            reason="User asked to count lines of code",
        )

    # search and replace
    m = re.search(
        r"\b(search|replace|find).*?(['\"])(.+?)\2.*?\b(?:with|to)\s+['\"]?(.+?)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="search_replace",
            args={"pattern": m.group(3), "replacement": m.group(4)},
            reason="User asked to search and replace",
        )

    # typecheck
    if re.search(r"\b(typecheck|type-check|type\s+check|mypy|tsc)\b", lower):
        return ToolRequest(
            type="tool", tool="typecheck_code", args={"path": "."},
            reason="User asked to type check code",
        )

    # list templates
    if re.search(r"\b(list|show)\b.*\b(templates|scaffolds|boilerplates)\b", lower):
        return ToolRequest(
            type="tool", tool="list_templates", args={},
            reason="User asked to list templates",
        )

    # create folder (direct)
    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_folder",
            args={"path": m.group(1)},
            reason=f"User asked to create folder {m.group(1)}",
        )

    return None


def casual_help_response() -> str:
    """Response for 'what can you do' style questions."""
    return (
        "I can help you manage a local workspace! Here's what I can do:\n"
        "  • Create and list projects\n"
        "  • Read, write, and search files\n"
        "  • Execute code (Python, JS, Go, Rust, Shell)\n"
        "  • Scaffold projects from templates\n"
        "  • Lint, format, and type-check code\n"
        "  • Search and replace across files\n"
        "  • Count lines of code\n"
        "  • Check git status and run tests\n\n"
        "Just ask naturally, like:\n"
        "  • \"list my projects\"\n"
        "  \"create a Python project called my-app\"\n"
        "  \"run main.py\"\n"
        "  \"lint this project\"\n"
        "  \"search for 'TODO' and replace with 'FIXME'\"\n"
        "  \"scaffold a new go module called api-server\""
    )
