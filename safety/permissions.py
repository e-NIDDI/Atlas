"""Permission system for Jarvis.

Provides user-defined safe directories, file type rules,
and operation-level permissions.
"""

from pathlib import Path
from typing import Set, List, Optional, Dict, Any
from dataclasses import dataclass, field

from jarvis.config import config
from jarvis.logger import logger


@dataclass
class PermissionRule:
    """A single permission rule."""
    path: str
    allow_read: bool = True
    allow_write: bool = False
    allow_delete: bool = False
    allow_execute: bool = False
    recursive: bool = True


class PermissionManager:
    """Manages user-defined permissions for file operations."""

    def __init__(self) -> None:
        self.rules: List[PermissionRule] = []
        self._setup_defaults()
        logger.info("Permission manager initialized")

    def _setup_defaults(self) -> None:
        """Set up default permission rules."""
        ws = str(config.workspace_root)

        # Workspace root: full access
        self.rules.append(PermissionRule(
            path=ws,
            allow_read=True,
            allow_write=True,
            allow_delete=True,
            allow_execute=True,
            recursive=True,
        ))

        # Home directory: read-only by default
        self.rules.append(PermissionRule(
            path=str(Path.home()),
            allow_read=True,
            allow_write=False,
            allow_delete=False,
            allow_execute=False,
            recursive=True,
        ))

        # User-defined safe directories
        for safe_dir in config.safe_directories:
            safe_dir = safe_dir.strip()
            if safe_dir:
                self.rules.append(PermissionRule(
                    path=safe_dir,
                    allow_read=True,
                    allow_write=True,
                    allow_delete=True,
                    allow_execute=True,
                    recursive=True,
                ))

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a custom permission rule."""
        self.rules.append(rule)
        logger.info(f"Permission rule added: {rule.path}")

    def check_operation(
        self,
        path: str,
        operation: str,  # "read", "write", "delete", "execute"
    ) -> bool:
        """Check if an operation is allowed on a path."""
        path_obj = Path(path).resolve()

        # Check rules in order (most specific first)
        for rule in reversed(self.rules):
            rule_path = Path(rule.path).resolve()

            if rule.recursive:
                try:
                    path_obj.relative_to(rule_path)
                except ValueError:
                    continue
            else:
                if path_obj.parent != rule_path and path_obj != rule_path:
                    continue

            # Found matching rule
            if operation == "read":
                return rule.allow_read
            elif operation == "write":
                return rule.allow_write
            elif operation == "delete":
                return rule.allow_delete
            elif operation == "execute":
                return rule.allow_execute

        # Default: deny
        return False

    def get_allowed_operations(self, path: str) -> Dict[str, bool]:
        """Get all allowed operations for a path."""
        return {
            "read": self.check_operation(path, "read"),
            "write": self.check_operation(path, "write"),
            "delete": self.check_operation(path, "delete"),
            "execute": self.check_operation(path, "execute"),
        }


# Global instance
permission_manager = PermissionManager()