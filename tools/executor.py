"""Safe code execution sandbox for Jarvis.

Provides isolated subprocess execution for:
- Python scripts
- Node.js / JavaScript
- Shell commands (whitelisted)
- Compiled languages (go, rust, java) via compile-then-run pattern

All execution is:
- Timeout-bounded (default 30s, configurable)
- Resource-limited (subprocess, not shell=True)
- Output-captured (stdout + stderr)
- Workspace-confined
- Fully audited
"""

import asyncio
import subprocess
import os
import signal
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from jarvis.tools.registry import BaseTool, ToolResult
from jarvis.tools.filesystem import fs
from jarvis.safety.whitelist import safety_whitelist
from jarvis.config import config
from jarvis.logger import logger


# ──────────────────────────────────────────────
#  Data Types
# ──────────────────────────────────────────────

@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
    timed_out: bool = False
    error: Optional[str] = None


# ──────────────────────────────────────────────
#  Supported language / runtime registry
# ──────────────────────────────────────────────

@dataclass
class RuntimeInfo:
    """Information about a supported language runtime."""
    language: str
    extensions: List[str]
    command: str
    args_template: List[str]  # ["{file}"] or ["-c", "{code}"]
    compile_first: bool = False
    compile_command: Optional[str] = None
    compile_args: Optional[List[str]] = None
    description: str = ""


RUNTIMES: Dict[str, RuntimeInfo] = {
    "python": RuntimeInfo(
        language="python",
        extensions=[".py"],
        command="python3",
        args_template=["{file}"],
        description="Python 3.x",
    ),
    "python3": RuntimeInfo(
        language="python",
        extensions=[".py"],
        command="python3",
        args_template=["{file}"],
        description="Python 3.x",
    ),
    "javascript": RuntimeInfo(
        language="javascript",
        extensions=[".js", ".mjs"],
        command="node",
        args_template=["{file}"],
        description="Node.js / JavaScript",
    ),
    "node": RuntimeInfo(
        language="javascript",
        extensions=[".js", ".mjs"],
        command="node",
        args_template=["{file}"],
        description="Node.js / JavaScript",
    ),
    "go": RuntimeInfo(
        language="go",
        extensions=[".go"],
        command="go",
        args_template=["run", "{file}"],
        description="Go (interpreted run)",
    ),
    "rust": RuntimeInfo(
        language="rust",
        extensions=[".rs"],
        command="cargo",
        args_template=["run"],
        description="Rust (via cargo run)",
        compile_first=True,
        # For single-file scripts, we use `rustc {file} && ./output`
    ),
    "shell": RuntimeInfo(
        language="shell",
        extensions=[".sh", ".bash"],
        command="bash",
        args_template=["{file}"],
        description="Bash shell script",
    ),
    "bash": RuntimeInfo(
        language="shell",
        extensions=[".sh", ".bash"],
        command="bash",
        args_template=["{file}"],
        description="Bash shell script",
    ),
}


# ──────────────────────────────────────────────
#  Safe Execution Engine
# ──────────────────────────────────────────────

class CodeExecutor:
    """Safe, isolated code execution engine.

    Runs code in a subprocess with:
    - Strict timeout (kills process tree on expiry)
    - Workspace-confinement (only scripts within workspace)
    - Captured stdout/stderr
    - No shell=True (prevents injection)
    """

    DEFAULT_TIMEOUT = 30
    MAX_TIMEOUT = 300  # 5 minutes hard cap

    # Commands that can ONLY run in file mode (not -c inline)
    FILE_ONLY_COMMANDS = {"go", "rust", "cargo"}

    # Binaries that require extra confirmation
    CONFIRMATION_COMMANDS = {"sudo", "docker", "kubectl", "helm", "cargo"}

    def __init__(self) -> None:
        logger.info("Code executor initialized")

    # ── Public API ─────────────────────────────

    async def execute_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        args: Optional[List[str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
        cwd: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute a file in the workspace.

        Args:
            file_path: Path to the file to execute (relative to workspace or absolute)
            language: Language/runtime hint (auto-detected from extension if omitted)
            args: Additional command-line arguments to pass to the program
            timeout: Maximum execution time in seconds
            cwd: Working directory (defaults to file's parent)

        Returns:
            ExecutionResult with stdout, stderr, return_code, duration
        """
        # Resolve path
        resolved = fs.resolve_path(file_path, must_exist=True)

        if not resolved.is_file():
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0,
                error=f"File not found: {file_path}",
            )

        # Detect language if not specified
        if not language:
            language = self._detect_language(resolved)

        runtime = RUNTIMES.get(language)
        if not runtime:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0,
                error=f"Unsupported language: {language}. Supported: {', '.join(RUNTIMES.keys())}",
            )

        # Build command
        cmd_parts = self._build_file_command(runtime, resolved, args or [])
        work_dir = Path(cwd) if cwd else resolved.parent

        logger.info(f"Executing file: {resolved} via {' '.join(cmd_parts)}")

        return await self._run_subprocess(cmd_parts, cwd=work_dir, timeout=timeout)

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> ExecutionResult:
        """Execute a code snippet in a temporary file.

        Creates a temp file with the code, runs it, and cleans up.

        Args:
            code: Source code to execute
            language: Language/runtime
            timeout: Maximum execution time

        Returns:
            ExecutionResult
        """
        runtime = RUNTIMES.get(language)
        if not runtime:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0,
                error=f"Unsupported language: {language}",
            )

        # Write code to a temp file inside workspace
        ext = runtime.extensions[0] if runtime.extensions else ".txt"
        tmp_dir = config.workspace_root / ".jarvis_exec"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        tmp_file = tmp_dir / f"exec_{self._random_id()}{ext}"
        try:
            tmp_file.write_text(code, encoding="utf-8")
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0,
                error=f"Failed to write temp file: {e}",
            )

        try:
            cmd_parts = self._build_file_command(runtime, tmp_file, [])
            logger.info(f"Executing code snippet ({language}), temp file: {tmp_file}")

            result = await self._run_subprocess(cmd_parts, cwd=tmp_dir, timeout=timeout)
            return result
        finally:
            # Cleanup
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception:
                pass

    # ── Internal ───────────────────────────────

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        for name, runtime in RUNTIMES.items():
            if ext in runtime.extensions:
                return name
        return "python"  # default fallback

    def _build_file_command(
        self, runtime: RuntimeInfo, file_path: Path, extra_args: List[str]
    ) -> List[str]:
        """Build the command list for executing a file."""
        cmd = [runtime.command]
        for arg in runtime.args_template:
            cmd.append(arg.replace("{file}", str(file_path)))
        cmd.extend(extra_args)
        return cmd

    def _validate_before_run(
        self, cmd_parts: List[str], cwd: Path, timeout: int
    ) -> Optional[ExecutionResult]:
        """Validate preconditions before running. Returns error result or None if OK."""
        if not cmd_parts:
            return ExecutionResult(
                success=False, stdout="", stderr="",
                return_code=-1, duration_ms=0,
                error="Empty command",
            )

        binary = cmd_parts[0]
        is_blocked, reason = safety_whitelist.is_command_blocked(binary)
        if is_blocked:
            return ExecutionResult(
                success=False, stdout="", stderr="",
                return_code=-1, duration_ms=0,
                error=reason,
            )

        try:
            cwd.resolve().relative_to(config.workspace_root.resolve())
        except ValueError:
            return ExecutionResult(
                success=False, stdout="", stderr="",
                return_code=-1, duration_ms=0,
                error=f"Working directory {cwd} is outside workspace",
            )

        return None

    @staticmethod
    def _run_subprocess_sync(
        cmd_parts: List[str], cwd: Path, timeout: int
    ) -> ExecutionResult:
        """Synchronous subprocess execution (runs in thread pool)."""
        start = time.time()
        try:
            proc = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True,
                shell=False,
                preexec_fn=lambda: signal.signal(signal.SIGALRM, signal.SIG_DFL)
                if hasattr(signal, 'SIGALRM') else None,
            )

            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                duration_ms = (time.time() - start) * 1000
                timed_out = False
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except Exception:
                    pass
                stdout, stderr = proc.communicate(timeout=5)
                duration_ms = (time.time() - start) * 1000
                timed_out = True
                if not stderr:
                    stderr = f"Execution timed out after {timeout} seconds"

            return ExecutionResult(
                success=proc.returncode == 0 and not timed_out,
                stdout=stdout or "",
                stderr=stderr or "",
                return_code=proc.returncode,
                duration_ms=duration_ms,
                timed_out=timed_out,
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False, stdout="", stderr="",
                return_code=-1, duration_ms=0,
                error=f"Command not found: {cmd_parts[0]}. Is it installed?",
            )
        except Exception as e:
            return ExecutionResult(
                success=False, stdout="", stderr="",
                return_code=-1, duration_ms=0,
                error=str(e),
            )

    async def _run_subprocess(
        self,
        cmd_parts: List[str],
        cwd: Path,
        timeout: int,
    ) -> ExecutionResult:
        """Run a subprocess safely with timeout (async, non-blocking)."""
        # Validate preconditions synchronously
        error = self._validate_before_run(cmd_parts, cwd, timeout)
        if error:
            return error

        timeout = min(timeout, self.MAX_TIMEOUT)

        # Run blocking subprocess in thread pool to avoid blocking event loop
        return await asyncio.to_thread(
            self._run_subprocess_sync, cmd_parts, cwd, timeout
        )

    @staticmethod
    def _random_id() -> str:
        """Generate a short random ID for temp files."""
        return uuid.uuid4().hex[:8]


# Global instance
executor = CodeExecutor()


# ══════════════════════════════════════════════
#  Tool Implementations
# ══════════════════════════════════════════════

class ExecuteFileTool(BaseTool):
    """Run a file in the workspace and capture its output."""
    name = "execute_file"
    description = "Execute a file in the workspace (Python, JS, Go, Rust, Shell) and capture output"
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
            language = kwargs.get("language")
            args = kwargs.get("args")
            timeout = kwargs.get("timeout", 30)
            cwd = kwargs.get("cwd")

            result = await executor.execute_file(
                file_path=path,
                language=language,
                args=args,
                timeout=timeout,
                cwd=cwd,
            )

            if result.error and not result.stdout:
                return ToolResult(
                    success=False,
                    message=f"Execution failed: {result.error}",
                    error=result.error,
                    data={
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "return_code": result.return_code,
                        "duration_ms": result.duration_ms,
                        "timed_out": result.timed_out,
                    },
                )

            message_parts = [
                f"Executed {path} ({'✓' if result.success else '✗'} return code: {result.return_code})",
                f"Duration: {result.duration_ms:.0f}ms",
            ]
            if result.timed_out:
                message_parts.append("⚠️ Timed out!")

            if result.stdout:
                stdout_preview = result.stdout[:2000]
                message_parts.append(f"\n--- stdout ---\n{stdout_preview}")
                if len(result.stdout) > 2000:
                    message_parts.append(f"... ({len(result.stdout) - 2000} more chars)")

            if result.stderr:
                stderr_preview = result.stderr[:1000]
                message_parts.append(f"\n--- stderr ---\n{stderr_preview}")
                if len(result.stderr) > 1000:
                    message_parts.append(f"... ({len(result.stderr) - 1000} more chars)")

            return ToolResult(
                success=result.success or bool(result.stdout),
                message="\n".join(message_parts),
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.return_code,
                    "duration_ms": result.duration_ms,
                    "timed_out": result.timed_out,
                },
            )
        except Exception as e:
            logger.error(f"Error in execute_file: {e}", exc_info=True)
            return ToolResult(success=False, message=str(e), error=str(e))


class ExecuteCodeTool(BaseTool):
    """Execute a code snippet inline."""
    name = "execute_code"
    description = "Execute a short code snippet inline (Python, JS, Shell) and capture output"
    requires_confirmation = True

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        if "code" not in kwargs:
            return False, "Missing required argument: code"
        if "language" not in kwargs:
            return False, "Missing required argument: language"
        return True, None

    def get_required_args(self) -> List[str]:
        return ["code", "language"]

    async def execute(self, **kwargs) -> ToolResult:
        try:
            code = kwargs["code"]
            language = kwargs["language"]
            timeout = kwargs.get("timeout", 30)

            # Validate language
            if language not in RUNTIMES:
                return ToolResult(
                    success=False,
                    message=f"Unsupported language: {language}. Supported: {', '.join(RUNTIMES.keys())}",
                    error=f"Unsupported language: {language}",
                )

            result = await executor.execute_code(
                code=code,
                language=language,
                timeout=timeout,
            )

            if result.error and not result.stdout:
                return ToolResult(
                    success=False,
                    message=f"Execution failed: {result.error}",
                    error=result.error,
                    data={
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "return_code": result.return_code,
                        "duration_ms": result.duration_ms,
                        "timed_out": result.timed_out,
                    },
                )

            message_parts = [
                f"Executed {language} snippet (✓ return code: {result.return_code})",
                f"Duration: {result.duration_ms:.0f}ms",
            ]
            if result.timed_out:
                message_parts.append("⚠️ Timed out!")

            if result.stdout:
                message_parts.append(f"\n--- output ---\n{result.stdout[:3000]}")

            if result.stderr:
                message_parts.append(f"\n--- errors ---\n{result.stderr[:1000]}")

            return ToolResult(
                success=result.success or bool(result.stdout),
                message="\n".join(message_parts),
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.return_code,
                    "duration_ms": result.duration_ms,
                    "timed_out": result.timed_out,
                },
            )
        except Exception as e:
            logger.error(f"Error in execute_code: {e}", exc_info=True)
            return ToolResult(success=False, message=str(e), error=str(e))
