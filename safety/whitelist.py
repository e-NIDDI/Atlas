"""Command and action whitelist validation for Jarvis."""

from pathlib import Path
from typing import Set, List, Tuple, Optional
from dataclasses import dataclass
from jarvis.logger import logger


@dataclass
class SafetyRule:
    """Safety rule definition."""
    name: str
    description: str
    allowed: bool
    reason: str


class SafetyWhitelist:
    """Manages safety whitelists and validation rules."""
    
    def __init__(self) -> None:
        """Initialize safety whitelist."""
        self._setup_whitelists()
        logger.info("Safety whitelist initialized")
    
    def _setup_whitelists(self) -> None:
        """Set up all whitelists and rules."""
        # Commands that are completely blocked
        self.blocked_commands: Set[str] = {
            # Destructive commands
            "rm", "rmdir", "del", "erase",
            "shutdown", "reboot", "halt", "poweroff",
            "format", "fdisk", "mkfs",
            "dd", "cat /dev/zero", "cat /dev/random",
            
            # Network commands that could be dangerous
            "curl", "wget", "nc", "netcat", "ncat",
            "ssh", "scp", "rsync", "sftp",
            "telnet", "ftp", "sftp",
            
            # Permission modification
            "chmod", "chown", "chgrp", "setfacl", "setfattr",
            "sudo", "su", "doas", "pkexec",
            
            # Process management
            "kill", "killall", "pkill", "xkill",
            "systemctl", "service", "init",
            
            # Code execution
            "eval", "exec", "call", "spawn",
            "python -c", "python3 -c",
            "perl -e", "ruby -e", "php -r",
            "node -e", "lua -e",
            
            # Shell features
            "source", ". ", "bash", "sh", "zsh", "fish",
            "cmd", "powershell", "pwsh",
            
            # Registry/system modification
            "reg", "regedit", "gpedit.msc",
            "msconfig", "sysedit",
            
            # Package managers (could install malicious software)
            "apt-get", "apt", "yum", "dnf", "pacman",
            "brew", "pip install", "npm install -g",
            "gem install", "cargo install",
        }
        
        # Commands that require extra scrutiny
        self.restricted_commands: Set[str] = {
            "git", "docker", "kubectl", "helm",
            "make", "cmake", "ninja",
            "gcc", "g++", "clang", "cl",
            "javac", "go", "rustc",
        }
        
        # Allowed commands (safe operations)
        self.allowed_commands: Set[str] = {
            # File viewing
            "ls", "dir", "cat", "less", "more", "head", "tail",
            "find", "which", "whereis", "locate",
            
            # Git (read-only operations)
            "git status", "git log", "git diff", "git branch",
            "git remote", "git show", "git blame", "git grep",
            
            # Development tools
            "pytest", "python -m pytest", "python3 -m pytest",
            "python -m unittest", "python3 -m unittest",
            "npm test", "npm run test", "yarn test",
            "make test", "cargo test", "go test",
            
            # Code quality
            "flake8", "pylint", "mypy", "black", "isort",
            "eslint", "prettier", "golint",
            
            # Build tools (read-only)
            "python -m build", "python setup.py --version",
            "npm run build", "yarn build",
            
            # System info (read-only)
            "whoami", "id", "pwd", "cd", "echo",
            "date", "time", "uname", "hostname",
            "env", "printenv", "set",
            
            # Text processing
            "grep", "egrep", "fgrep", "rg", "ag",
            "sed", "awk", "tr", "cut", "sort", "uniq",
            "wc", "diff", "patch",
            
            # Archive operations (read-only)
            "tar -t", "zipinfo", "unzip -l",
        }
        
        # File extensions that are safe to read
        self.safe_extensions: Set[str] = {
            ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".c", ".cpp", ".h", ".hpp", ".cs",
            ".go", ".rs", ".rb", ".php", ".swift", ".kt",
            ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg",
            ".html", ".css", ".scss", ".sass", ".less",
            ".sql", ".sh", ".bash", ".zsh", ".fish",
            ".dockerfile", ".makefile", ".gitignore", ".gitattributes",
            ".license", ".readme", ".changelog", ".todo",
            ".csv", ".tsv", ".log", ".env", ".example",
        }
        
        # File extensions that are potentially dangerous
        self.dangerous_extensions: Set[str] = {
            ".exe", ".dll", ".so", ".dylib", ".bin",
            ".bat", ".cmd", ".ps1", ".vbs", ".js",
            ".jar", ".war", ".ear", ".pyc", ".pyo",
            ".deb", ".rpm", ".pkg", ".msi", ".dmg",
        }
        
        # Actions that require user confirmation
        self.actions_requiring_confirmation: Set[str] = {
            "create_project",
            "rename_project",
            "delete_project",
            "write_file",
            "create_file",
            "delete_file",
            "run_tests",
            "execute_command",
            "git_push",
            "git_commit",
            "git_merge",
            "git_rebase",
            "git_reset",
            "git_checkout",
        }
    
    def is_command_blocked(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a command is blocked.
        
        Args:
            command: Command to check
            
        Returns:
            Tuple of (is_blocked, reason)
        """
        command_lower = command.lower().strip()
        
        # Check blocked commands
        for blocked in self.blocked_commands:
            if command_lower == blocked or command_lower.startswith(blocked + " "):
                reason = f"Command '{command}' is blocked for security reasons"
                logger.warning(f"Blocked command attempt: {command}")
                return True, reason
        
        return False, None
    
    def is_command_restricted(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a command is restricted (requires extra validation).
        
        Args:
            command: Command to check
            
        Returns:
            Tuple of (is_restricted, reason)
        """
        command_lower = command.lower().strip()
        
        for restricted in self.restricted_commands:
            if command_lower == restricted or command_lower.startswith(restricted + " "):
                reason = f"Command '{command}' requires additional validation"
                logger.info(f"Restricted command: {command}")
                return True, reason
        
        return False, None
    
    def is_command_allowed(self, command: str) -> bool:
        """
        Check if a command is explicitly allowed.
        
        Args:
            command: Command to check
            
        Returns:
            True if allowed, False otherwise
        """
        command_lower = command.lower().strip()
        
        for allowed in self.allowed_commands:
            if command_lower == allowed or command_lower.startswith(allowed + " "):
                return True
        
        return False
    
    def validate_command(self, command: str, args: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate a command is safe to execute.
        
        Args:
            command: Command name
            args: Command arguments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Build full command string for checking
        full_command = command + " " + " ".join(args) if args else command
        full_command_lower = full_command.lower().strip()
        
        # Check if blocked
        is_blocked, block_reason = self.is_command_blocked(full_command_lower)
        if is_blocked:
            return False, block_reason
        
        # Check if allowed or restricted
        is_allowed = self.is_command_allowed(full_command_lower)
        is_restricted, restrict_reason = self.is_command_restricted(full_command_lower)
        
        if is_allowed:
            logger.debug(f"Command allowed: {full_command}")
            return True, None
        
        if is_restricted:
            # Restricted commands need additional validation
            logger.info(f"Command requires validation: {full_command}")
            # For now, we'll allow restricted commands but log them
            # In production, you might want to require extra confirmation
            return True, None
        
        # Unknown command - block by default
        error = f"Command '{command}' is not in the allowed commands list"
        logger.warning(f"Unknown command blocked: {command}")
        return False, error
    
    def is_extension_safe(self, filename: str) -> bool:
        """
        Check if a file extension is safe.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if safe, False if dangerous
        """
        path = Path(filename)
        extension = path.suffix.lower()
        
        if extension in self.dangerous_extensions:
            logger.warning(f"Dangerous file extension detected: {extension}")
            return False
        
        return True
    
    def requires_confirmation(self, action: str) -> bool:
        """
        Check if an action requires user confirmation.
        
        Args:
            action: Action name
            
        Returns:
            True if confirmation required, False otherwise
        """
        return action in self.actions_requiring_confirmation
    
    def get_safety_rules(self) -> List[SafetyRule]:
        """
        Get all safety rules.
        
        Returns:
            List of SafetyRule objects
        """
        rules = []
        
        # Blocked commands
        for cmd in sorted(self.blocked_commands):
            rules.append(SafetyRule(
                name=f"block_{cmd}",
                description=f"Block command: {cmd}",
                allowed=False,
                reason="Security risk"
            ))
        
        # Allowed commands
        for cmd in sorted(self.allowed_commands):
            rules.append(SafetyRule(
                name=f"allow_{cmd}",
                description=f"Allow command: {cmd}",
                allowed=True,
                reason="Safe operation"
            ))
        
        # Actions requiring confirmation
        for action in sorted(self.actions_requiring_confirmation):
            rules.append(SafetyRule(
                name=f"confirm_{action}",
                description=f"Require confirmation for: {action}",
                allowed=True,
                reason="Requires user approval"
            ))
        
        return rules
    
    def validate_file_operation(
        self,
        operation: str,
        path: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a file operation is safe.
        
        Args:
            operation: Operation type (read, write, delete, etc.)
            path: File path
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for dangerous extensions in write operations
        if operation in ["write", "create", "delete"]:
            path_obj = Path(path)
            if path_obj.suffix.lower() in self.dangerous_extensions:
                return False, f"Cannot {operation} file with dangerous extension: {path_obj.suffix}"
        
        logger.debug(f"File operation validated: {operation} {path}")
        return True, None


# Global safety whitelist instance
safety_whitelist = SafetyWhitelist()
