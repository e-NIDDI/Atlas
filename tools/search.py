"""Search tools for Jarvis."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import fnmatch
import re

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.config import config
from jarvis.logger import logger


class SearchManager:
    """Manages search operations within the workspace."""
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize search manager.
        
        Args:
            workspace_root: Workspace root directory
        """
        self.workspace_root = workspace_root or config.workspace_root
        logger.info(f"Search manager initialized with workspace: {self.workspace_root}")
    
    def search_by_pattern(
        self,
        pattern: str,
        project_name: Optional[str] = None,
        recursive: bool = True,
        search_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for files by pattern.
        
        Args:
            pattern: Search pattern (glob or regex)
            project_name: Optional project name
            recursive: Whether to search recursively
            search_content: Whether to search file contents
            
        Returns:
            List of matching file information dictionaries
        """
        try:
            # Determine search directory
            if project_name:
                search_dir = self.workspace_root / project_name
            else:
                search_dir = self.workspace_root
            
            if not search_dir.exists():
                raise ValueError(f"Directory not found: {search_dir}")
            
            matches = []
            
            # Try glob pattern first
            try:
                if recursive:
                    iterator = search_dir.rglob(pattern)
                else:
                    iterator = search_dir.glob(pattern)
                
                for item in iterator:
                    if item.is_file():
                        rel_path = item.relative_to(self.workspace_root)
                        file_info = self._get_file_info(item, rel_path)
                        
                        # Search content if requested
                        if search_content:
                            content_matches = self._search_in_file(item, pattern)
                            if content_matches:
                                file_info["content_matches"] = content_matches
                        
                        matches.append(file_info)
                
                if matches:
                    logger.info(f"Found {len(matches)} files matching glob pattern '{pattern}'")
                    return matches
            except Exception:
                # If glob fails, try regex
                pass
            
            # Try regex pattern
            try:
                regex = re.compile(pattern)
                
                if recursive:
                    iterator = search_dir.rglob("*")
                else:
                    iterator = search_dir.iterdir()
                
                for item in iterator:
                    if item.is_file():
                        # Check if filename matches
                        if regex.search(item.name):
                            rel_path = item.relative_to(self.workspace_root)
                            file_info = self._get_file_info(item, rel_path)
                            
                            # Search content if requested
                            if search_content:
                                content_matches = self._search_in_file(item, pattern)
                                if content_matches:
                                    file_info["content_matches"] = content_matches
                            
                            matches.append(file_info)
                
                logger.info(f"Found {len(matches)} files matching regex pattern '{pattern}'")
                return matches
                
            except re.error as e:
                logger.warning(f"Invalid regex pattern: {e}")
                raise ValueError(f"Invalid search pattern: {e}")
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error searching with pattern '{pattern}': {e}")
            raise ValueError(f"Failed to search: {e}")
    
    def search_content(
        self,
        query: str,
        project_name: Optional[str] = None,
        file_pattern: str = "*",
        case_sensitive: bool = False,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for text within files.
        
        Args:
            query: Text to search for
            project_name: Optional project name
            file_pattern: File pattern to search in
            case_sensitive: Whether search is case sensitive
            max_results: Maximum number of results
            
        Returns:
            List of search results with context
        """
        try:
            # Determine search directory
            if project_name:
                search_dir = self.workspace_root / project_name
            else:
                search_dir = self.workspace_root
            
            if not search_dir.exists():
                raise ValueError(f"Directory not found: {search_dir}")
            
            results = []
            
            # Get all files matching pattern
            files = list(search_dir.rglob(file_pattern))
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                # Skip binary files
                if self._is_binary(file_path):
                    continue
                
                # Search in file
                matches = self._search_in_file(
                    file_path,
                    query,
                    case_sensitive=case_sensitive,
                    context_lines=2
                )
                
                if matches:
                    rel_path = file_path.relative_to(self.workspace_root)
                    results.append({
                        "path": str(rel_path),
                        "absolute_path": str(file_path),
                        "matches": matches[:10],  # Limit matches per file
                        "match_count": len(matches)
                    })
                
                if len(results) >= max_results:
                    break
            
            logger.info(f"Content search found {len(results)} files matching '{query}'")
            return results
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error searching content for '{query}': {e}")
            raise ValueError(f"Failed to search content: {e}")
    
    def _search_in_file(
        self,
        file_path: Path,
        pattern: str,
        case_sensitive: bool = False,
        context_lines: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Search for pattern in a file.
        
        Args:
            file_path: Path to file
            pattern: Search pattern
            case_sensitive: Whether search is case sensitive
            context_lines: Number of context lines to include
            
        Returns:
            List of matches with context
        """
        matches = []
        
        try:
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            # Compile regex
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error:
                # If pattern is not valid regex, escape it
                escaped = re.escape(pattern)
                regex = re.compile(escaped, flags)
            
            # Search for matches
            for i, line in enumerate(lines):
                if regex.search(line):
                    # Get context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    
                    context = {
                        "line_number": i + 1,
                        "line": line,
                        "context_before": lines[start:i] if start < i else [],
                        "context_after": lines[i + 1:end] if i + 1 < end else []
                    }
                    matches.append(context)
            
        except Exception as e:
            logger.warning(f"Error searching in file {file_path}: {e}")
        
        return matches
    
    def _is_binary(self, file_path: Path) -> bool:
        """
        Check if a file is binary.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if binary, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except Exception:
            return False
    
    def _get_file_info(self, path: Path, rel_path: Path) -> Dict[str, Any]:
        """
        Get file information.
        
        Args:
            path: Absolute path
            rel_path: Relative path from workspace
            
        Returns:
            File information dictionary
        """
        try:
            stat = path.stat()
            return {
                "name": path.name,
                "path": str(rel_path),
                "absolute_path": str(path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": path.suffix,
            }
        except Exception as e:
            logger.warning(f"Error getting info for {path}: {e}")
            return {
                "name": path.name,
                "path": str(rel_path),
                "absolute_path": str(path),
                "size": 0,
                "modified": None,
                "extension": path.suffix,
            }


# Global search manager instance
search_manager = SearchManager()


class SearchFilesTool(BaseTool):
    """Tool for searching files."""
    
    name = "search_files"
    description = "Search for files matching a pattern"
    requires_confirmation = False
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "pattern" not in kwargs:
            return False, "Missing required argument: pattern"
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["pattern"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            pattern = kwargs["pattern"]
            project_name = kwargs.get("project")
            recursive = kwargs.get("recursive", True)
            search_content = kwargs.get("search_content", False)
            
            files = search_manager.search_by_pattern(
                pattern,
                project_name,
                recursive,
                search_content
            )
            
            if not files:
                message = f"No files found matching pattern '{pattern}'"
            else:
                message = f"Found {len(files)} file(s) matching '{pattern}':\n"
                for i, file_info in enumerate(files[:20], 1):  # Show first 20
                    size_kb = file_info["size"] / 1024
                    message += f"{i}. {file_info['path']} ({size_kb:.1f} KB)\n"
                    
                    # Show content matches if available
                    if "content_matches" in file_info:
                        for match in file_info["content_matches"][:3]:
                            message += f"   Line {match['line_number']}: {match['line'][:80]}\n"
                
                if len(files) > 20:
                    message += f"... and {len(files) - 20} more files\n"
            
            return ToolResult(
                success=True,
                message=message,
                data=files
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in search_files tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to search files: {e}",
                error=str(e)
            )


class SearchContentTool(BaseTool):
    """Tool for searching within file contents."""
    
    name = "search_content"
    description = "Search for text within files"
    requires_confirmation = False
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "query" not in kwargs:
            return False, "Missing required argument: query"
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["query"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            query = kwargs["query"]
            project_name = kwargs.get("project")
            file_pattern = kwargs.get("file_pattern", "*")
            case_sensitive = kwargs.get("case_sensitive", False)
            max_results = kwargs.get("max_results", 50)
            
            results = search_manager.search_content(
                query,
                project_name,
                file_pattern,
                case_sensitive,
                max_results
            )
            
            if not results:
                message = f"No results found for '{query}'"
            else:
                total_matches = sum(r["match_count"] for r in results)
                message = f"Found {total_matches} matches in {len(results)} file(s) for '{query}':\n\n"
                
                for i, result in enumerate(results[:10], 1):  # Show first 10 files
                    message += f"{i}. {result['path']} ({result['match_count']} matches)\n"
                    
                    # Show first few matches
                    for match in result["matches"][:3]:
                        message += f"   Line {match['line_number']}: {match['line'][:80]}\n"
                    
                    message += "\n"
                
                if len(results) > 10:
                    message += f"... and {len(results) - 10} more files\n"
            
            return ToolResult(
                success=True,
                message=message,
                data=results
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in search_content tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to search content: {e}",
                error=str(e)
            )