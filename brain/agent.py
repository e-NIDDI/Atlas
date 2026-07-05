"""Agent loop for Jarvis brain layer."""

from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

from jarvis.brain.chat import ChatManager, get_chat_manager
from jarvis.brain.parser import ResponseParser, ParseResult
from jarvis.tools.dispatcher import ToolDispatcher, DispatchResult
from jarvis.tools.registry import ToolRegistry
from jarvis.safety.validator import SafetyValidator
from jarvis.safety.whitelist import SafetyWhitelist
from jarvis.ui.dialogs import ApprovalManager
from jarvis.memory.history import HistoryManager
from jarvis.memory.database import Database
from jarvis.logger import logger


class AgentState(Enum):
    """Agent state."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"


@dataclass
class AgentResponse:
    """Response from the agent."""
    message: str
    tool_executed: bool = False
    tool_name: Optional[str] = None
    tool_result: Optional[DispatchResult] = None
    state: AgentState = AgentState.IDLE


class JarvisAgent:
    """Main agent loop for Jarvis."""
    
    def __init__(
        self,
        chat_manager: Optional[ChatManager] = None,
        tool_dispatcher: Optional[ToolDispatcher] = None,
        history_manager: Optional[HistoryManager] = None
    ) -> None:
        """
        Initialize Jarvis agent.
        
        Args:
            chat_manager: Chat manager instance
            tool_dispatcher: Tool dispatcher instance
            history_manager: History manager instance
        """
        self.chat_manager = chat_manager or get_chat_manager()
        self.tool_dispatcher = tool_dispatcher or ToolDispatcher()
        self.history_manager = history_manager or HistoryManager()
        self.parser = ResponseParser()
        
        self.state = AgentState.IDLE
        self.current_tool_request = None
        
        logger.info("Jarvis agent initialized")
    
    async def process_message(
        self,
        user_message: str,
        auto_approve: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and generate response.
        
        Args:
            user_message: User's message
            auto_approve: Whether to auto-approve tool execution
            
        Yields:
            Response chunks
        """
        logger.info(f"Processing message: {user_message[:100]}")
        self.state = AgentState.THINKING
        
        try:
            # Send message to Ollama and stream response
            full_response = ""
            async for chunk in self.chat_manager.send_message(user_message, stream=True):
                full_response += chunk
                yield chunk
            
            # Parse the response
            parse_result = self.parser.parse(full_response)
            
            # Handle tool request
            if parse_result.is_tool_request and parse_result.tool_request:
                self.state = AgentState.EXECUTING
                self.current_tool_request = parse_result.tool_request
                
                logger.info(f"Tool request detected: {parse_result.tool_request.tool}")
                
                # Dispatch the tool
                dispatch_result = await self.tool_dispatcher.dispatch(
                    tool_name=parse_result.tool_request.tool,
                    args=parse_result.tool_request.args,
                    reason=parse_result.tool_request.reason,
                    auto_approve=auto_approve
                )
                
                # Generate explanation of what happened
                explanation = self._generate_explanation(dispatch_result)
                yield explanation
                
                self.current_tool_request = None
                self.state = AgentState.IDLE
            
            else:
                # Normal message
                self.state = AgentState.IDLE
        
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            logger.error(error_msg, exc_info=True)
            self.state = AgentState.ERROR
            yield f"Error: {error_msg}"
    
    async def process_message_complete(self, user_message: str) -> AgentResponse:
        """
        Process a user message and return complete response.
        
        Args:
            user_message: User's message
            
        Returns:
            AgentResponse object
        """
        logger.info(f"Processing message (complete): {user_message[:100]}")
        self.state = AgentState.THINKING
        
        try:
            # Send message to Ollama
            parse_result = await self.chat_manager.send_message_complete(user_message)
            
            # Handle tool request
            if parse_result.is_tool_request and parse_result.tool_request:
                self.state = AgentState.EXECUTING
                self.current_tool_request = parse_result.tool_request
                
                logger.info(f"Tool request detected (complete): {parse_result.tool_request.tool}")
                
                # Dispatch the tool
                dispatch_result = await self.tool_dispatcher.dispatch(
                    tool_name=parse_result.tool_request.tool,
                    args=parse_result.tool_request.args,
                    reason=parse_result.tool_request.reason,
                    auto_approve=False
                )
                
                # Generate explanation
                explanation = self._generate_explanation(dispatch_result)
                
                self.current_tool_request = None
                self.state = AgentState.IDLE
                
                return AgentResponse(
                    message=explanation,
                    tool_executed=True,
                    tool_name=parse_result.tool_request.tool,
                    tool_result=dispatch_result,
                    state=self.state
                )
            
            else:
                # Normal message
                message = parse_result.message or parse_result.raw_response
                self.state = AgentState.IDLE
                
                return AgentResponse(
                    message=message,
                    tool_executed=False,
                    state=self.state
                )
        
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            logger.error(error_msg, exc_info=True)
            self.state = AgentState.ERROR
            
            return AgentResponse(
                message=f"Error: {error_msg}",
                tool_executed=False,
                state=self.state
            )
    
    def _generate_explanation(self, dispatch_result: DispatchResult) -> str:
        """
        Generate human-readable explanation of tool execution.
        
        Args:
            dispatch_result: Tool dispatch result
            
        Returns:
            Explanation string
        """
        if dispatch_result.success:
            if dispatch_result.approved:
                return f"✓ Action completed: {dispatch_result.message}"
            else:
                return f"✓ Action completed (auto-approved): {dispatch_result.message}"
        else:
            if dispatch_result.error and "rejected" in dispatch_result.error.lower():
                return f"✗ Action was rejected: {dispatch_result.message}"
            else:
                return f"✗ Action failed: {dispatch_result.message}"
    
    async def process_message_with_ui(
        self,
        user_message: str,
        app: Any  # Textual app instance
    ) -> AgentResponse:
        """
        Process a user message with UI confirmation dialogs.
        
        Args:
            user_message: User's message
            app: Textual app instance
            
        Returns:
            AgentResponse object
        """
        logger.info(f"Processing message with UI: {user_message[:100]}")
        self.state = AgentState.THINKING
        
        try:
            # Send message to Ollama
            parse_result = await self.chat_manager.send_message_complete(user_message)
            
            # Handle tool request
            if parse_result.is_tool_request and parse_result.tool_request:
                self.state = AgentState.WAITING_APPROVAL
                self.current_tool_request = parse_result.tool_request
                
                logger.info(f"Tool request detected (UI): {parse_result.tool_request.tool}")
                
                # Dispatch with UI confirmation
                dispatch_result = await self.tool_dispatcher.dispatch_with_ui(
                    tool_name=parse_result.tool_request.tool,
                    args=parse_result.tool_request.args,
                    reason=parse_result.tool_request.reason,
                    app=app
                )
                
                # Generate explanation
                explanation = self._generate_explanation(dispatch_result)
                
                self.current_tool_request = None
                self.state = AgentState.IDLE
                
                return AgentResponse(
                    message=explanation,
                    tool_executed=True,
                    tool_name=parse_result.tool_request.tool,
                    tool_result=dispatch_result,
                    state=self.state
                )
            
            else:
                # Normal message
                message = parse_result.message or parse_result.raw_response
                self.state = AgentState.IDLE
                
                return AgentResponse(
                    message=message,
                    tool_executed=False,
                    state=self.state
                )
        
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            logger.error(error_msg, exc_info=True)
            self.state = AgentState.ERROR
            
            return AgentResponse(
                message=f"Error: {error_msg}",
                tool_executed=False,
                state=self.state
            )
    
    def get_state(self) -> AgentState:
        """
        Get current agent state.
        
        Returns:
            Current agent state
        """
        return self.state
    
    def get_current_tool_request(self) -> Optional[Any]:
        """
        Get current tool request if any.
        
        Returns:
            Current tool request or None
        """
        return self.current_tool_request
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.chat_manager.clear_history()
        logger.info("Agent history cleared")
    
    async def check_ollama_connection(self) -> bool:
        """
        Check if Ollama is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return await self.chat_manager.check_ollama_connection()
    
    async def close(self) -> None:
        """Close the agent and cleanup resources."""
        await self.chat_manager.close()
        logger.info("Jarvis agent closed")


# Global agent instance
agent: Optional[JarvisAgent] = None


def get_agent() -> JarvisAgent:
    """
    Get or create the global agent instance.
    
    Returns:
        JarvisAgent instance
    """
    global agent
    if agent is None:
        agent = JarvisAgent()
    return agent