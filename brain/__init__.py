"""Jarvis brain layer."""

from jarvis.brain.ollama import OllamaClient, ollama_client
from jarvis.brain.chat import ChatManager, get_chat_manager, ConversationHistory, ConversationTurn
from jarvis.brain.parser import ResponseParser, response_parser, ParseResult, ToolRequest, MessageResponse
from jarvis.brain.agent import JarvisAgent, get_agent, AgentState, AgentResponse

__all__ = [
    "OllamaClient",
    "ollama_client",
    "ChatManager",
    "get_chat_manager",
    "ConversationHistory",
    "ConversationTurn",
    "ResponseParser",
    "response_parser",
    "ParseResult",
    "ToolRequest",
    "MessageResponse",
    "JarvisAgent",
    "get_agent",
    "AgentState",
    "AgentResponse",
]