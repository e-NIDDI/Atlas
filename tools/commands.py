"""Command execution tools for Jarvis."""

import subprocess
import shlex
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.config import config
from jarvis.logger import logger


class CommandManager:
    """Manages safe command execution."""
    
    # Whitelist of allowed commands
    ALLOWED_COMMANDS = {
        "git",
        "pytest",
        "python",
        "python3",
        "node",
        "npm",
        "ls",
        "dir",
        "cat",
        "echo",
        "find",
        "grep",
    }
    
    # Blacklisted commands (for extra safety)
    BLACKLISTED_COMMANDS = {
        "rm",
        "del",
        "shutdown",
        "reboot",
        "curl",
        "wget",
        "chmod",
        "chown",
        "sudo",
        "su",
        "eval",
        "exec",
        "system",
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
    }
    
    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """
        Initialize command manager.
        
        Args:
            workspace_root: Workspace root directory
        """
        self.workspace_root = workspace_root or config.workspace_root
        logger.info(f"Command manager initialized with workspace: {self.workspace_root}")
    
    def validate_command(self, command: str, args: List[str]) -> tuple[bool, Optional[str]]:
        """
        Validate a command is safe to execute.
        
        Args:
            command: Command name
            args: Command arguments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check blacklist first
        if command.lower() in self.BLACKLISTED_COMMANDS:
            error = f"Command '{command}' is not allowed for security reasons"
            logger.warning(error)
            return False, error
        
        # Check whitelist
        if command.lower() not in self.ALLOWED_COMMANDS:
            error = f"Command '{command}' is not in the allowed commands list"
            logger.warning(error)
            return False, error
        
        # Additional validation for specific commands
        if command.lower() == "git":
            # Only allow safe git commands
            if args and args[0].lower() in {"status", "log", "diff", "branch", "remote", "show"}:
                return True, None
            else:
                return False, f"Git command 'git {args[0] if args else ''}' is not allowed"
        
        logger.debug(f"Command validated: {command} {' '.join(args)}")
        return True, None
    
    def execute_command(
        self,
        command: str,
        args: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Execute a command safely.
        
        Args:
            command: Command to execute
            args: Command arguments
            cwd: Working directory
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with stdout, stderr, and return code
        """
        # Validate command
        is_valid, error_msg = self.validate_command(command, args)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Set working directory
        if cwd is None:
            cwd = self.workspace_root
        else:
            cwd = Path(cwd)
            if not cwd.is_absolute():
                cwd = self.workspace_root / cwd
        
        # Security check: ensure cwd is within workspace
        try:
            cwd.resolve().relative_to(self.workspace_root.resolve())
        except ValueError:
            raise ValueError(
                f"Working directory '{cwd}' is outside the workspace. "
                f"All commands must run within {self.workspace_root}"
            )
        
        # Build full command
        full_command = [command] + args
        
        logger.info(f"Executing command: {' '.join(full_command)} in {cwd}")
        
        try:
            result = subprocess.run(
                full_command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False  # Never use shell=True for security
            )
            
            logger.info(
                f"Command completed: return_code={result.returncode}, "
                f"stdout_len={len(result.stdout)}, stderr_len={len(result.stderr)}"
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            error = f"Command timed out after {timeout} seconds"
            logger.error(error)
            raise ValueError(error)
        except FileNotFoundError:
            error = f"Command not found: {command}"
            logger.error(error)
            raise ValueError(error)
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            raise ValueError(f"Failed to execute command: {e}")


# Global command manager instance
command_manager = CommandManager()


class GitStatusTool(BaseTool):
    """Tool for checking git status."""
    
    name = "git_status"
    description = "Check git status of a project"
    requires_confirmation = False
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        # project is optional
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            project_name = kwargs.get("project")
            
            # Determine working directory
            if project_name:
                cwd = config.workspace_root / project_name
            else:
                cwd = config.workspace_root
            
            # Check if it's a git repository
            git_dir = cwd / ".git"
            if not git_dir.exists():
                return ToolResult(
                    success=False,
                    message=f"Not a git repository: {cwd}",
                    error="Not a git repository"
                )
            
            # Execute git status
            result = command_manager.execute_command(
                command="git",
                args=["status", "--short"],
                cwd=cwd
            )
            
            if result["success"] or result["stdout"]:
                message = f"Git status for {cwd.name}:\n"
                if result["stdout"]:
                    message += result["stdout"]
                else:
                    message += "Working directory clean\n"
                
                return ToolResult(
                    success=True,
                    message=message,
                    data={
                        "stdout": result["stdout"],
                        "stderr": result["stderr"],
                        "return_code": result["return_code"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Git status failed: {result['stderr']}",
                    error=result["stderr"]
                )
                
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in git_status tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to get git status: {e}",
                error=str(e)
            )


class RunTestsTool(BaseTool):
    """Tool for running tests."""
    
    name = "run_tests"
    description = "Run tests in a project"
    requires_confirmation = True
    
    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate arguments."""
        # project is optional
        return True, None
    
    def get_required_args(self) -> List[str]:
        """Get required arguments."""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        try:
            project_name = kwargs.get("project")
            
            # Determine working directory
            if project_name:
                cwd = config.workspace_root / project_name
            else:
                cwd = config.workspace_root
            
            # Try to detect test framework and run tests
            # Check for pytest
            if (cwd / "pytest.ini").exists() or (cwd / "pyproject.toml").exists():
                result = command_manager.execute_command(
                    command="pytest",
                    args=["-v"],
                    cwd=cwd,
                    timeout=60
                )
            # Check for unittest
            elif (cwd / "test").exists() or (cwd / "tests").exists():
                result = command_manager.execute_command(
                    command="python",
                    args=["-m", "unittest", "discover", "-v"],
                    cwd=cwd,
                    timeout=60
                )
            else:
                return ToolResult(
                    success=False,
                    message="No test framework detected. Looking for pytest or unittest.",
                    error="No test framework found"
                )
            
            message = f"Test results for {cwd.name}:\n"
            if result["stdout"]:
                message += result["stdout"]
            if result["stderr"]:
                message += "\nErrors/Warnings:\n"
                message += result["stderr"]
            
            return ToolResult(
                success=result["success"],
                message=message,
                data={
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "return_code": result["return_code"]
                }
            )
            
        except ValueError as e:
            return ToolResult(
                success=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error in run_tests tool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Failed to run tests: {e}",
                error=str(e)
            )