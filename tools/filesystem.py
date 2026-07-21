"""Complete filesystem management tools for Jarvis.

Provides all file and directory operations:
read, write, append, delete, create_folder, delete_folder,
rename, move, copy, list, search, metadata.
"""

import os
import shutil
import stat
import fnmatch
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.config import config
from jarvis.logger import logger


# ──────────────────────────────────────────────
#  Core Filesystem Manager
# ──────────────────────────────────────────────

class FileSystemManager:
    """Complete filesystem operations within the workspace."""

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB read limit

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = (workspace_root or config.workspace_root).resolve()
        logger.info(f"FileSystemManager initialized: {self.workspace_root}")

    # ── Path resolution ────────────────────────

    def resolve_path(self, path: str, must_exist: bool = False) -> Path:
        """Resolve a path, validate it's within workspace, follow symlinks safely."""
        if not path or not path.strip():
            raise ValueError("Path cannot be empty")

        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve(strict=False)
        else:
            resolved = (self.workspace_root / p).resolve(strict=False)

        # Resolve symlinks for security check
        try:
            real = resolved.resolve(strict=False)
            real.relative_to(self.workspace_root)
        except ValueError:
            raise ValueError(
                f"Path '{path}' resolves outside workspace ({self.workspace_root}). "
                "All paths must be within the workspace."
            )

        if must_exist and not resolved.exists():
            raise ValueError(f"Path does not exist: {path}")

        return resolved

    # ── Read ───────────────────────────────────

    def read_file(self, path: str) -> str:
        """Read a text file. Returns content as string."""
        resolved = self.resolve_path(path, must_exist=True)
        if not resolved.is_file():
            raise ValueError(f"Not a file: {path}")

        size = resolved.stat().st_size
        if size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large ({size / 1024 / 1024:.1f} MB). "
                f"Max: {self.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
            )

        # Detect binary — if null bytes, refuse
        with open(resolved, 'rb') as f:
            header = f.read(1024)
            if b'\x00' in header:
                raise ValueError(
                    f"Binary file detected: {path}. "
                    "Use document reading tools for PDFs, DOCX, etc."
                )

        content = resolved.read_text(encoding='utf-8', errors='replace')
        logger.info(f"Read file: {resolved} ({len(content)} chars)")
        return content

    def read_file_binary(self, path: str) -> bytes:
        """Read a file as bytes (for document processing)."""
        resolved = self.resolve_path(path, must_exist=True)
        if not resolved.is_file():
            raise ValueError(f"Not a file: {path}")
        return resolved.read_bytes()

    # ── Write ──────────────────────────────────

    def write_file(self, path: str, content: str, create_dirs: bool = True) -> Path:
        """Write text content to a file. Creates parent dirs by default."""
        resolved = self.resolve_path(path)
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding='utf-8')
        logger.info(f"Wrote file: {resolved} ({len(content)} chars)")
        return resolved

    def append_file(self, path: str, content: str) -> Path:
        """Append text content to a file. Creates file if it doesn't exist."""
        resolved = self.resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, 'a', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Appended to file: {resolved} ({len(content)} chars)")
        return resolved

    # ── Delete ─────────────────────────────────

    def delete_file(self, path: str) -> None:
        """Delete a file. Raises if path is a directory or doesn't exist."""
        resolved = self.resolve_path(path, must_exist=True)
        if not resolved.is_file():
            raise ValueError(f"Not a file (or is a directory): {path}")
        resolved.unlink()
        logger.info(f"Deleted file: {resolved}")

    # ── Folder operations ──────────────────────

    def create_folder(self, path: str, exist_ok: bool = True) -> Path:
        """Create a directory (and parents)."""
        resolved = self.resolve_path(path)
        resolved.mkdir(parents=True, exist_ok=exist_ok)
        logger.info(f"Created folder: {resolved}")
        return resolved

    def delete_folder(self, path: str, recursive: bool = True) -> None:
        """Delete a directory. Recursive by default."""
        resolved = self.resolve_path(path, must_exist=True)
        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {path}")
        if recursive:
            shutil.rmtree(resolved)
        else:
            resolved.rmdir()
        logger.info(f"Deleted folder: {resolved}")

    # ── Rename / Move / Copy ───────────────────

    def rename_item(self, old_path: str, new_path: str) -> Tuple[Path, Path]:
        """Rename a file or directory."""
        src = self.resolve_path(old_path, must_exist=True)
        dst = self.resolve_path(new_path)
        if dst.exists():
            raise ValueError(f"Target already exists: {new_path}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        logger.info(f"Renamed: {src} -> {dst}")
        return src, dst

    def move_item(self, source: str, destination: str) -> Tuple[Path, Path]:
        """Move a file or directory to a new location."""
        src = self.resolve_path(source, must_exist=True)
        dst = self.resolve_path(destination)
        if dst.exists():
            raise ValueError(f"Target already exists: {destination}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        logger.info(f"Moved: {src} -> {dst}")
        return src, dst

    def copy_item(self, source: str, destination: str) -> Tuple[Path, Path]:
        """Copy a file or directory."""
        src = self.resolve_path(source, must_exist=True)
        dst = self.resolve_path(destination)
        if dst.exists():
            raise ValueError(f"Target already exists: {destination}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        logger.info(f"Copied: {src} -> {dst}")
        return src, dst

    # ── List / Search ──────────────────────────

    def list_directory(
        self,
        path: str = ".",
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> List[Dict[str, Any]]:
        """List contents of a directory."""
        resolved = self.resolve_path(path, must_exist=True)
        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {path}")

        items: List[Dict[str, Any]] = []
        iterator = resolved.rglob("*") if recursive else resolved.iterdir()

        for item in sorted(iterator):
            if not include_hidden and item.name.startswith('.'):
                continue
            try:
                rel = item.relative_to(self.workspace_root)
            except ValueError:
                rel = item
            items.append(self._file_info(item, rel))

        logger.info(f"Listed {len(items)} items in {resolved}")
        return items

    def search_files(
        self,
        pattern: str,
        directory: str = ".",
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for files by glob or regex pattern on filename."""
        resolved = self.resolve_path(directory, must_exist=True)
        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        matches: List[Dict[str, Any]] = []
        iterator = resolved.rglob("*") if recursive else resolved.glob("*")

        # Try as glob first
        try:
            for item in iterator:
                if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                    rel = item.relative_to(self.workspace_root)
                    matches.append(self._file_info(item, rel))
            if matches:
                logger.info(f"Glob search '{pattern}': {len(matches)} matches")
                return matches
        except Exception:
            pass

        # Try as regex
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            iterator = resolved.rglob("*") if recursive else resolved.iterdir()
            for item in iterator:
                if item.is_file() and regex.search(item.name):
                    rel = item.relative_to(self.workspace_root)
                    matches.append(self._file_info(item, rel))
            logger.info(f"Regex search '{pattern}': {len(matches)} matches")
        except re.error as e:
            raise ValueError(f"Invalid search pattern: {e}")

        return matches

    def search_content(
        self,
        query: str,
        directory: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        max_results: int = 50,
        context_lines: int = 2,
    ) -> List[Dict[str, Any]]:
        """Search for text within file contents (grep)."""
        resolved = self.resolve_path(directory, must_exist=True)
        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        results: List[Dict[str, Any]] = []
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            regex = re.compile(query, flags)
        except re.error:
            regex = re.compile(re.escape(query), flags)

        for file_path in resolved.rglob(file_pattern):
            if not file_path.is_file():
                continue
            if self._is_binary(file_path):
                continue

            try:
                text = file_path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue

            lines = text.split('\n')
            file_matches: List[Dict[str, Any]] = []

            for i, line in enumerate(lines):
                if regex.search(line):
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    file_matches.append({
                        "line_number": i + 1,
                        "line": line.strip(),
                        "context_before": [l.strip() for l in lines[start:i]],
                        "context_after": [l.strip() for l in lines[i + 1:end]],
                    })

            if file_matches:
                rel = file_path.relative_to(self.workspace_root)
                results.append({
                    "path": str(rel),
                    "absolute_path": str(file_path),
                    "matches": file_matches[:10],
                    "match_count": len(file_matches),
                })

            if len(results) >= max_results:
                break

        logger.info(f"Content search '{query}': {len(results)} files")
        return results

    # ── Metadata ───────────────────────────────

    def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get detailed metadata about a file or directory."""
        resolved = self.resolve_path(path, must_exist=True)
        try:
            rel = resolved.relative_to(self.workspace_root)
        except ValueError:
            rel = resolved

        stat_info = resolved.stat()
        is_file = resolved.is_file()
        is_dir = resolved.is_dir()
        is_symlink = resolved.is_symlink()

        meta = {
            "name": resolved.name,
            "path": str(rel),
            "absolute_path": str(resolved),
            "type": "file" if is_file else "directory" if is_dir else "other",
            "size": stat_info.st_size,
            "size_human": self._human_size(stat_info.st_size),
            "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            "permissions": stat.filemode(stat_info.st_mode),
            "is_symlink": is_symlink,
            "extension": resolved.suffix if is_file else None,
        }

        if is_symlink:
            try:
                meta["symlink_target"] = str(resolved.readlink())
            except Exception:
                meta["symlink_target"] = None

        if is_dir:
            try:
                meta["item_count"] = len(list(resolved.iterdir()))
            except Exception:
                meta["item_count"] = None

        logger.info(f"Metadata for {resolved}")
        return meta

    # ── Helpers ────────────────────────────────

    def _file_info(self, path: Path, rel: Path) -> Dict[str, Any]:
        """Get file info dict."""
        try:
            s = path.stat()
            return {
                "name": path.name,
                "path": str(rel),
                "absolute_path": str(path),
                "type": "file" if path.is_file() else "directory",
                "size": s.st_size,
                "size_human": self._human_size(s.st_size),
                "modified": datetime.fromtimestamp(s.st_mtime).isoformat(),
                "extension": path.suffix,
            }
        except Exception as e:
            return {
                "name": path.name,
                "path": str(rel),
                "absolute_path": str(path),
                "type": "unknown",
                "size": 0,
                "size_human": "0 B",
                "modified": None,
                "extension": path.suffix,
            }

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @staticmethod
    def _is_binary(path: Path) -> bool:
        try:
            with open(path, 'rb') as f:
                return b'\x00' in f.read(1024)
        except Exception:
            return True


# Global instance
fs = FileSystemManager()


# ══════════════════════════════════════════════
#  Tool Implementations
# ══════════════════════════════════════════════

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a text file (TXT, MD, PY, JS, etc.)"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            content = fs.read_file(kwargs["path"])
            return ToolResult(
                success=True,
                message=f"Read file: {kwargs['path']}",
                data={"path": kwargs["path"], "content": content, "size": len(content)},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file (creates parent directories if needed)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        if "content" not in kwargs:
            return False, "Missing required argument: content"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path", "content"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            resolved = fs.write_file(kwargs["path"], kwargs["content"])
            return ToolResult(
                success=True,
                message=f"File written: {resolved}",
                data={"path": str(resolved), "size": len(kwargs["content"])},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class AppendFileTool(BaseTool):
    name = "append_file"
    description = "Append content to an existing file (creates file if it doesn't exist)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        if "content" not in kwargs:
            return False, "Missing required argument: content"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path", "content"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            resolved = fs.append_file(kwargs["path"], kwargs["content"])
            return ToolResult(
                success=True,
                message=f"Appended to file: {resolved}",
                data={"path": str(resolved), "appended_size": len(kwargs["content"])},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a file permanently"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            fs.delete_file(kwargs["path"])
            return ToolResult(
                success=True,
                message=f"File deleted: {kwargs['path']}",
                data={"path": kwargs["path"]},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class CreateFolderTool(BaseTool):
    name = "create_folder"
    description = "Create a directory (and parent directories if needed)"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            resolved = fs.create_folder(kwargs["path"])
            return ToolResult(
                success=True,
                message=f"Folder created: {resolved}",
                data={"path": str(resolved)},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class DeleteFolderTool(BaseTool):
    name = "delete_folder"
    description = "Delete a directory (recursively deletes all contents)"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            fs.delete_folder(kwargs["path"])
            return ToolResult(
                success=True,
                message=f"Folder deleted: {kwargs['path']}",
                data={"path": kwargs["path"]},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class RenameItemTool(BaseTool):
    name = "rename_item"
    description = "Rename a file or directory"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "old_path" not in kwargs:
            return False, "Missing required argument: old_path"
        if "new_path" not in kwargs:
            return False, "Missing required argument: new_path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["old_path", "new_path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            src, dst = fs.rename_item(kwargs["old_path"], kwargs["new_path"])
            return ToolResult(
                success=True,
                message=f"Renamed: {src.name} -> {dst.name}",
                data={"old_path": str(src), "new_path": str(dst)},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class MoveItemTool(BaseTool):
    name = "move_item"
    description = "Move a file or directory to a new location"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "source" not in kwargs:
            return False, "Missing required argument: source"
        if "destination" not in kwargs:
            return False, "Missing required argument: destination"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["source", "destination"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            src, dst = fs.move_item(kwargs["source"], kwargs["destination"])
            return ToolResult(
                success=True,
                message=f"Moved: {src.name} -> {dst}",
                data={"source": str(src), "destination": str(dst)},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class CopyItemTool(BaseTool):
    name = "copy_item"
    description = "Copy a file or directory to a new location"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "source" not in kwargs:
            return False, "Missing required argument: source"
        if "destination" not in kwargs:
            return False, "Missing required argument: destination"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["source", "destination"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            src, dst = fs.copy_item(kwargs["source"], kwargs["destination"])
            return ToolResult(
                success=True,
                message=f"Copied: {src.name} -> {dst}",
                data={"source": str(src), "destination": str(dst)},
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List files and directories in a path"
    requires_confirmation = False

    def get_required_args(self) -> List[str]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        try:
            path = kwargs.get("path", ".")
            recursive = kwargs.get("recursive", False)
            include_hidden = kwargs.get("include_hidden", False)
            items = fs.list_directory(path, recursive, include_hidden)

            if not items:
                return ToolResult(
                    success=True,
                    message=f"Directory is empty: {path}",
                    data=[],
                )

            lines = [f"Contents of '{path}' ({len(items)} items):"]
            for item in items[:30]:
                t = "📄" if item["type"] == "file" else "📁"
                lines.append(f"  {t} {item['path']}  ({item['size_human']})")
            if len(items) > 30:
                lines.append(f"  ... and {len(items) - 30} more")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=items,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files by name pattern (glob or regex)"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "pattern" not in kwargs:
            return False, "Missing required argument: pattern"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["pattern"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            pattern = kwargs["pattern"]
            directory = kwargs.get("directory", ".")
            recursive = kwargs.get("recursive", True)
            files = fs.search_files(pattern, directory, recursive)

            if not files:
                return ToolResult(
                    success=True,
                    message=f"No files matching '{pattern}'",
                    data=[],
                )

            lines = [f"Found {len(files)} file(s) matching '{pattern}':"]
            for f in files[:20]:
                lines.append(f"  {f['path']}  ({f['size_human']})")
            if len(files) > 20:
                lines.append(f"  ... and {len(files) - 20} more")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=files,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class SearchContentTool(BaseTool):
    name = "search_content"
    description = "Search for text within file contents (grep)"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "query" not in kwargs:
            return False, "Missing required argument: query"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["query"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            query = kwargs["query"]
            directory = kwargs.get("directory", ".")
            file_pattern = kwargs.get("file_pattern", "*")
            case_sensitive = kwargs.get("case_sensitive", False)
            max_results = kwargs.get("max_results", 50)

            results = fs.search_content(
                query, directory, file_pattern, case_sensitive, max_results
            )

            if not results:
                return ToolResult(
                    success=True,
                    message=f"No matches for '{query}'",
                    data=[],
                )

            total = sum(r["match_count"] for r in results)
            lines = [f"Found {total} matches in {len(results)} file(s) for '{query}':"]
            for r in results[:10]:
                lines.append(f"  {r['path']} ({r['match_count']} matches)")
                for m in r["matches"][:3]:
                    lines.append(f"    L{m['line_number']}: {m['line'][:100]}")
            if len(results) > 10:
                lines.append(f"  ... and {len(results) - 10} more files")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=results,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))


class GetMetadataTool(BaseTool):
    name = "get_file_metadata"
    description = "Get detailed metadata about a file or directory"
    requires_confirmation = False

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["path"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            meta = fs.get_metadata(kwargs["path"])
            lines = [
                f"Metadata for: {meta['path']}",
                f"  Type:        {meta['type']}",
                f"  Size:        {meta['size_human']} ({meta['size']} bytes)",
                f"  Created:     {meta['created']}",
                f"  Modified:    {meta['modified']}",
                f"  Accessed:    {meta['accessed']}",
                f"  Permissions: {meta['permissions']}",
                f"  Symlink:     {meta['is_symlink']}",
            ]
            if meta.get("extension"):
                lines.append(f"  Extension:   {meta['extension']}")
            if meta.get("item_count") is not None:
                lines.append(f"  Items:       {meta['item_count']}")
            if meta.get("symlink_target"):
                lines.append(f"  Target:      {meta['symlink_target']}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data=meta,
            )
        except Exception as e:
            return ToolResult(success=False, message=str(e), error=str(e))