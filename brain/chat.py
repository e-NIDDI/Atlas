"""Chat management for Jarvis brain layer."""

from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field

from jarvis.brain.ollama import OllamaClient, OllamaMessage
from jarvis.brain.parser import ResponseParser, ParseResult
from jarvis.logger import logger


@dataclass
class ConversationTurn:
    """Single turn in conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_tool_request: bool = False
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None


class ConversationHistory:
    """Manages conversation history."""
    
    def __init__(self, max_history: int = 50) -> None:
        """
        Initialize conversation history.
        
        Args:
            max_history: Maximum number of turns to keep
        """
        self.max_history = max_history
        self.turns: List[ConversationTurn] = []
        logger.info(f"Conversation history initialized (max {max_history} turns)")
    
    def add_turn(
        self,
        role: str,
        content: str,
        is_tool_request: bool = False,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict] = None
    ) -> None:
        """
        Add a turn to the conversation.
        
        Args:
            role: Role (user or assistant)
            content: Message content
            is_tool_request: Whether this was a tool request
            tool_name: Tool name if applicable
            tool_args: Tool arguments if applicable
        """
        turn = ConversationTurn(
            role=role,
            content=content,
            is_tool_request=is_tool_request,
            tool_name=tool_name,
            tool_args=tool_args
        )
        
        self.turns.append(turn)
        
        # Trim history if needed
        if len(self.turns) > self.max_history:
            self.turns = self.turns[-self.max_history:]
        
        logger.debug(f"Added {role} turn (total: {len(self.turns)})")
    
    def get_ollama_messages(self) -> List[OllamaMessage]:
        """
        Get conversation history in Ollama format.
        
        Returns:
            List of OllamaMessage objects
        """
        messages = []
        
        for turn in self.turns:
            messages.append(OllamaMessage(role=turn.role, content=turn.content))
        
        logger.debug(f"Converted {len(messages)} turns to Ollama format")
        return messages
    
    def get_recent_context(self, num_turns: int = 10) -> List[Dict[str, str]]:
        """
        Get recent conversation context.
        
        Args:
            num_turns: Number of recent turns to include
            
        Returns:
            List of message dictionaries
        """
        recent = self.turns[-num_turns:] if num_turns > 0 else self.turns
        return [
            {"role": turn.role, "content": turn.content}
            for turn in recent
        ]
    
    def clear(self) -> None:
        """Clear conversation history."""
        self.turns.clear()
        logger.info("Conversation history cleared")
    
    def get_last_user_message(self) -> Optional[str]:
        """
        Get the last user message.
        
        Returns:
            Last user message or None
        """
        for turn in reversed(self.turns):
            if turn.role == "user":
                return turn.content
        return None


class ChatManager:
    """Manages chat interactions with Ollama."""
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None) -> None:
        """
        Initialize chat manager.
        
        Args:
            ollama_client: Ollama client instance
        """
        self.ollama_client = ollama_client or OllamaClient()
        self.parser = ResponseParser()
        self.history = ConversationHistory()
        logger.info("Chat manager initialized")
    
    async def send_message(
        self,
        user_message: str,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response.
        
        Args:
            user_message: User's message
            stream: Whether to stream the response
            
        Yields:
            Response chunks
        """
        logger.info(f"Processing user message: {user_message[:100]}")
        
        # Add user message to history
        self.history.add_turn("user", user_message)
        
        # Get conversation history
        messages = self.history.get_ollama_messages()
        
        # Collect full response
        full_response = ""
        
        async for chunk in self.ollama_client.chat(messages, stream=stream):
            full_response += chunk
            yield chunk
        
        # Parse the response
        parse_result = self.parser.parse(full_response)
        
        # Add assistant response to history
        if parse_result.is_tool_request and parse_result.tool_request:
            self.history.add_turn(
                "assistant",
                full_response,
                is_tool_request=True,
                tool_name=parse_result.tool_request.tool,
                tool_args=parse_result.tool_request.args
            )
            logger.info(f"Tool request detected: {parse_result.tool_request.tool}")
        else:
            message_content = parse_result.message or full_response
            self.history.add_turn("assistant", message_content)
            logger.debug("Normal message response")
    
    async def send_message_complete(self, user_message: str) -> ParseResult:
        """
        Send a message and get complete parsed response.
        
        Args:
            user_message: User's message
            
        Returns:
            ParseResult object
        """
        logger.info(f"Processing user message (complete): {user_message[:100]}")
        
        # Add user message to history
        self.history.add_turn("user", user_message)
        
        # Get conversation history
        messages = self.history.get_ollama_messages()
        
        # Get complete response
        full_response = await self.ollama_client.chat_complete(messages)
        
        if not full_response:
            logger.warning("Empty response from Ollama")
            full_response = "I'm sorry, I didn't receive a response. Please try again."
        
        # Parse the response
        parse_result = self.parser.parse(full_response)
        
        # Add assistant response to history
        if parse_result.is_tool_request and parse_result.tool_request:
            self.history.add_turn(
                "assistant",
                full_response,
                is_tool_request=True,
                tool_name=parse_result.tool_request.tool,
                tool_args=parse_result.tool_request.args
            )
            logger.info(f"Tool request detected (complete): {parse_result.tool_request.tool}")
        else:
            message_content = parse_result.message or full_response
            self.history.add_turn("assistant", message_content)
            logger.debug("Normal message response (complete)")
        
        return parse_result
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history.clear()
        logger.info("Chat history cleared")
    
    def get_history(self) -> List[ConversationTurn]:
        """
        Get conversation history.
        
        Returns:
            List of conversation turns
        """
        return self.history.turns.copy()
    
    async def check_ollama_connection(self) -> bool:
        """
        Check if Ollama is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return await self.ollama_client.check_connection()
    
    async def close(self) -> None:
        """Close the chat manager."""
        await self.ollama_client.close()
        logger.info("Chat manager closed")


# Global chat manager instance
chat_manager: Optional[ChatManager] = None


def get_chat_manager() -> ChatManager:
    """
    Get or create the global chat manager instance.
    
    Returns:
        ChatManager instance
    """
    global chat_manager
    if chat_manager is None:
        chat_manager = ChatManager()
    return chat_manager