"""Path safety validation for Jarvis."""

from pathlib import Path
from typing import Optional
from jarvis.config import config
from jarvis.logger import logger


class PathValidator:
    """Validates and sanitizes file paths for safety."""
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize path validator.
        
        Args:
            workspace_root: Workspace root directory
        """
        self.workspace_root = (workspace_root or config.workspace_root).resolve()
        logger.info(f"Path validator initialized with workspace: {self.workspace_root}")
    
    def validate_path(self, path: str, must_exist: bool = False) -> Path:
        """
        Validate a path is safe and within workspace.
        
        Args:
            path: Path to validate
            must_exist: Whether the path must exist
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path is invalid or outside workspace
        """
        if not path or not path.strip():
            raise ValueError("Path cannot be empty")
        
        # Convert to Path object
        path_obj = Path(path)
        
        # Resolve to absolute path
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            # Relative path - resolve from workspace
            resolved = (self.workspace_root / path_obj).resolve()
        
        # Security check: ensure path is within workspace
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise ValueError(
                f"Path '{path}' is outside the workspace. "
                f"All paths must be within {self.workspace_root}"
            )
        
        # Check if path exists (if required)
        if must_exist and not resolved.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        # Check for path traversal attempts
        if ".." in path_obj.parts:
            logger.warning(f"Path traversal attempt detected: {path}")
            # We allow it if it resolves within workspace, but log it
        
        logger.debug(f"Path validated: {path} -> {resolved}")
        return resolved
    
    def validate_file_path(
        self,
        path: str,
        must_exist: bool = False,
        must_be_file: bool = False
    ) -> Path:
        """
        Validate a file path.
        
        Args:
            path: Path to validate
            must_exist: Whether the file must exist
            must_be_file: Whether the path must be a file (not directory)
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path is invalid
        """
        resolved = self.validate_path(path, must_exist=must_exist)
        
        if must_be_file and resolved.exists() and not resolved.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        return resolved
    
    def validate_directory_path(
        self,
        path: str,
        must_exist: bool = False
    ) -> Path:
        """
        Validate a directory path.
        
        Args:
            path: Path to validate
            must_exist: Whether the directory must exist
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path is invalid
        """
        resolved = self.validate_path(path, must_exist=must_exist)
        
        if resolved.exists() and not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        return resolved
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to remove dangerous characters.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")
        
        # Remove null bytes
        filename = filename.replace("\x00", "")
        
        # Remove other dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in dangerous_chars:
            filename = filename.replace(char, "_")
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip(". ")
        
        # Ensure filename is not empty after sanitization
        if not filename:
            filename = "unnamed"
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[:250] + ("." + ext if ext else "")
        
        logger.debug(f"Filename sanitized: {filename}")
        return filename
    
    def is_safe_path(self, path: str) -> bool:
        """
        Check if a path is safe (within workspace).
        
        Args:
            path: Path to check
            
        Returns:
            True if safe, False otherwise
        """
        try:
            self.validate_path(path)
            return True
        except ValueError:
            return False
    
    def get_relative_path(self, path: str) -> Path:
        """
        Get path relative to workspace.
        
        Args:
            path: Absolute or relative path
            
        Returns:
            Path relative to workspace
        """
        resolved = self.validate_path(path)
        return resolved.relative_to(self.workspace_root)
    
    def resolve_project_path(self, project_name: str, file_path: str) -> Path:
        """
        Resolve a file path within a project.
        
        Args:
            project_name: Project name
            file_path: File path within project
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path is invalid
        """
        if not project_name or not project_name.strip():
            raise ValueError("Project name cannot be empty")
        
        # Sanitize project name
        safe_project = self.sanitize_filename(project_name)
        
        # Construct project path
        project_path = self.workspace_root / safe_project
        
        # Resolve file path within project
        resolved = (project_path / file_path).resolve()
        
        # Security check: ensure path is within workspace
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise ValueError(
                f"Path '{file_path}' in project '{project_name}' is outside the workspace"
            )
        
        logger.debug(f"Project path resolved: {project_name}/{file_path} -> {resolved}")
        return resolved


# Global path validator instance
path_validator = PathValidator()