"""CLI approval flow for tool execution."""

from dataclasses import dataclass
from typing import Any, Callable, Awaitable, Dict, Optional

from jarvis.logger import logger


@dataclass
class ConfirmationRequest:
    """Request for user confirmation."""
    title: str
    message: str
    tool_name: str
    args: Dict[str, Any]
    risk_level: str = "medium"


RISK_COLORS = {
    "low": "\033[32m",
    "medium": "\033[33m",
    "high": "\033[31m",
    "critical": "\033[1;31m",
}
RESET = "\033[0m"


class ApprovalManager:
    """Manages approval flow for tool execution."""

    def request_approval(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
        risk_level: str = "medium",
    ) -> ConfirmationRequest:
        """Create an approval request."""
        request = ConfirmationRequest(
            title=f"Confirm Action: {tool_name}",
            message=reason,
            tool_name=tool_name,
            args=args,
            risk_level=risk_level,
        )
        logger.info(f"Approval requested: {tool_name} (risk: {risk_level})")
        return request

    def get_risk_level(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Determine risk level for a tool execution."""
        critical_tools = {"delete_project", "delete_file", "execute_command"}
        if tool_name in critical_tools:
            return "critical"

        high_risk_tools = {"write_file", "create_file", "run_tests"}
        if tool_name in high_risk_tools:
            return "high"

        medium_risk_tools = {"create_project", "rename_project", "git_commit", "git_push"}
        if tool_name in medium_risk_tools:
            return "medium"

        return "low"

    def format_args_for_display(self, args: Dict[str, Any]) -> str:
        """Format tool arguments for display."""
        if not args:
            return "  (none)"

        formatted = []
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            formatted.append(f"  {key}: {value}")
        return "\n".join(formatted)


def prompt_approval(request: ConfirmationRequest) -> bool:
    """Prompt user on the terminal to approve or reject an action."""
    color = RISK_COLORS.get(request.risk_level, "")
    print()
    print(f"{color}┌─ Action requires approval ─────────────────────────{RESET}")
    print(f"│ Tool:  {request.tool_name}")
    print(f"│ Risk:  {color}{request.risk_level.upper()}{RESET}")
    print(f"│ Why:   {request.message}")
    print("│ Args:")
    for line in ApprovalManager().format_args_for_display(request.args).splitlines():
        print(f"│ {line}")
    print(f"{color}└──────────────────────────────────────────────────{RESET}")

    while True:
        try:
            answer = input("Approve? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nRejected.")
            return False

        if answer in ("y", "yes"):
            logger.info(f"User approved: {request.tool_name}")
            return True
        if answer in ("n", "no", ""):
            logger.info(f"User rejected: {request.tool_name}")
            return False
        print("Please answer y or n.")


async def cli_confirm(request: ConfirmationRequest) -> bool:
    """Async wrapper for CLI approval prompt."""
    return prompt_approval(request)


# Global approval manager instance
approval_manager = ApprovalManager()
