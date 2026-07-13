"""Agent loop for Jarvis brain layer."""

from typing import Optional, Dict, Any, AsyncGenerator, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from jarvis.brain.chat import ChatManager, get_chat_manager
from jarvis.brain.parser import ResponseParser, ParseResult
from jarvis.brain.sanitize import should_buffer_response, sanitize_response, is_prompt_regurgitation, is_casual_chat
from jarvis.brain.intent import detect_tool_intent
from jarvis.tools.dispatcher import ToolDispatcher, DispatchResult
from jarvis.cli.approval import ConfirmationRequest
from jarvis.memory.history import HistoryManager
from jarvis.config import config
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
        auto_approve: bool = False,
        confirm_fn: Optional[Callable[[ConfirmationRequest], Awaitable[bool]]] = None,
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

        # Skip the LLM for obvious small-talk on small models
        if should_buffer_response(config.ollama_model):
            if is_casual_chat(user_message) and not detect_tool_intent(user_message):
                from jarvis.brain.sanitize import is_help_question
                from jarvis.brain.intent import casual_help_response
                reply = (
                    casual_help_response()
                    if is_help_question(user_message)
                    else (
                        "Hey! I'm Jarvis, your local workspace assistant. "
                        "I can help you manage projects and files. What's up?"
                    )
                )
                self.chat_manager.history.add_turn("user", user_message)
                self.chat_manager.history.add_turn("assistant", reply)
                yield reply
                self.state = AgentState.IDLE
                return

            intent = detect_tool_intent(user_message)
            if intent:
                self.state = AgentState.EXECUTING
                self.chat_manager.history.add_turn("user", user_message)
                dispatch_result = await self.tool_dispatcher.dispatch(
                    tool_name=intent.tool,
                    args=intent.args,
                    reason=intent.reason,
                    auto_approve=auto_approve,
                    confirm_fn=confirm_fn,
                )
                explanation = self._generate_explanation(dispatch_result)
                self.chat_manager.history.add_turn("assistant", explanation)
                yield explanation
                self.state = AgentState.IDLE
                return
        
        try:
            full_response = ""
            buffer_mode = should_buffer_response(config.ollama_model)
            streaming = not buffer_mode

            async for chunk in self.chat_manager.send_message(user_message, stream=True):
                full_response += chunk
                if buffer_mode:
                    continue
                stripped = full_response.lstrip()
                if stripped.startswith("{") and '"type"' in stripped:
                    streaming = False
                elif streaming:
                    yield chunk
            
            raw_response = full_response
            regurgitated = is_prompt_regurgitation(raw_response)
            full_response = sanitize_response(raw_response, user_message)
            parse_result = self.parser.parse(full_response)

            # Small-model fallback: route clear requests even if model garbled output
            if should_buffer_response(config.ollama_model):
                intent = detect_tool_intent(user_message)
                if intent and (regurgitated or not parse_result.is_tool_request):
                    parse_result = ParseResult(
                        is_tool_request=True,
                        tool_request=intent,
                        raw_response=raw_response,
                    )
            
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
                    auto_approve=auto_approve,
                    confirm_fn=confirm_fn,
                )
                
                # Generate explanation of what happened
                explanation = self._generate_explanation(dispatch_result)
                yield explanation
                
                self.current_tool_request = None
                self.state = AgentState.IDLE
            
            else:
                message = parse_result.message or full_response.strip()
                if buffer_mode or (not streaming and message):
                    yield message
                self.state = AgentState.IDLE
        
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            logger.error(error_msg, exc_info=True)
            self.state = AgentState.ERROR
            yield f"Error: {error_msg}"
    
    async def process_message_complete(
        self,
        user_message: str,
        auto_approve: bool = False,
        confirm_fn: Optional[Callable[[ConfirmationRequest], Awaitable[bool]]] = None,
    ) -> AgentResponse:
        """
        Process a user message and return complete response.
        
        Args:
            user_message: User's message
            auto_approve: Skip confirmation prompts
            confirm_fn: Async callback for approval prompts
            
        Returns:
            AgentResponse object
        """
        logger.info(f"Processing message (complete): {user_message[:100]}")
        self.state = AgentState.THINKING
        
        try:
            # Skip LLM for small models when intent is obvious
            if should_buffer_response(config.ollama_model):
                if is_casual_chat(user_message) and not detect_tool_intent(user_message):
                    from jarvis.brain.sanitize import is_help_question
                    from jarvis.brain.intent import casual_help_response
                    reply = (
                        casual_help_response()
                        if is_help_question(user_message)
                        else (
                            "Hey! I'm Jarvis, your local workspace assistant. "
                            "I can help you manage projects and files. What's up?"
                        )
                    )
                    self.chat_manager.history.add_turn("user", user_message)
                    self.chat_manager.history.add_turn("assistant", reply)
                    return AgentResponse(message=reply, state=AgentState.IDLE)

                intent = detect_tool_intent(user_message)
                if intent:
                    self.state = AgentState.EXECUTING
                    self.chat_manager.history.add_turn("user", user_message)
                    dispatch_result = await self.tool_dispatcher.dispatch(
                        tool_name=intent.tool,
                        args=intent.args,
                        reason=intent.reason,
                        auto_approve=auto_approve,
                        confirm_fn=confirm_fn,
                    )
                    explanation = self._generate_explanation(dispatch_result)
                    self.chat_manager.history.add_turn("assistant", explanation)
                    self.state = AgentState.IDLE
                    return AgentResponse(
                        message=explanation,
                        tool_executed=True,
                        tool_name=intent.tool,
                        tool_result=dispatch_result,
                        state=self.state,
                    )

            parse_result = await self.chat_manager.send_message_complete(user_message)

            if should_buffer_response(config.ollama_model) and not parse_result.is_tool_request:
                intent = detect_tool_intent(user_message)
                if intent:
                    parse_result = ParseResult(
                        is_tool_request=True,
                        tool_request=intent,
                        raw_response=parse_result.raw_response,
                    )
            
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
                    auto_approve=auto_approve,
                    confirm_fn=confirm_fn,
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