"""Code refactoring tools for Jarvis.

Provides:
- Search and replace across files
- Multi-file targeted edits (insert/delete/replace at specific lines)
- Symbol renaming across a project
- Code block extraction
"""

import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.tools.filesystem import fs
from jarvis.config import config
from jarvis.logger import logger


# ──────────────────────────────────────────────
#  Refactoring Engine
# ──────────────────────────────────────────────

class RefactorEngine:
    """Safe refactoring operations across files."""

    def __init__(self) -> None:
        logger.info("Refactor engine initialized")

    def search_replace(
        self,
        pattern: str,
        replacement: str,
        path: str = ".",
        file_pattern: str = "*",
        regex: bool = False,
        case_sensitive: bool = False,
        max_replacements: int = 100,
        preview: bool = True,
    ) -> Dict[str, Any]:
        """Search and replace text across files.

        Args:
            pattern: Text or regex pattern to search for
            replacement: Replacement text
            path: File or directory to search in
            file_pattern: Glob pattern for files (when path is a directory)
            regex: Whether pattern is a regex
            case_sensitive: Whether search is case-sensitive
            max_replacements: Max total replacements
            preview: If True, only show what would change

        Returns:
            Dict with summary and per-file changes
        """
        resolved = fs.resolve_path(path, must_exist=True)

        files_to_process: List[Path] = []
        if resolved.is_file():
            files_to_process = [resolved]
        else:
            files_to_process = [
                f for f in resolved.rglob(file_pattern)
                if f.is_file() and not self._is_binary(f)
            ]

        if not files_to_process:
            raise ValueError(f"No files matching '{file_pattern}' in {path}")

        # Compile pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            if regex:
                search_re = re.compile(pattern, flags)
            else:
                search_re = re.compile(re.escape(pattern), flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        total_replacements = 0
        total_files_changed = 0
        file_changes = []

        for file_path in files_to_process:
            if total_replacements >= max_replacements:
                break

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            new_content, count = search_re.subn(replacement, content)

            if count == 0:
                continue

            rel_path = self._relative(file_path)
            file_changes.append({
                "path": str(rel_path),
                "replacements": count,
                "preview": self._generate_preview(content, new_content, search_re),
            })

            total_replacements += count
            total_files_changed += 1

            if not preview:
                file_path.write_text(new_content, encoding="utf-8")

        return {
            "pattern": pattern,
            "replacement": replacement,
            "files_searched": len(files_to_process),
            "files_changed": total_files_changed,
            "total_replacements": total_replacements,
            "preview_only": preview,
            "changes": file_changes,
        }

    def edit_lines(
        self,
        path: str,
        edits: List[Dict[str, Any]],
        preview: bool = True,
    ) -> Dict[str, Any]:
        """Apply targeted line edits to a file.

        Each edit dict can have:
        - type: "insert" | "delete" | "replace"
        - line: int (1-indexed line number)
        - content: str (for insert/replace)
        - end_line: int (for delete range)

        Args:
            path: Path to the file
            edits: List of edit operations
            preview: If True, only show what would change

        Returns:
            Dict with results
        """
        resolved = fs.resolve_path(path, must_exist=True)
        if not resolved.is_file():
            raise ValueError(f"Not a file: {path}")

        content = resolved.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        original_lines = list(lines)

        changes = []
        # Apply edits in reverse line order to preserve line numbers
        for edit in sorted(edits, key=lambda e: e.get("line", 1), reverse=True):
            line = edit.get("line", 1) - 1  # Convert to 0-indexed
            edit_type = edit.get("type", "replace")

            if line < 0 or line >= len(lines):
                changes.append({
                    "type": edit_type,
                    "line": edit["line"],
                    "error": "Line out of range",
                })
                continue

            old_line = lines[line] if line < len(lines) else ""

            if edit_type == "insert":
                content_str = edit.get("content", "")
                lines.insert(line, content_str)
                changes.append({
                    "type": "insert",
                    "line": edit["line"],
                    "content": content_str,
                    "success": True,
                })

            elif edit_type == "delete":
                end_line = edit.get("end_line", edit["line"]) - 1
                deleted_lines = lines[line:end_line + 1]
                del lines[line:end_line + 1]
                changes.append({
                    "type": "delete",
                    "line": edit["line"],
                    "end_line": edit.get("end_line", edit["line"]),
                    "deleted": deleted_lines,
                    "success": True,
                })

            elif edit_type == "replace":
                new_content = edit.get("content", "")
                lines[line] = new_content
                changes.append({
                    "type": "replace",
                    "line": edit["line"],
                    "old": old_line,
                    "new": new_content,
                    "success": True,
                })

        if not preview:
            resolved.write_text("\n".join(lines), encoding="utf-8")

        return {
            "path": str(self._relative(resolved)),
            "edits_applied": len([c for c in changes if c.get("success")]),
            "preview_only": preview,
            "changes": changes,
        }

    def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        path: str = ".",
        file_pattern: str = "*",
        language: Optional[str] = None,
        preview: bool = True,
    ) -> Dict[str, Any]:
        """Rename a symbol across a project.

        Uses word-boundary matching to avoid partial renames.
        For example, renaming "foo" won't affect "foobar".

        Args:
            old_name: Current symbol name
            new_name: New symbol name
            path: File or directory
            file_pattern: Glob pattern for files
            language: Language hint for smart scope detection
            preview: If True, only preview

        Returns:
            Dict with results
        """
        # Use word-boundary regex for safe renaming
        escaped = re.escape(old_name)
        pattern = rf'\b{escaped}\b'
        replacement = new_name

        return self.search_replace(
            pattern=pattern,
            replacement=replacement,
            path=path,
            file_pattern=file_pattern,
            regex=True,
            case_sensitive=True,
            preview=preview,
        )

    # ── Helpers ────────────────────────────────

    def _generate_preview(self, old_content: str, new_content: str, pattern: re.Pattern) -> str:
        """Generate a diff-like preview of changes."""
        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        preview_parts = []
        max_preview_lines = 10
        changes_shown = 0

        for i, (old, new) in enumerate(zip(old_lines, new_lines)):
            if old != new and pattern.search(old):
                preview_parts.append(f"  - L{i + 1}: {old[:80]}")
                preview_parts.append(f"  + L{i + 1}: {new[:80]}")
                changes_shown += 1
                if changes_shown >= max_preview_lines:
                    remaining = sum(1 for o, n in zip(old_lines, new_lines) if o != n)
                    preview_parts.append(f"  ... ({remaining - changes_shown} more changes)")
                    break

        return "\n".join(preview_parts)

    @staticmethod
    def _relative(path: Path) -> Path:
        """Get path relative to workspace."""
        try:
            return path.relative_to(config.workspace_root)
        except ValueError:
            return path

    @staticmethod
    def _is_binary(path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(path, "rb") as f:
                return b"\x00" in f.read(1024)
        except Exception:
            return True


# Global instance
refactor = RefactorEngine()


# ══════════════════════════════════════════════
#  Tool Implementations
# ══════════════════════════════════════════════

class SearchReplaceTool(BaseTool):
    """Search and replace text across files."""
    name = "search_replace"
    description = "Search and replace text across multiple files (with preview)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "pattern" not in kwargs:
            return False, "Missing required argument: pattern"
        if "replacement" not in kwargs:
            return False, "Missing required argument: replacement"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["pattern", "replacement"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            pattern = kwargs["pattern"]
            replacement = kwargs["replacement"]
            path = kwargs.get("path", ".")
            file_pattern = kwargs.get("file_pattern", "*")
            regex = kwargs.get("regex", False)
            case_sensitive = kwargs.get("case_sensitive", False)
            preview = kwargs.get("preview", True)
            max_replacements = kwargs.get("max_replacements", 100)

            result = refactor.search_replace(
                pattern=pattern,
                replacement=replacement,
                path=path,
                file_pattern=file_pattern,
                regex=regex,
                case_sensitive=case_sensitive,
                max_replacements=max_replacements,
                preview=preview,
            )

            lines = [
                f"Search & Replace: '{result['pattern']}' -> '{result['replacement']}'",
                f"  Files searched: {result['files_searched']}",
                f"  Files changed:  {result['files_changed']}",
                f"  Replacements:   {result['total_replacements']}",
                f"  Mode:           {'PREVIEW' if result['preview_only'] else 'APPLIED'}",
            ]

            if result["changes"]:
                lines.append("")
                for change in result["changes"][:10]:
                    lines.append(f"  📄 {change['path']} ({change['replacements']} replacements)")
                    if change.get("preview"):
                        for preview_line in change["preview"].split("\n")[:8]:
                            lines.append(f"    {preview_line}")
                if len(result["changes"]) > 10:
                    lines.append(f"    ... and {len(result['changes']) - 10} more files")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class EditLinesTool(BaseTool):
    """Insert, delete, or replace specific lines in a file."""
    name = "edit_lines"
    description = "Insert, delete, or replace specific lines in a file"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        if "edits" not in kwargs:
            return False, "Missing required argument: edits"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path", "edits"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            path = kwargs["path"]
            edits = kwargs["edits"]
            preview = kwargs.get("preview", True)

            result = refactor.edit_lines(path=path, edits=edits, preview=preview)

            lines = [
                f"Line edits for {result['path']}:",
                f"  Edits applied: {result['edits_applied']}",
                f"  Mode: {'PREVIEW' if result['preview_only'] else 'APPLIED'}",
            ]

            if result["changes"]:
                lines.append("")
                for change in result["changes"][:20]:
                    t = change["type"]
                    ln = change["line"]
                    if change.get("success"):
                        if t == "insert":
                            lines.append(f"  + L{ln}: {change.get('content', '')[:60]}")
                        elif t == "delete":
                            end = change.get("end_line", ln)
                            end_str = f"-{end}" if end != ln else ""
                            lines.append(f"  - L{ln}{end_str}")
                        elif t == "replace":
                            lines.append(f"  ~ L{ln}: {change.get('old', '')[:50]} -> {change.get('new', '')[:50]}")
                    else:
                        lines.append(f"  ! L{ln}: {change.get('error', 'failed')}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class RenameSymbolTool(BaseTool):
    """Rename a symbol (variable, function, class) across a project."""
    name = "rename_symbol"
    description = "Rename a symbol across files (safe word-boundary replacement)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "old_name" not in kwargs:
            return False, "Missing required argument: old_name"
        if "new_name" not in kwargs:
            return False, "Missing required argument: new_name"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["old_name", "new_name"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            old_name = kwargs["old_name"]
            new_name = kwargs["new_name"]
            path = kwargs.get("path", ".")
            file_pattern = kwargs.get("file_pattern", "*")
            preview = kwargs.get("preview", True)

            result = refactor.rename_symbol(
                old_name=old_name,
                new_name=new_name,
                path=path,
                file_pattern=file_pattern,
                preview=preview,
            )

            lines = [
                f"Rename symbol: '{old_name}' -> '{new_name}'",
                f"  Files searched: {result['files_searched']}",
                f"  Files changed:  {result['files_changed']}",
                f"  Replacements:   {result['total_replacements']}",
                f"  Mode:           {'PREVIEW' if result['preview_only'] else 'APPLIED'}",
            ]

            if result["changes"]:
                lines.append("")
                for change in result["changes"][:10]:
                    lines.append(f"  📄 {change['path']} ({change['replacements']} replacements)")
                    if change.get("preview"):
                        for preview_line in change["preview"].split("\n")[:6]:
                            lines.append(f"    {preview_line}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))
