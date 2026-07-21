"""Safety validation for Jarvis tools and actions."""

from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from jarvis.safety.paths import PathValidator
from jarvis.safety.whitelist import SafetyWhitelist
from jarvis.tools.registry import tool_registry
from jarvis.logger import logger


@dataclass
class ValidationResult:
    """Result of safety validation."""
    is_valid: bool
    error_message: Optional[str] = None
    requires_confirmation: bool = False
    warnings: list[str] = None
    
    def __post_init__(self) -> None:
        """Initialize warnings list if None."""
        if self.warnings is None:
            self.warnings = []


class SafetyValidator:
    """Validates tool requests and actions for safety."""
    
    def __init__(
        self,
        path_validator: Optional[PathValidator] = None,
        whitelist: Optional[SafetyWhitelist] = None
    ) -> None:
        """
        Initialize safety validator.
        
        Args:
            path_validator: Path validator instance
            whitelist: Safety whitelist instance
        """
        self.path_validator = path_validator or PathValidator()
        self.whitelist = whitelist or SafetyWhitelist()
        logger.info("Safety validator initialized")
    
    def validate_tool_request(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a tool request.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            
        Returns:
            ValidationResult object
        """
        logger.debug(f"Validating tool request: {tool_name}")
        
        # Check if tool exists in the registry
        tool = tool_registry.get_tool(tool_name)
        if tool is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unknown tool: {tool_name}",
                requires_confirmation=False
            )
        
        # Check if tool requires confirmation
        requires_confirmation = self.whitelist.requires_confirmation(tool_name)
        
        # Validate based on tool type
        if tool_name in ["create_project", "rename_project"]:
            return self._validate_project_tool(tool_name, args, requires_confirmation)

        elif tool_name == "list_projects":
            return ValidationResult(is_valid=True, requires_confirmation=requires_confirmation)
        
        elif tool_name in ["read_file", "write_file", "append_file", "delete_file",
                           "create_folder", "delete_folder", "rename_item", "move_item",
                           "copy_item", "list_directory", "search_files", "search_content",
                           "get_file_metadata"]:
            return self._validate_file_tool(tool_name, args, requires_confirmation)
        
        elif tool_name in ["read_document", "summarize_document", "locate_in_document"]:
            return self._validate_document_tool(tool_name, args, requires_confirmation)
        
        elif tool_name in ["create_note", "search_notes", "list_notes",
                           "create_task", "list_tasks", "complete_task",
                           "remember_project_context", "get_project_context",
                           "search_memory"]:
            return self._validate_secretary_tool(tool_name, args, requires_confirmation)
        
        elif tool_name == "git_status":
            return self._validate_git_tool(tool_name, args, requires_confirmation)
        
        elif tool_name == "run_tests":
            return self._validate_test_tool(tool_name, args, requires_confirmation)
        
        # ── NEW: Code Execution tools ──────────────
        elif tool_name in ["execute_file", "execute_code"]:
            return self._validate_execution_tool(tool_name, args, requires_confirmation)
        
        # ── NEW: Code Analysis tools ────────────────
        elif tool_name in ["lint_code", "format_code", "typecheck_code", "count_lines"]:
            return self._validate_analysis_tool(tool_name, args, requires_confirmation)
        
        # ── NEW: Refactoring tools ──────────────────
        elif tool_name in ["search_replace", "edit_lines", "rename_symbol"]:
            return self._validate_refactor_tool(tool_name, args, requires_confirmation)
        
        # ── NEW: Scaffolding tools ──────────────────
        elif tool_name in ["scaffold_project", "list_templates"]:
            return self._validate_scaffold_tool(tool_name, args, requires_confirmation)
        
        else:
            # Fallback: allow the tool with basic validation
            return ValidationResult(
                is_valid=True,
                requires_confirmation=requires_confirmation
            )
    
    def _validate_project_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """
        Validate project-related tools.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            requires_confirmation: Whether confirmation is required
            
        Returns:
            ValidationResult object
        """
        warnings = []
        
        if tool_name == "create_project":
            if "name" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'name' for create_project (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
            
            name = args["name"]
            if not name or not str(name).strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Project name cannot be empty",
                    requires_confirmation=requires_confirmation
                )

            parent = args.get("parent")
            if parent:
                try:
                    parent_path = self.path_validator.validate_path(str(parent), must_exist=False)
                    if parent_path.exists() and not parent_path.is_dir():
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Parent path is not a directory: {parent}",
                            requires_confirmation=requires_confirmation,
                        )
                except ValueError as e:
                    return ValidationResult(
                        is_valid=False,
                        error_message=str(e),
                        requires_confirmation=requires_confirmation,
                    )
            
            try:
                safe_name = self.path_validator.sanitize_filename(str(name))
                if safe_name != str(name).strip():
                    warnings.append(f"Project name sanitized: '{name}' -> '{safe_name}'")
            except ValueError as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid project name: {e}",
                    requires_confirmation=requires_confirmation
                )
        
        elif tool_name == "rename_project":
            if "old_name" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'old_name' for rename_project (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
            
            if "new_name" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'new_name' for rename_project (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        logger.debug(f"Project tool validated: {tool_name}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation,
            warnings=warnings
        )
    
    def _validate_file_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """
        Validate file-related tools.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            requires_confirmation: Whether confirmation is required
            
        Returns:
            ValidationResult object
        """
        warnings = []
        
        # Tools that require a "path" argument
        path_required_tools = [
            "read_file", "write_file", "append_file", "delete_file",
            "create_folder", "delete_folder", "get_file_metadata",
        ]
        if tool_name in path_required_tools and "path" not in args:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required argument 'path' for {tool_name} (received args: {args})",
                requires_confirmation=requires_confirmation
            )
        
        # Tools that require "content"
        if tool_name in ["write_file", "append_file"] and "content" not in args:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required argument 'content' for {tool_name} (received args: {args})",
                requires_confirmation=requires_confirmation
            )
        
        # rename/move/copy require two path args
        if tool_name == "rename_item":
            for arg in ["old_path", "new_path"]:
                if arg not in args:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing required argument '{arg}' for {tool_name} (received args: {args})",
                        requires_confirmation=requires_confirmation
                    )
        
        if tool_name in ["move_item", "copy_item"]:
            for arg in ["source", "destination"]:
                if arg not in args:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing required argument '{arg}' for {tool_name} (received args: {args})",
                        requires_confirmation=requires_confirmation
                    )
        
        if tool_name == "search_files" and "pattern" not in args:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required argument 'pattern' for {tool_name} (received args: {args})",
                requires_confirmation=requires_confirmation
            )

        if tool_name == "search_content" and "query" not in args:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required argument 'query' for {tool_name} (received args: {args})",
                requires_confirmation=requires_confirmation
            )
        
        # Validate paths
        path = args.get("path") or args.get("old_path") or args.get("source")
        if path:
            # Check if path is safe
            if not self.path_validator.is_safe_path(path):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Path is outside workspace: {path}",
                    requires_confirmation=requires_confirmation
                )
            
            # Check file extension for write operations
            if tool_name in ["write_file", "create_file"]:
                is_safe = self.whitelist.is_extension_safe(path)
                if not is_safe:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Cannot write to file with dangerous extension: {path}",
                        requires_confirmation=requires_confirmation
                    )
        
        logger.debug(f"File tool validated: {tool_name}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation,
            warnings=warnings
        )
    
    def _validate_git_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """
        Validate git-related tools.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            requires_confirmation: Whether confirmation is required
            
        Returns:
            ValidationResult object
        """
        # Git tools are generally safe (read-only operations)
        logger.debug(f"Git tool validated: {tool_name}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation
        )
    
    def _validate_test_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """
        Validate test-related tools.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            requires_confirmation: Whether confirmation is required
            
        Returns:
            ValidationResult object
        """
        # Test tools are generally safe
        logger.debug(f"Test tool validated: {tool_name}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation
        )
    
    def _validate_document_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """
        Validate document-related tools.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            requires_confirmation: Whether confirmation is required
            
        Returns:
            ValidationResult object
        """
        # Check required arguments
        if tool_name in ["read_document", "summarize_document"]:
            if "path" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'path' for {tool_name} (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        if tool_name == "locate_in_document":
            if "path" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'path' for locate_in_document (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
            if "query" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'query' for locate_in_document (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        logger.debug(f"Document tool validated: {tool_name}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation
        )
    
    def _validate_secretary_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """
        Validate secretary-related tools.
        
        Args:
            tool_name: Tool name
            args: Tool arguments
            requires_confirmation: Whether confirmation is required
            
        Returns:
            ValidationResult object
        """
        # Check required arguments
        if tool_name == "create_note":
            if "title" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'title' for create_note (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        if tool_name == "create_task":
            if "title" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'title' for create_task (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        if tool_name == "complete_task":
            if "task_id" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'task_id' for complete_task (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        if tool_name == "remember_project_context":
            for arg in ["project", "key", "value"]:
                if arg not in args:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing required argument '{arg}' for remember_project_context (received args: {args})",
                        requires_confirmation=requires_confirmation
                    )
        
        if tool_name == "get_project_context":
            if "project" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'project' for get_project_context (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        if tool_name == "search_memory":
            if "query" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'query' for search_memory (received args: {args})",
                    requires_confirmation=requires_confirmation
                )
        
        logger.debug(f"Secretary tool validated: {tool_name}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation
        )
    
    def _validate_execution_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """Validate code execution tools."""
        if tool_name == "execute_file":
            if "path" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'path' for execute_file (received args: {args})",
                    requires_confirmation=requires_confirmation,
                )
            # Validate the file path
            path = args["path"]
            if not self.path_validator.is_safe_path(str(path)):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File path is outside workspace: {path}",
                    requires_confirmation=requires_confirmation,
                )

        if tool_name == "execute_code":
            if "code" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'code' for execute_code",
                    requires_confirmation=requires_confirmation,
                )
            if "language" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'language' for execute_code",
                    requires_confirmation=requires_confirmation,
                )
            # Limit code snippet size
            code = args["code"]
            if isinstance(code, str) and len(code) > 50000:
                return ValidationResult(
                    is_valid=False,
                    error_message="Code snippet too large (max 50KB)",
                    requires_confirmation=requires_confirmation,
                )

        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation,
        )

    def _validate_analysis_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """Validate code analysis tools."""
        if tool_name in ("lint_code", "format_code", "typecheck_code", "count_lines"):
            if "path" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required argument 'path' for {tool_name}",
                    requires_confirmation=requires_confirmation,
                )
            path = args["path"]
            if not self.path_validator.is_safe_path(str(path)):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Path is outside workspace: {path}",
                    requires_confirmation=requires_confirmation,
                )

        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation,
        )

    def _validate_refactor_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """Validate refactoring tools."""
        if tool_name == "search_replace":
            if "pattern" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'pattern' for search_replace",
                    requires_confirmation=requires_confirmation,
                )
            if "replacement" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'replacement' for search_replace",
                    requires_confirmation=requires_confirmation,
                )

            path = args.get("path", ".")
            if not self.path_validator.is_safe_path(str(path)):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Path is outside workspace: {path}",
                    requires_confirmation=requires_confirmation,
                )

        if tool_name == "edit_lines":
            if "path" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'path' for edit_lines",
                    requires_confirmation=requires_confirmation,
                )
            if "edits" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'edits' for edit_lines",
                    requires_confirmation=requires_confirmation,
                )

        if tool_name == "rename_symbol":
            if "old_name" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'old_name' for rename_symbol",
                    requires_confirmation=requires_confirmation,
                )
            if "new_name" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'new_name' for rename_symbol",
                    requires_confirmation=requires_confirmation,
                )

        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation,
        )

    def _validate_scaffold_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        requires_confirmation: bool
    ) -> ValidationResult:
        """Validate scaffolding tools."""
        if tool_name == "scaffold_project":
            if "name" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'name' for scaffold_project",
                    requires_confirmation=requires_confirmation,
                )
            if "template" not in args:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required argument 'template' for scaffold_project",
                    requires_confirmation=requires_confirmation,
                )

        return ValidationResult(
            is_valid=True,
            requires_confirmation=requires_confirmation,
        )

    def validate_command(
        self,
        command: str,
        args: list[str]
    ) -> ValidationResult:
        """
        Validate a command execution.
        
        Args:
            command: Command name
            args: Command arguments
            
        Returns:
            ValidationResult object
        """
        logger.debug(f"Validating command: {command} {' '.join(args)}")
        
        # Check if command is blocked
        is_blocked, block_reason = self.whitelist.is_command_blocked(command)
        if is_blocked:
            return ValidationResult(
                is_valid=False,
                error_message=block_reason,
                requires_confirmation=True
            )
        
        # Check if command is allowed
        is_valid, error_msg = self.whitelist.validate_command(command, args)
        
        if not is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                requires_confirmation=True
            )
        
        # Check if command is restricted
        is_restricted, _ = self.whitelist.is_command_restricted(command)
        
        logger.debug(f"Command validated: {command}")
        return ValidationResult(
            is_valid=True,
            requires_confirmation=is_restricted or self.whitelist.requires_confirmation("execute_command")
        )
    
    def validate_path(self, path: str, must_exist: bool = False) -> ValidationResult:
        """
        Validate a file path.
        
        Args:
            path: Path to validate
            must_exist: Whether the path must exist
            
        Returns:
            ValidationResult object
        """
        try:
            self.path_validator.validate_path(path, must_exist=must_exist)
            return ValidationResult(is_valid=True)
        except ValueError as e:
            return ValidationResult(
                is_valid=False,
                error_message=str(e)
            )
    
    def get_validation_summary(self, result: ValidationResult) -> str:
        """
        Get a human-readable summary of validation result.
        
        Args:
            result: ValidationResult object
            
        Returns:
            Summary string
        """
        if result.is_valid:
            parts = ["✓ Validation passed"]
            
            if result.requires_confirmation:
                parts.append("(requires confirmation)")
            
            if result.warnings:
                parts.append(f"\nWarnings: {'; '.join(result.warnings)}")
            
            return " ".join(parts)
        else:
            return f"✗ Validation failed: {result.error_message}"


# Global safety validator instance
safety_validator = SafetyValidator()