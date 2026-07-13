"""Tool dispatcher for Jarvis."""

from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

from jarvis.tools.registry import ToolRegistry, ToolResult, tool_registry as global_tool_registry
import jarvis.tools.register_tools  # noqa: F401 — register tools on import
from jarvis.safety.validator import SafetyValidator
from jarvis.cli.approval import ApprovalManager, ConfirmationRequest, prompt_approval
from jarvis.memory.history import HistoryManager
from jarvis.logger import logger


class DispatchResult:
    """Result of tool dispatch."""
    
    def __init__(
        self,
        success: bool,
        message: str,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        approved: bool = False
    ) -> None:
        """
        Initialize dispatch result.
        
        Args:
            success: Whether the tool executed successfully
            message: Result message
            data: Result data
            error: Error message if failed
            approved: Whether the action was approved by user
        """
        self.success = success
        self.message = message
        self.data = data
        self.error = error
        self.approved = approved
    
    def __repr__(self) -> str:
        """String representation."""
        status = "SUCCESS" if self.success else "FAILED"
        return f"DispatchResult({status}, approved={self.approved}, message={self.message[:50]}...)"


class ToolDispatcher:
    """Dispatches tool requests with safety validation and approval flow."""
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        safety_validator: Optional[SafetyValidator] = None,
        approval_manager: Optional[ApprovalManager] = None,
        history_manager: Optional[HistoryManager] = None
    ) -> None:
        """
        Initialize tool dispatcher.
        
        Args:
            registry: Tool registry instance
            safety_validator: Safety validator instance
            approval_manager: Approval manager instance
            history_manager: History manager instance
        """
        self.tool_registry = registry or global_tool_registry
        self.safety_validator = safety_validator or SafetyValidator()
        self.approval_manager = approval_manager or ApprovalManager()
        self.history_manager = history_manager or HistoryManager()
        logger.info("Tool dispatcher initialized")
    
    async def dispatch(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
        auto_approve: bool = False,
        confirm_fn: Optional[Callable[[ConfirmationRequest], Awaitable[bool]]] = None,
    ) -> DispatchResult:
        """
        Dispatch a tool request.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            reason: Reason for the action
            auto_approve: Whether to skip confirmation
            confirm_fn: Async callback for approval prompts
            
        Returns:
            DispatchResult object
        """
        logger.info(f"Dispatching tool: {tool_name}")
        
        # Step 1: Validate the tool request
        validation_result = self.safety_validator.validate_tool_request(tool_name, args)
        
        if not validation_result.is_valid:
            error_msg = f"Validation failed: {validation_result.error_message}"
            logger.warning(error_msg)
            
            self.history_manager.log_action(
                tool=tool_name,
                arguments=args,
                approved=False,
                success=False,
                error=validation_result.error_message
            )
            
            return DispatchResult(
                success=False,
                message=error_msg,
                error=validation_result.error_message,
                approved=False
            )
        
        # Step 2: Check if approval is required
        requires_approval = validation_result.requires_confirmation and not auto_approve
        approved = not requires_approval
        
        if requires_approval:
            logger.info(f"Approval required for: {tool_name}")
            
            risk_level = self.approval_manager.get_risk_level(tool_name, args)
            request = self.approval_manager.request_approval(
                tool_name=tool_name,
                args=args,
                reason=reason,
                risk_level=risk_level
            )
            
            if confirm_fn:
                approved = await confirm_fn(request)
            else:
                approved = prompt_approval(request)
            
            if not approved:
                message = f"Action '{tool_name}' was rejected"
                logger.info(message)
                
                self.history_manager.log_action(
                    tool=tool_name,
                    arguments=args,
                    approved=False,
                    success=False,
                    error="User rejected action"
                )
                
                return DispatchResult(
                    success=False,
                    message=message,
                    error="User rejected action",
                    approved=False
                )
        
        # Step 3: Execute the tool
        logger.info(f"Executing tool: {tool_name}")
        
        try:
            result = await self.tool_registry.execute_tool(tool_name, **args)
            
            self.history_manager.log_action(
                tool=tool_name,
                arguments=args,
                approved=requires_approval or auto_approve,
                success=result.success,
                error=result.error,
                result=result.message
            )
            
            self.history_manager.log_conversation(
                role="system",
                content=f"Executed {tool_name}: {result.message}",
                is_tool_request=True,
                tool_name=tool_name,
                tool_args=str(args)
            )
            
            logger.info(f"Tool executed: {tool_name} - success={result.success}")
            
            return DispatchResult(
                success=result.success,
                message=result.message,
                data=result.data,
                error=result.error,
                approved=requires_approval or auto_approve
            )
            
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {e}"
            logger.error(error_msg, exc_info=True)
            
            self.history_manager.log_action(
                tool=tool_name,
                arguments=args,
                approved=requires_approval,
                success=False,
                error=str(e)
            )
            
            return DispatchResult(
                success=False,
                message=error_msg,
                error=str(e),
                approved=requires_approval
            )
    
    def get_available_tools(self) -> list[str]:
        """Get list of available tools."""
        return self.tool_registry.list_tools()
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a tool."""
        return self.tool_registry.get_tool_info(tool_name)


# Global tool dispatcher instance
tool_dispatcher = ToolDispatcher()
