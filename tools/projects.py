"""Project management tools for Jarvis."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.config import config
from jarvis.logger import logger


@dataclass
class Project:
    """Project data structure."""
    id: Optional[int]
    name: str
    path: Path
    created_at: datetime
    description: Optional[str] = None


class ProjectManager:
    """Manages projects in the workspace."""
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize project manager.
        
        Args:
            workspace_root: Workspace root directory
        """
        self.workspace_root = workspace_root or config.workspace_root
        self.projects: Dict[str, Project] = {}
        logger.info(f"Project manager initialized with workspace: {self.workspace_root}")
    
    def create_project(self, name: str, description: Optional[str] = None) -> Project:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Optional project description
            
        Returns:
            Created Project object
            
        Raises:
            ValueError: If project already exists or name is invalid
        """
        # Validate project name
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty")
        
        # Sanitize project name
        safe_name = self._sanitize_name(name)
        
        # Check if project already exists
        if safe_name in self.projects:
            raise ValueError(f"Project '{safe_name}' already exists")
        
        # Create project path
        project_path = self.workspace_root / safe_name
        
        # Check if directory already exists
        if project_path.exists():
            raise ValueError(f"Project directory already exists: {project_path}")
        
        # Create project directory
        try:
            project_path.mkdir(parents=True, exist_ok=False)
            logger.info(f"Created project directory: {project_path}")
        except OSError as e:
            raise ValueError(f"Failed to create project directory: {e}")
        
        # Create project object
        project = Project(
            id=None,
            name=safe_name,
            path=project_path,
            created_at=datetime.now(),
            description=description
        )
        
        # Add to projects dict
        self.projects[safe_name] = project
        
        logger.info(f"Project created: {safe_name}")
        return project
    
    def list_projects(self) -> List[Project]:
        """
        List all projects.
        
        Returns:
            List of Project objects
        """
        return list(self.projects.values())
    
    def get_project(self, name: str) -> Optional[Project]:
        """
        Get a project by name.
        
        Args:
            name: Project name
            
        Returns:
            Project object or None if not found
        """
        return self.projects.get(name)
    
    def rename_project(self, old_name: str, new_name: str) -> Project:
        """
        Rename a project.
        
        Args:
            old_name: Current project name
            new_name: New project name
            
        Returns:
            Updated Project object
            
        Raises:
            ValueError: If project doesn't exist or new name is invalid
        """
        # Check if old project exists
        if old_name not in self.projects:
            raise ValueError(f"Project '{old_name}' not found")
        
        # Validate new name
        if not new_name or not new_name.strip():
            raise ValueError("New project name cannot be empty")
        
        safe_new_name = self._sanitize_name(new_name)
        
        # Check if new name already exists
        if safe_new_name in self.projects:
            raise ValueError(f"Project '{safe_new_name}' already exists")
        
        # Get old project
        project = self.projects[old_name]
        
        # Rename directory
        old_path = project.path
        new_path = self.workspace_root / safe_new_name
        
        try:
            old_path.rename(new_path)
            logger.info(f"Renamed project directory: {old_path} -> {new_path}")
        except OSError as e:
            raise ValueError(f"Failed to rename project directory: {e}")
        
        # Update project object
        project.name = safe_new_name
        project.path = new_path
        
        # Update projects dict
        del self.projects[old_name]
        self.projects[safe_new_name] = project
        
        logger.info(f"Project renamed: {old_name} -> {safe_new_name}")
        return project
    
    def delete_project(self, name: str) -> bool:
        """
        Delete a project.
        
        Args:
            name: Project name
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If project doesn't exist
        """
        if name not in self.projects:
            raise ValueError(f"Project '{name}' not found")
        
        project = self.projects[name]
        
        # Delete directory
        try:
            import shutil
            shutil.rmtree(project.path)
            logger.info(f"Deleted project directory: {project.path}")
        except OSError as e:
            raise ValueError(f"Failed to delete project directory: {e}")
        
        # Remove from dict
        del self.projects[name]
        
        logger.info(f"Project deleted: {name}")
        return True
    
    def load_projects(self) -> None:
        """Load existing projects from workspace directory."""
        if not self.workspace_root.exists():
            logger.warning(f"Workspace directory does not exist: {self.workspace_root}")
            return
        
        self.projects.clear()
        
        try:
            for item in self.workspace_root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it's a valid project (has some content or is a git repo)
                    project = Project(
                        id=None,
                        name=item.name,
                        path=item,
                        created_at=datetime.fromtimestamp(item.stat().st_ctime)
                    )
                    self.projects[item.name] = project
            
            logger.info(f"Loaded {len(self.projects)} projects from workspace")
        except Exception as e:
            logger.error(f"Error loading projects: {e}")
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize project name.
        
        Args:
            name: Raw project name
            
        Returns:
            Sanitized project name
        """
        # Remove leading/trailing whitespace
        name = name.strip()
        
        # Replace spaces with hyphens
        name = name.replace(' ', '-')
        
        # Remove invalid characters (keep alphanumeric, hyphens, underscores)
        import re
        name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
        
        # Ensure it's not empty
        if not name:
            name = "unnamed-project"
        
        return name


# Global project manager instance
project_manager = ProjectManager()


class CreateProjectTool(BaseTool):
    """Tool for creating a new project."""
    
    name = "create_project"
    description = "Create a new project in the workspace"
    requires_confirmation = True
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "name" not in kwargs:
            return False, "Missing required argument: name"
        
        if not kwargs["name"] or not str(kwargs["name"]).strip():
            return False, "Project name cannot be empty"
        
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["name"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            name = kwargs["name"]
            description = kwargs.get("description")
            
            project = project_manager.create_project(name, description)
            
            return ToolResult(
                success=True,
                message=f"Project '{project.name}' created successfully at {project.path}",
                data={
                    "name": project.name,
                    "path": str(project.path),
                    "created_at": project.created_at.isoformat()
                }
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error creating project: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to create project: {e}",
                error=str(e)
            )


class ListProjectsTool(BaseTool):
    """Tool for listing all projects."""
    
    name = "list_projects"
    description = "List all projects in the workspace"
    requires_confirmation = False
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            # Reload projects to get latest
            project_manager.load_projects()
            
            projects = project_manager.list_projects()
            
            if not projects:
                return ToolResult(
                    success=True,
                    message="No projects found. Create your first project to get started!",
                    data=[]
                )
            
            project_list = []
            for project in projects:
                project_list.append({
                    "name": project.name,
                    "path": str(project.path),
                    "created_at": project.created_at.isoformat(),
                    "description": project.description
                })
            
            message = f"Found {len(projects)} project(s):\n"
            for i, project in enumerate(projects, 1):
                message += f"{i}. {project.name} - {project.path}\n"
            
            return ToolResult(
                success=True,
                message=message,
                data=project_list
            )
        except Exception as e:
            logger.error(f"Error listing projects: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to list projects: {e}",
                error=str(e)
            )


class RenameProjectTool(BaseTool):
    """Tool for renaming a project."""
    
    name = "rename_project"
    description = "Rename an existing project"
    requires_confirmation = True
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        if "old_name" not in kwargs:
            return False, "Missing required argument: old_name"
        
        if "new_name" not in kwargs:
            return False, "Missing required argument: new_name"
        
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return ["old_name", "new_name"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            old_name = kwargs["old_name"]
            new_name = kwargs["new_name"]
            
            project = project_manager.rename_project(old_name, new_name)
            
            return ToolResult(
                success=True,
                message=f"Project renamed from '{old_name}' to '{project.name}'",
                data={
                    "old_name": old_name,
                    "new_name": project.name,
                    "path": str(project.path)
                }
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error renaming project: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to rename project: {e}",
                error=str(e)
            )