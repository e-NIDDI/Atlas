"""Simple intent detection for when small models fail to output proper JSON.

This is the fallback for small models (tinyllama, qwen2.5:1.5b, etc.)
that can't reliably produce structured JSON tool requests.

Patterns checked BEFORE LLM call in agent.py, so these MUST be broad
enough to catch common user phrasings for all available tools.
"""

import re
from typing import Optional

from jarvis.brain.parser import ToolRequest


# ── Main intent detection ────────────────────────────────

def detect_tool_intent(message: str) -> Optional[ToolRequest]:
    """
    Detect tool intent from natural language.

    Fallback for small models that can't reliably produce JSON.
    Returns a ToolRequest if a clear intent is detected, None otherwise.
    """
    text = message.strip()
    lower = text.lower()

    # HELP / CAPABILITIES — Not handled here. Greetings/help questions
    # are caught by is_casual_chat() in brain/sanitize.py (_HELP_RE / _CASUAL_RE)
    # before detect_tool_intent is even called.

    # ══════════════════════════════════════════════════════
    #  LIST PROJECTS
    # ══════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════
    #  SCAFFOLD PROJECT (check BEFORE generic create_project
    #  so "scaffold python project called X" routes correctly)
    # ══════════════════════════════════════════════════════

    _TEMPLATE_MAP = {
        "python": "python-package",
        "node": "node-package",
        "react": "node-package",
        "web": "node-package",
        "go": "go-module",
        "rust": "rust-project",
        "shell": "shell-script",
        "html": "html-website",
        "html5": "html-website",
    }
    _LANG_RE = r"\b(python|node|react|go|rust|shell|web|html|html5)\b"

    # "make / create / start / scaffold a(n) language project called X"
    m = re.search(
        r"\b(?:scaffold|generate|create|make|start|new)\b.*?"
        + _LANG_RE + r".*?"
        r"\b(?:project|app|package|module|site|website)\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        lang = m.group(1)
        template = _TEMPLATE_MAP.get(lang, "python-package")
        return ToolRequest(
            type="tool", tool="scaffold_project",
            args={"name": m.group(2), "template": template},
            reason=f"User asked to create a {lang} project",
        )

    # "make a language project" (no name given) — auto-name it
    m = re.search(
        r"\b(?:scaffold|generate|create|make|start|new)\b.*?"
        + _LANG_RE + r".*?"
        r"\b(?:project|app|package|module|site|website)\b",
        lower,
    )
    if m:
        lang = m.group(1)
        template = _TEMPLATE_MAP.get(lang, "python-package")
        # Normalize: strip version numbers from lang names (e.g. html5 -> html)
        display_lang = lang.rstrip("0123456789")
        default_name = f"{lang}-project"
        return ToolRequest(
            type="tool", tool="scaffold_project",
            args={"name": default_name, "template": template},
            reason=f"User asked to create a {display_lang} project (no name given, using '{default_name}')",
        )

    # ══════════════════════════════════════════════════════
    #  CREATE PROJECT (explicit "project" keyword only)
    #  Note: "scaffold|generate" is NOT in the alternation
    #  below — scaffold-with-language was checked above.
    # ══════════════════════════════════════════════════════

    # "create project called X in parent/"
    m = re.search(
        r"\b(?:create|make|start|new)\b.*?\bproject\b.*?"
        r"\bin\s+(?:the\s+)?([\w-]+)(?:\s+folder|\s+directory)?\s+"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(2), "parent": m.group(1)},
            reason=f"User asked to create project {m.group(2)} in {m.group(1)}/",
        )

    # "create project called X in / under parent"
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

    # "create / scaffold / generate project called X"
    m = re.search(
        r"\b(?:create|make|start|new|scaffold|generate)\b.*?\bproject\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_project",
            args={"name": m.group(1)},
            reason=f"User asked to create project {m.group(1)}",
        )

    # ══════════════════════════════════════════════════════
    #  CREATE FOLDER / DIRECTORY  (→ create_folder tool)
    # ══════════════════════════════════════════════════════

    # "create folder called X in parent/"
    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"\bin\s+(?:the\s+)?([\w./-]+)(?:\s+folder|\s+directory)?\s+"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_folder",
            args={"path": f"{m.group(1)}/{m.group(2)}"},
            reason=f"User asked to create folder {m.group(2)} in {m.group(1)}/",
        )

    # "create folder called X in / under parent"
    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"(?:called|named)\s+['\"]?([\w-]+)['\"]?\s+"
        r"(?:in|on|under|inside)\s+(?:the\s+)?([\w./-]+)"
        r"(?:\s+(?:folder|directory))?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_folder",
            args={"path": f"{m.group(2)}/{m.group(1)}"},
            reason=f"User asked to create folder {m.group(1)} in {m.group(2)}/",
        )

    # "create folder/directory called / named X"
    m = re.search(
        r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b.*?"
        r"(?:called|named)\s+['\"]?([\w./-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="create_folder",
            args={"path": m.group(1)},
            reason=f"User asked to create folder {m.group(1)}",
        )

    # "make a folder" / "make a directory" (no name given)
    # Don't auto-create with a generic name — return None and let the
    # LLM ask what to name it (or fall back to a clearer prompt).
    if re.search(r"\b(?:create|make|new)\b.*?\b(?:directory|folder)\b", lower):
        return ToolRequest(
            type="tool", tool="create_folder",
            args={"path": "new-folder"},
            reason="User asked to create a folder (no name given, using default)",
        )

    # ══════════════════════════════════════════════════════
    #  FILE OPERATIONS
    # ══════════════════════════════════════════════════════

    # "create file called X"
    m = re.search(
        r"\b(?:create|make|new)\b.*?\bfile\b.*?"
        r"(?:called|named)\s+['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="write_file",
            args={"path": m.group(1), "content": ""},
            reason=f"User asked to create file {m.group(1)}",
        )

    # "write X to file" / "write to X" — broader match
    m = re.search(
        r"\b(?:write|add|put)\b\s+"
        r"(?:[\w\s]+?)?\b"
        r"(?:to|in|into)\s+(?:a\s+)?(?:file\s+)?['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="write_file",
            args={"path": m.group(1), "content": ""},  # content filled by agent
            reason=f"User asked to write to {m.group(1)}",
        )

    # "write code that does X to file Y"
    m = re.search(
        r"\b(?:write|generate|create|make)\b.*?"
        r"(?:code|script|program|function|class|module)\b.*?"
        r"(?:called|named)\s+['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="write_file",
            args={"path": m.group(1), "content": ""},
            reason=f"User asked to write code to {m.group(1)}",
        )

    # "read file X"
    m = re.search(
        r"\b(?:read|show|open|display|cat|view)\b.*?"
        r"(?:file\s+)?['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="read_file",
            args={"path": m.group(1)},
            reason=f"User asked to read {m.group(1)}",
        )

    # "list files" or "show files"
    if re.search(r"\b(list|show)\b.*\bfiles?\b", lower):
        return ToolRequest(
            type="tool", tool="list_directory", args={},
            reason="User asked to list files",
        )

    # "list / show directory X"
    m = re.search(
        r"\b(list|show|what'?s\s+in)\b.*?"
        r"(?:directory|folder)\s+['\"]?([\w./-]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="list_directory",
            args={"path": m.group(2)},
            reason=f"User asked to list {m.group(2)}",
        )

    # "delete / remove file X"
    m = re.search(
        r"\b(?:delete|remove|erase|rm)\b\s+"
        r"(?:file\s+)?['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="delete_file",
            args={"path": m.group(1)},
            reason=f"User asked to delete {m.group(1)}",
        )

    # ══════════════════════════════════════════════════════
    #  CODE OPERATIONS  (added in the code-capabilities patch)
    # ══════════════════════════════════════════════════════

    # git status
    if re.search(r"\bgit\s+status\b", lower):
        return ToolRequest(
            type="tool", tool="git_status", args={},
            reason="User asked for git status",
        )

    # "run / execute file X"
    m = re.search(
        r"\b(?:run|execute|start)\b.*?"
        r"(?:file|script|code)\s+['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="execute_file",
            args={"path": m.group(1)},
            reason=f"User asked to execute {m.group(1)}",
        )

    # (scaffold pattern moved above the create_project section)

    # "lint / check code"
    if re.search(r"\b(lint|check|analyze)\b.*\b(code|file|project)\b", lower):
        return ToolRequest(
            type="tool", tool="lint_code", args={"path": "."},
            reason="User asked to lint code",
        )

    # "format / beautify code"
    if re.search(r"\b(format|beautify|prettify)\b.*\b(code|file|project)\b", lower):
        return ToolRequest(
            type="tool", tool="format_code", args={"path": "."},
            reason="User asked to format code",
        )

    # "typecheck / type check / mypy"
    if re.search(r"\b(typecheck|type-check|type\s+check|mypy|tsc)\b", lower):
        return ToolRequest(
            type="tool", tool="typecheck_code", args={"path": "."},
            reason="User asked to type check code",
        )

    # "count lines / loc / cloc"
    if re.search(r"\b(count|lines?\s+of\s+code|loc|cloc)\b", lower):
        return ToolRequest(
            type="tool", tool="count_lines", args={"path": "."},
            reason="User asked to count lines of code",
        )

    # "search for X and replace with Y"
    m = re.search(
        r"\b(search|replace|find)\b.*?"
        r"['\u201c]([^'\u201d]+)['\u201d]\s*.*?"
        r"\b(?:with|to)\s+['\u201c]([^'\u201d]+)['\u201d]",
        lower,
    )
    if m:
        return ToolRequest(
            type="tool", tool="search_replace",
            args={"pattern": m.group(2), "replacement": m.group(3)},
            reason="User asked to search and replace",
        )

    # "list / show templates"
    if re.search(r"\b(list|show)\b.*\b(templates|scaffolds|boilerplates)\b", lower):
        return ToolRequest(
            type="tool", tool="list_templates", args={},
            reason="User asked to list templates",
        )

    # ══════════════════════════════════════════════════════
    #  GENERIC CATCHERS (last resort — very broad patterns)
    # ══════════════════════════════════════════════════════

    # "create X" where X has an extension → write_file
    m = re.search(
        r"\b(?:create|make|generate)\b\s+(?:a\s+|an\s+)?"
        r"['\"]?([\w./-]+\.[\w]+)['\"]?",
        lower,
    )
    if m:
        ext = m.group(1).rsplit(".", 1)[-1].lower()
        if ext in ("py", "js", "ts", "jsx", "tsx", "txt", "md", "json", "yaml", "yml", "html", "css", "sh", "go", "rs", "java", "rb", "php", "sql"):
            return ToolRequest(
                type="tool", tool="write_file",
                args={"path": m.group(1), "content": ""},
                reason=f"User asked to create file {m.group(1)}",
            )

    # No intent detected
    return None


# ══════════════════════════════════════════════════════════
#  HELP TEXT
# ══════════════════════════════════════════════════════════

def casual_help_response() -> str:
    """Response for 'what can you do' style questions."""
    return (
        "I'm Jarvis, your local AI workspace assistant! Here's what I can do:\n\n"

        "📁 **Files & Folders**\n"
        "  • \"create a folder called my-folder\"\n"
        "  • \"create a file called app.py\"\n"
        "  • \"read README.md\"\n"
        "  • \"write code to main.py\"\n"
        "  • \"list my files\"\n"
        "  • \"delete old-file.txt\"\n\n"

        "📦 **Projects**\n"
        "  • \"create a project called my-app\"\n"
        "  • \"list my projects\"\n"
        "  • \"scaffold a python project called my-package\"\n\n"

        "⚡ **Code**\n"
        "  • \"run main.py\"\n"
        "  • \"lint this project\"\n"
        "  • \"format my code\"\n"
        "  • \"typecheck my project\"\n"
        "  • \"search for 'TODO' and replace with 'FIXME'\"\n"
        "  • \"count lines of code\"\n\n"

        "📋 **Other**\n"
        "  • \"check git status\"\n"
        "  • \"run tests\"\n"
        "  • \"list all templates\"\n\n"

        "Most actions that change files will ask for your approval first. ✅"
    )
