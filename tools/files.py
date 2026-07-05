"""File management tools for Jarvis."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.config import config
from jarvis.logger import logger


class FileManager:
    """Manages file operations within the workspace."""
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize file manager.
        
        Args:
            workspace_root: Workspace root directory
        """
        self.workspace_root = workspace_root or config.workspace_root
        logger.info(f"File manager initialized with workspace: {self.workspace_root}")
    
    def resolve_path(self, path: str, project_name: Optional[str] = None) -> Path:
        """
        Resolve a path relative to workspace or project.
        
        Args:
            path: Path to resolve
            project_name: Optional project name
            
        Returns:
            Resolved absolute Path
            
        Raises:
            ValueError: If path is outside workspace
        """
        # Convert to Path object
        path_obj = Path(path)
        
        # If absolute, use as-is but validate
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            # If project specified, resolve relative to project
            if project_name:
                project_path = self.workspace_root / project_name
                resolved = (project_path / path_obj).resolve()
            else:
                # Otherwise resolve relative to workspace
                resolved = (self.workspace_root / path_obj).resolve()
        
        # Security check: ensure path is within workspace
        try:
            resolved.relative_to(self.workspace_root.resolve())
        except ValueError:
            raise ValueError(
                f"Path '{path}' is outside the workspace. "
                f"All paths must be within {self.workspace_root}"
            )
        
        return resolved
    
    def read_file(self, path: str, project_name: Optional[str] = None) -> str:
        """
        Read a file.
        
        Args:
            path: Path to the file
            project_name: Optional project name
            
        Returns:
            File contents
            
        Raises:
            ValueError: If file doesn't exist or can't be read
        """
        try:
            resolved_path = self.resolve_path(path, project_name)
            
            if not resolved_path.exists():
                raise ValueError(f"File not found: {path}")
            
            if not resolved_path.is_file():
                raise ValueError(f"Path is not a file: {path}")
            
            # Check file size (limit to 10MB)
            file_size = resolved_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                raise ValueError(
                    f"File too large ({file_size / 1024 / 1024:.1f}MB). "
                    f"Maximum size is 10MB."
                )
            
            content = resolved_path.read_text(encoding='utf-8')
            logger.info(f"Read file: {resolved_path} ({len(content)} chars)")
            return content
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise ValueError(f"Failed to read file: {e}")
    
    def write_file(
        self,
        path: str,
        content: str,
        project_name: Optional[str] = None,
        create_dirs: bool = True
    ) -> Path:
        """
        Write content to a file.
        
        Args:
            path: Path to the file
            content: Content to write
            project_name: Optional project name
            create_dirs: Whether to create parent directories
            
        Returns:
            Path to the written file
            
        Raises:
            ValueError: If path is invalid or can't be written
        """
        try:
            resolved_path = self.resolve_path(path, project_name)
            
            # Create parent directories if needed
            if create_dirs:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            resolved_path.write_text(content, encoding='utf-8')
            logger.info(f"Wrote file: {resolved_path} ({len(content)} chars)")
            
            return resolved_path
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            raise ValueError(f"Failed to write file: {e}")
    
    def create_file(
        self,
        path: str,
        project_name: Optional[str] = None,
        create_dirs: bool = True
    ) -> Path:
        """
        Create an empty file.
        
        Args:
            path: Path to the file
            project_name: Optional project name
            create_dirs: Whether to create parent directories
            
        Returns:
            Path to the created file
            
        Raises:
            ValueError: If file already exists or can't be created
        """
        try:
            resolved_path = self.resolve_path(path, project_name)
            
            if resolved_path.exists():
                raise ValueError(f"File already exists: {path}")
            
            # Create parent directories if needed
            if create_dirs:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create empty file
            resolved_path.touch()
            logger.info(f"Created file: {resolved_path}")
            
            return resolved_path
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating file {path}: {e}")
            raise ValueError(f"Failed to create file: {e}")
    
    def list_files(
        self,
        directory: str = ".",
        project_name: Optional[str] = None,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List files in a directory.
        
        Args:
            directory: Directory path
            project_name: Optional project name
            recursive: Whether to list recursively
            
        Returns:
            List of file information dictionaries
        """
        try:
            resolved_dir = self.resolve_path(directory, project_name)
            
            if not resolved_dir.exists():
                raise ValueError(f"Directory not found: {directory}")
            
            if not resolved_dir.is_dir():
                raise ValueError(f"Path is not a directory: {directory}")
            
            files = []
            
            if recursive:
                # Recursive listing
                for item in sorted(resolved_dir.rglob("*")):
                    if item.is_file():
                        rel_path = item.relative_to(self.workspace_root)
                        files.append(self._get_file_info(item, rel_path))
            else:
                # Non-recursive listing
                for item in sorted(resolved_dir.iterdir()):
                    if item.is_file():
                        rel_path = item.relative_to(self.workspace_root)
                        files.append(self._get_file_info(item, rel_path))
            
            logger.info(f"Listed {len(files)} files in {resolved_dir}")
            return files
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            raise ValueError(f"Failed to list files: {e}")
    
    def search_files(
        self,
        pattern: str,
        project_name: Optional[str] = None,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for files matching a pattern.
        
        Args:
            pattern: Search pattern (glob pattern)
            project_name: Optional project name
            recursive: Whether to search recursively
            
        Returns:
            List of matching file information dictionaries
        """
        try:
            if project_name:
                search_dir = self.workspace_root / project_name
            else:
                search_dir = self.workspace_root
            
            if not search_dir.exists():
                raise ValueError(f"Directory not found: {search_dir}")
            
            matches = []
            
            if recursive:
                iterator = search_dir.rglob(pattern)
            else:
                iterator = search_dir.glob(pattern)
            
            for item in iterator:
                if item.is_file():
                    rel_path = item.relative_to(self.workspace_root)
                    matches.append(self._get_file_info(item, rel_path))
            
            logger.info(f"Found {len(matches)} files matching '{pattern}'")
            return matches
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error searching for files with pattern '{pattern}': {e}")
            raise ValueError(f"Failed to search files: {e}")
    
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


# Global file manager instance
file_manager = FileManager()


class ReadFileTool(BaseTool):
    """Tool for reading files."""
    
    name = "read_file"
    description = "Read the contents of a file"
    requires_confirmation = False
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["path"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            path = kwargs["path"]
            project_name = kwargs.get("project")
            
            content = file_manager.read_file(path, project_name)
            
            return ToolResult(
                success=True,
                message=f"Read file: {path}",
                data={
                    "path": path,
                    "content": content,
                    "size": len(content)
                }
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in read_file tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to read file: {e}",
                error=str(e)
            )


class WriteFileTool(BaseTool):
    """Tool for writing files."""
    
    name = "write_file"
    description = "Write content to a file"
    requires_confirmation = True
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        
        if "content" not in kwargs:
            return False, "Missing required argument: content"
        
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["path", "content"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            path = kwargs["path"]
            content = kwargs["content"]
            project_name = kwargs.get("project")
            
            resolved_path = file_manager.write_file(path, content, project_name)
            
            return ToolResult(
                success=True,
                message=f"File written successfully: {resolved_path}",
                data={
                    "path": str(resolved_path.relative_to(config.workspace_root)),
                    "size": len(content)
                }
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in write_file tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to write file: {e}",
                error=str(e)
            )


class CreateFileTool(BaseTool):
    """Tool for creating empty files."""
    
    name = "create_file"
    description = "Create a new empty file"
    requires_confirmation = True
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "path" not in kwargs:
            return False, "Missing required argument: path"
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["path"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            path = kwargs["path"]
            project_name = kwargs.get("project")
            
            resolved_path = file_manager.create_file(path, project_name)
            
            return ToolResult(
                success=True,
                message=f"File created successfully: {resolved_path}",
                data={
                    "path": str(resolved_path.relative_to(config.workspace_root))
                }
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in create_file tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to create file: {e}",
                error=str(e)
            )


class ListFilesTool(BaseTool):
    """Tool for listing files."""
    
    name = "list_files"
    description = "List files in a directory"
    requires_confirmation = False
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        # directory is optional
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            directory = kwargs.get("directory", ".")
            project_name = kwargs.get("project")
            recursive = kwargs.get("recursive", False)
            
            files = file_manager.list_files(directory, project_name, recursive)
            
            if not files:
                message = f"No files found in '{directory}'"
            else:
                message = f"Found {len(files)} file(s) in '{directory}':\n"
                for i, file_info in enumerate(files[:20], 1):  # Show first 20
                    size_kb = file_info["size"] / 1024
                    message += f"{i}. {file_info['path']} ({size_kb:.1f} KB)\n"
                
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
            logger.error(f"Error in list_files tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to list files: {e}",
                error=str(e)
            )


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
            
            files = file_manager.search_files(pattern, project_name, recursive)
            
            if not files:
                message = f"No files found matching pattern '{pattern}'"
            else:
                message = f"Found {len(files)} file(s) matching '{pattern}':\n"
                for i, file_info in enumerate(files[:20], 1):  # Show first 20
                    size_kb = file_info["size"] / 1024
                    message += f"{i}. {file_info['path']} ({size_kb:.1f} KB)\n"
                
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