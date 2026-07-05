"""Confirmation dialogs for Jarvis UI."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Static,
    Button,
    Label,
    RichLog,
)
from textual.screen import ModalScreen
from textual.binding import Binding
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass

from jarvis.logger import logger


@dataclass
class ConfirmationRequest:
    """Request for user confirmation."""
    title: str
    message: str
    tool_name: str
    args: Dict[str, Any]
    risk_level: str = "medium"  # low, medium, high, critical


class ConfirmationDialog(ModalScreen[bool]):
    """Modal dialog for confirming tool execution."""
    
    CSS = """
    ConfirmationDialog {
        align: center middle;
    }
    
    #dialog_container {
        width: 80;
        height: 20;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }
    
    #dialog_title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    
    #dialog_message {
        margin-bottom: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    #dialog_details {
        background: $boost;
        padding: 1;
        margin-bottom: 1;
        border: solid $accent;
    }
    
    #button_container {
        height: 3;
        align: right middle;
    }
    
    Button {
        margin-left: 1;
    }
    
    .risk-low {
        color: $success;
    }
    
    .risk-medium {
        color: $warning;
    }
    
    .risk-high {
        color: $error;
    }
    
    .risk-critical {
        color: $error;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("y", "approve", "Yes", show=True),
        Binding("n", "reject", "No", show=True),
        Binding("escape", "reject", "Cancel", show=True),
    ]
    
    def __init__(
        self,
        request: ConfirmationRequest,
        callback: Optional[Callable[[bool], None]] = None
    ) -> None:
        """
        Initialize confirmation dialog.
        
        Args:
            request: Confirmation request details
            callback: Optional callback function(result: bool)
        """
        super().__init__()
        self.request = request
        self.callback = callback
        self.result_value: bool = False
    
    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        with Container(id="dialog_container"):
            yield Static(f"⚠️  {self.request.title}", id="dialog_title")
            yield Static(self.request.message, id="dialog_message")
            
            # Show details
            details = f"Tool: {self.request.tool_name}\n"
            details += f"Arguments: {self.request.args}\n"
            details += f"Risk Level: [{self.request.risk_level.upper()}]"
            yield Static(details, id="dialog_details")
            
            with Horizontal(id="button_container"):
                yield Button("Yes, Execute", id="yes_btn", variant="success")
                yield Button("No, Cancel", id="no_btn", variant="error")
    
    def on_mount(self) -> None:
        """Handle dialog mount."""
        # Focus the No button by default (safer option)
        self.query_one("#no_btn", Button).focus()
        logger.info(f"Confirmation dialog shown: {self.request.tool_name}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "yes_btn":
            self.action_approve()
        elif event.button.id == "no_btn":
            self.action_reject()
    
    def action_approve(self) -> None:
        """Approve the action."""
        self.result_value = True
        logger.info(f"User approved: {self.request.tool_name}")
        
        if self.callback:
            self.callback(True)
        
        self.dismiss(True)
    
    def action_reject(self) -> None:
        """Reject the action."""
        self.result_value = False
        logger.info(f"User rejected: {self.request.tool_name}")
        
        if self.callback:
            self.callback(False)
        
        self.dismiss(False)
    
    @staticmethod
    async def show(
        app: App,
        request: ConfirmationRequest
    ) -> bool:
        """
        Show confirmation dialog and wait for result.
        
        Args:
            app: Textual app instance
            request: Confirmation request
            
        Returns:
            True if approved, False if rejected
        """
        dialog = ConfirmationDialog(request)
        result = await app.push_screen_wait(dialog)
        return result if result is not None else False


class ApprovalManager:
    """Manages approval flow for tool execution."""
    
    def __init__(self) -> None:
        """Initialize approval manager."""
        self.pending_approvals: Dict[str, ConfirmationRequest] = {}
        self.approval_callbacks: Dict[str, Callable[[bool], None]] = {}
        logger.info("Approval manager initialized")
    
    def request_approval(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
        risk_level: str = "medium"
    ) -> ConfirmationRequest:
        """
        Create an approval request.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            reason: Reason for the action
            risk_level: Risk level (low, medium, high, critical)
            
        Returns:
            ConfirmationRequest object
        """
        request = ConfirmationRequest(
            title=f"Confirm Action: {tool_name}",
            message=reason,
            tool_name=tool_name,
            args=args,
            risk_level=risk_level
        )
        
        logger.info(f"Approval requested: {tool_name} (risk: {risk_level})")
        return request
    
    def requires_approval(self, tool_name: str, risk_level: str = "medium") -> bool:
        """
        Check if a tool requires approval.
        
        Args:
            tool_name: Name of the tool
            risk_level: Risk level
            
        Returns:
            True if approval required, False otherwise
        """
        # Critical and high risk always require approval
        if risk_level in ["critical", "high"]:
            return True
        
        # Medium risk requires approval for certain tools
        if risk_level == "medium":
            medium_risk_tools = {
                "create_project",
                "rename_project",
                "write_file",
                "create_file",
                "run_tests",
                "execute_command",
            }
            return tool_name in medium_risk_tools
        
        # Low risk tools don't require approval
        return False
    
    def get_risk_level(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Determine risk level for a tool execution.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            
        Returns:
            Risk level (low, medium, high, critical)
        """
        # Critical risk tools
        critical_tools = {
            "delete_project",
            "delete_file",
            "execute_command",
        }
        if tool_name in critical_tools:
            return "critical"
        
        # High risk tools
        high_risk_tools = {
            "write_file",
            "create_file",
            "run_tests",
        }
        if tool_name in high_risk_tools:
            return "high"
        
        # Medium risk tools
        medium_risk_tools = {
            "create_project",
            "rename_project",
            "git_commit",
            "git_push",
        }
        if tool_name in medium_risk_tools:
            return "medium"
        
        # Low risk (read-only operations)
        return "low"
    
    def format_args_for_display(self, args: Dict[str, Any]) -> str:
        """
        Format tool arguments for display in dialog.
        
        Args:
            args: Tool arguments
            
        Returns:
            Formatted string
        """
        if not args:
            return "No arguments"
        
        formatted = []
        for key, value in args.items():
            # Truncate long values
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            formatted.append(f"  {key}: {value}")
        
        return "\n".join(formatted)


# Global approval manager instance
approval_manager = ApprovalManager()