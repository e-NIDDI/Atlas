"""Code analysis, linting, and formatting tools for Jarvis.

Provides:
- Lint code (flake8, pylint, ruff, eslint)
- Format code (black, ruff, prettier)
- Type-check (mypy, pyright)
- Count lines of code (cloc / manual)
- Dependency analysis
- Code metrics (cyclomatic complexity, etc.)

Each tool auto-detects which linter/formatter to use
based on the project's language and config files.
"""

import subprocess
import asyncio
import re
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.tools.filesystem import fs
from jarvis.config import config
from jarvis.logger import logger


# ──────────────────────────────────────────────
#  Linter / Formatter Auto-Detection
# ──────────────────────────────────────────────

LINTERS: Dict[str, List[Dict[str, Any]]] = {
    "python": [
        {
            "name": "ruff",
            "command": "ruff",
            "args": ["check", "{path}"],
            "config_files": ["pyproject.toml", "ruff.toml", ".ruff.toml"],
            "description": "Fast Python linter",
        },
        {
            "name": "flake8",
            "command": "flake8",
            "args": ["{path}"],
            "config_files": [".flake8", "setup.cfg", "tox.ini"],
            "description": "Python style guide enforcer",
        },
        {
            "name": "pylint",
            "command": "pylint",
            "args": ["{path}"],
            "config_files": [".pylintrc", "pyproject.toml"],
            "description": "Python static analysis",
        },
    ],
    "javascript": [
        {
            "name": "eslint",
            "command": "eslint",
            "args": ["{path}"],
            "config_files": [".eslintrc", ".eslintrc.js", ".eslintrc.json"],
            "description": "JS/TS linter",
        },
    ],
    "typescript": [
        {
            "name": "eslint",
            "command": "eslint",
            "args": ["{path}"],
            "config_files": [".eslintrc", ".eslintrc.js", ".eslintrc.json"],
            "description": "JS/TS linter",
        },
    ],
}

FORMATTERS: Dict[str, List[Dict[str, Any]]] = {
    "python": [
        {
            "name": "ruff",
            "command": "ruff",
            "args": ["format", "{path}"],
            "config_files": ["pyproject.toml", "ruff.toml", ".ruff.toml"],
            "description": "Fast Python formatter",
        },
        {
            "name": "black",
            "command": "black",
            "args": ["{path}"],
            "config_files": ["pyproject.toml"],
            "description": "Python code formatter",
        },
    ],
    "javascript": [
        {
            "name": "prettier",
            "command": "prettier",
            "args": ["--write", "{path}"],
            "config_files": [".prettierrc", ".prettierrc.js", "package.json"],
            "description": "Code formatter",
        },
    ],
    "typescript": [
        {
            "name": "prettier",
            "command": "prettier",
            "args": ["--write", "{path}"],
            "config_files": [".prettierrc", ".prettierrc.js", "package.json"],
            "description": "Code formatter",
        },
    ],
}


# ──────────────────────────────────────────────
#  Analyzer Engine
# ──────────────────────────────────────────────

class Analyzer:
    """Code analysis and linting engine."""

    def __init__(self) -> None:
        logger.info("Analyzer initialized")

    def detect_language(self, path_str: str) -> str:
        """Detect the primary language of a file or project."""
        path = fs.resolve_path(path_str, must_exist=True)

        if path.is_file():
            ext = path.suffix.lower()
            ext_map = {
                ".py": "python",
                ".js": "javascript",
                ".jsx": "javascript",
                ".ts": "typescript",
                ".tsx": "typescript",
                ".go": "go",
                ".rs": "rust",
                ".java": "java",
                ".rb": "ruby",
                ".php": "php",
                ".swift": "swift",
                ".kt": "kotlin",
                ".sh": "shell",
                ".bash": "shell",
            }
            return ext_map.get(ext, "unknown")

        # Directory — look for project files
        for f in path.iterdir():
            name = f.name.lower()
            if name == "pyproject.toml" or name == "setup.py":
                return "python"
            if name == "package.json":
                return "javascript"
            if name == "go.mod":
                return "go"
            if name == "cargo.toml":
                return "rust"
            if name == "pom.xml" or name == "build.gradle":
                return "java"
            if name == "gemfile":
                return "ruby"
            if name == "composer.json":
                return "php"
            if name == "package.swift":
                return "swift"

        # Default: check for file extensions
        py_files = list(path.rglob("*.py"))
        if py_files:
            return "python"
        js_files = list(path.rglob("*.js")) or list(path.rglob("*.jsx"))
        if js_files:
            return "javascript"
        ts_files = list(path.rglob("*.ts")) or list(path.rglob("*.tsx"))
        if ts_files:
            return "typescript"
        go_files = list(path.rglob("*.go"))
        if go_files:
            return "go"
        rs_files = list(path.rglob("*.rs"))
        if rs_files:
            return "rust"

        return "unknown"

    async def lint(self, path_str: str, linter: Optional[str] = None) -> Dict[str, Any]:
        """Lint a file or project.

        Args:
            path_str: Path to file or directory
            linter: Specific linter to use (auto-detected if omitted)

        Returns:
            Dict with results, warnings, errors
        """
        resolved = fs.resolve_path(path_str, must_exist=True)
        lang = self.detect_language(str(resolved))

        available = LINTERS.get(lang, [])
        if not available:
            raise ValueError(
                f"No linters available for {lang}. "
                f"Supported: {', '.join(LINTERS.keys())}"
            )

        # If specific linter requested, find it
        if linter:
            candidates = [l for l in available if l["name"] == linter]
            if not candidates:
                raise ValueError(
                    f"Linter '{linter}' not available for {lang}. "
                    f"Available: {[l['name'] for l in available]}"
                )
            linters_to_try = candidates
        else:
            linters_to_try = available

        results = []
        all_issues = []

        for lint_cfg in linters_to_try:
            cmd = self._build_command(lint_cfg["command"], lint_cfg["args"], resolved)
            try:
                proc = await asyncio.to_thread(
                    lambda: subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        shell=False,
                    )
                )

                issues = self._parse_linter_output(lint_cfg["name"], proc.stdout + proc.stderr)
                results.append({
                    "linter": lint_cfg["name"],
                    "success": proc.returncode in (0, 1),  # 1 = lint found issues
                    "issues_count": len(issues),
                    "issues": issues,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                })
                all_issues.extend(issues)
            except FileNotFoundError:
                continue  # Try next linter
            except subprocess.TimeoutExpired:
                results.append({
                    "linter": lint_cfg["name"],
                    "success": False,
                    "issues_count": 0,
                    "issues": [],
                    "error": "Timed out",
                })
                continue

            if linter:
                break  # Only run the requested linter

        return {
            "path": str(resolved),
            "language": lang,
            "linters_run": len(results),
            "total_issues": len(all_issues),
            "results": results,
            "issues": all_issues[:100],  # Cap at 100 issues
        }

    async def format_code(self, path_str: str, formatter: Optional[str] = None) -> Dict[str, Any]:
        """Format a file or project.

        Args:
            path_str: Path to file or directory
            formatter: Specific formatter to use (auto-detected if omitted)

        Returns:
            Dict with results
        """
        resolved = fs.resolve_path(path_str, must_exist=True)
        lang = self.detect_language(str(resolved))

        available = FORMATTERS.get(lang, [])
        if not available:
            raise ValueError(
                f"No formatters available for {lang}. "
                f"Supported: {', '.join(FORMATTERS.keys())}"
            )

        if formatter:
            candidates = [f for f in available if f["name"] == formatter]
            if not candidates:
                raise ValueError(f"Formatter '{formatter}' not available for {lang}")
            formatters_to_try = candidates
        else:
            formatters_to_try = available

        results = []
        for fmt_cfg in formatters_to_try:
            cmd = self._build_command(fmt_cfg["command"], fmt_cfg["args"], resolved)
            try:
                proc = await asyncio.to_thread(
                    lambda: subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        shell=False,
                    )
                )

                results.append({
                    "formatter": fmt_cfg["name"],
                    "success": proc.returncode == 0,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                })
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                results.append({
                    "formatter": fmt_cfg["name"],
                    "success": False,
                    "error": "Timed out",
                })
                continue

            if formatter:
                break

        return {
            "path": str(resolved),
            "language": lang,
            "formatters_run": len(results),
            "results": results,
        }

    async def typecheck(self, path_str: str) -> Dict[str, Any]:
        """Run type checking on a project."""
        resolved = fs.resolve_path(path_str, must_exist=True)
        lang = self.detect_language(str(resolved))

        if lang == "python":
            return await self._run_typechecker("mypy", ["{path}"], resolved, "mypy")
        elif lang in ("javascript", "typescript"):
            return await self._run_typechecker("tsc", ["--noEmit", "{path}"], resolved, "tsc")
        elif lang == "go":
            return await self._run_typechecker("go", ["vet", "{path}"], resolved, "go vet")
        else:
            raise ValueError(f"Type checking not available for {lang}")

    def count_lines(self, path_str: str) -> Dict[str, Any]:
        """Count lines of code in a file or project."""
        resolved = fs.resolve_path(path_str, must_exist=True)

        result = {
            "path": str(resolved),
            "files": 0,
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "by_extension": {},
        }

        if resolved.is_file():
            files = [resolved]
        else:
            files = [
                f for f in resolved.rglob("*")
                if f.is_file() and not f.name.startswith(".")
                and f.suffix.lower() in self._code_extensions()
            ]

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.split("\n")
            ext = file_path.suffix.lower() or "(no ext)"

            if ext not in result["by_extension"]:
                result["by_extension"][ext] = {
                    "files": 0,
                    "lines": 0,
                    "code": 0,
                    "comments": 0,
                    "blank": 0,
                }

            ext_data = result["by_extension"][ext]
            ext_data["files"] += 1
            result["files"] += 1

            for line in lines:
                stripped = line.strip()
                result["total_lines"] += 1
                ext_data["lines"] += 1

                if not stripped:
                    result["blank_lines"] += 1
                    ext_data["blank"] += 1
                elif stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                    result["comment_lines"] += 1
                    ext_data["comments"] += 1
                else:
                    result["code_lines"] += 1
                    ext_data["code"] += 1

        return result

    # ── Internal ───────────────────────────────

    def _build_command(self, base_cmd: str, args_template: List[str], target: Path) -> List[str]:
        """Build a command from template."""
        cmd = [base_cmd]
        for arg in args_template:
            cmd.append(arg.replace("{path}", str(target)))
        return cmd

    async def _run_typechecker(
        self, command: str, args_template: List[str], target: Path, label: str
    ) -> Dict[str, Any]:
        """Run a type checker."""
        cmd = self._build_command(command, args_template, target)
        try:
            proc = await asyncio.to_thread(
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    shell=False,
                )
            )
            return {
                "tool": label,
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "return_code": proc.returncode,
            }
        except FileNotFoundError:
            return {"tool": label, "success": False, "error": f"{command} not found"}
        except subprocess.TimeoutExpired:
            return {"tool": label, "success": False, "error": "Timed out"}

    def _parse_linter_output(self, linter_name: str, output: str) -> List[Dict[str, Any]]:
        """Parse linter output into structured issues."""
        issues = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # ruff format: path:line:col: code message
            m = re.match(r"^(.+?):(\d+):(\d+):\s*(.+)$", line)
            if m:
                issues.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "column": int(m.group(3)),
                    "message": m.group(4),
                    "linter": linter_name,
                })
                continue

            # flake8 format: path:line:col: code message
            m = re.match(r"^(.+?):(\d+):(\d+):\s*(\w+\d+)\s+(.+)$", line)
            if m:
                issues.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "column": int(m.group(3)),
                    "code": m.group(4),
                    "message": m.group(5),
                    "linter": linter_name,
                })
                continue

            # Generic format: file(line,col): message
            m = re.match(r"^(.+?)\((\d+),(\d+)\):\s*(.+)$", line)
            if m:
                issues.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "column": int(m.group(3)),
                    "message": m.group(4),
                    "linter": linter_name,
                })

        return issues

    @staticmethod
    def _code_extensions() -> set:
        return {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".go", ".rs", ".java", ".rb", ".php",
            ".swift", ".kt", ".sh", ".bash",
            ".c", ".cpp", ".h", ".hpp",
            ".css", ".scss", ".html",
            ".json", ".yaml", ".yml", ".toml",
            ".sql", ".md", ".rst",
        }


# Global instance
analyzer = Analyzer()


# ══════════════════════════════════════════════
#  Tool Implementations
# ══════════════════════════════════════════════

class LintCodeTool(BaseTool):
    """Lint code files with available linters."""
    name = "lint_code"
    description = "Run linters on a file or project (ruff, flake8, pylint, eslint)"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            path = kwargs["path"]
            linter = kwargs.get("linter")
            result = await analyzer.lint(path, linter=linter)

            lines = [
                f"Lint results for {result['path']}",
                f"  Language: {result['language']}",
                f"  Linters run: {result['linters_run']}",
                f"  Total issues: {result['total_issues']}",
            ]

            if result["issues"]:
                lines.append(f"\n  Issues (showing up to 100):")
                for issue in result["issues"][:30]:
                    loc = f"L{issue.get('line', '?')}:{issue.get('column', '?')}"
                    msg = issue.get("message", "")
                    code = issue.get("code", "")
                    code_str = f" [{code}]" if code else ""
                    lines.append(f"    {loc}{code_str} {msg[:100]}")
                if len(result["issues"]) > 30:
                    lines.append(f"    ... and {len(result['issues']) - 30} more issues")
            else:
                lines.append("\n  ✅ No issues found!")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class FormatCodeTool(BaseTool):
    """Format code files with available formatters."""
    name = "format_code"
    description = "Format code using auto-detected formatters (ruff, black, prettier)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            path = kwargs["path"]
            formatter = kwargs.get("formatter")
            result = await analyzer.format_code(path, formatter=formatter)

            lines = [
                f"Format results for {result['path']}",
                f"  Language: {result['language']}",
                f"  Formatters run: {result['formatters_run']}",
            ]

            for r in result["results"]:
                status = "✓" if r["success"] else "✗"
                err = r.get("error", "")
                lines.append(f"    {status} {r['formatter']}")
                if err:
                    lines.append(f"       Error: {err}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class TypeCheckTool(BaseTool):
    """Run type checking on a project."""
    name = "typecheck_code"
    description = "Run type checking (mypy, tsc, go vet)"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            path = kwargs["path"]
            result = await analyzer.typecheck(path)

            lines = [
                f"Type check results for {path}:",
                f"  Tool: {result['tool']}",
                f"  Success: {'✓' if result['success'] else '✗'}",
            ]

            if result.get("stdout"):
                lines.append(f"\n  Output:\n{result['stdout'][:2000]}")
            if result.get("stderr"):
                lines.append(f"\n  Errors:\n{result['stderr'][:2000]}")
            if result.get("error"):
                lines.append(f"\n  Error: {result['error']}")

            return ToolResult(
                success=result["success"],
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class CountLinesTool(BaseTool):
    """Count lines of code in a file or project."""
    name = "count_lines"
    description = "Count lines of code, comments, and blanks in a file or project"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            path = kwargs["path"]
            result = analyzer.count_lines(path)

            lines = [
                f"Line counts for {result['path']}:",
                f"  Files:   {result['files']}",
                f"  Total:   {result['total_lines']}",
                f"  Code:    {result['code_lines']}",
                f"  Comment: {result['comment_lines']}",
                f"  Blank:   {result['blank_lines']}",
            ]

            if result["by_extension"]:
                lines.append("\n  By extension:")
                for ext, data in sorted(result["by_extension"].items()):
                    if ext == "(no ext)":
                        continue
                    lines.append(
                        f"    {ext:8s} {data['files']:3d} files, "
                        f"{data['code']:6d} code, {data['comments']:4d} comments, "
                        f"{data['blank']:4d} blank"
                    )

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))
