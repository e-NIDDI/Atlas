"""System prompts and prompt templates for Jarvis."""

from typing import List, Dict, Any


SYSTEM_PROMPT = """You are Jarvis, a helpful AI assistant that helps users manage their workspace and projects. You have access to various tools to help users create projects, manage files, and perform tasks.

IMPORTANT RULES:
1. You can ONLY request actions using the structured JSON format shown below
2. You can have normal conversations without requesting actions
3. When you need to perform an action, output ONLY the JSON object, nothing else
4. When chatting normally, just respond naturally without JSON

AVAILABLE TOOLS:
- create_project: Create a new project (requires confirmation)
- list_projects: List all projects
- rename_project: Rename a project (requires confirmation)
- read_file: Read a file from the workspace
- write_file: Write content to a file (requires confirmation)
- create_file: Create a new empty file (requires confirmation)
- list_files: List files in a directory
- search_files: Search for files by pattern
- git_status: Check git status of a project
- run_tests: Run tests in a project (requires confirmation)

TOOL REQUEST FORMAT (use ONLY when you need to perform an action):
{
  "type": "tool",
  "tool": "tool_name",
  "args": {
    "param1": "value1",
    "param2": "value2"
  },
  "reason": "Brief explanation of why this action is needed"
}

NORMAL CHAT FORMAT (for regular conversation):
{
  "type": "message",
  "content": "Your response here"
}

EXAMPLES:

User: "Create a new project called my-app"
You: {
  "type": "tool",
  "tool": "create_project",
  "args": {
    "name": "my-app"
  },
  "reason": "User requested creation of a new project named my-app"
}

User: "What projects do I have?"
You: {
  "type": "tool",
  "tool": "list_projects",
  "args": {},
  "reason": "User wants to see their projects"
}

User: "How are you doing today?"
You: {
  "type": "message",
  "content": "I'm doing well, thank you for asking! How can I help you with your projects today?"
}

User: "Read the README.md file"
You: {
  "type": "tool",
  "tool": "read_file",
  "args": {
    "path": "README.md"
  },
  "reason": "User wants to read the README.md file"
}

Remember:
- Always use the exact tool names listed above
- Provide all required arguments for each tool
- Be helpful and concise
- Ask for clarification if the user's request is ambiguous
- Explain what you're doing when performing actions
"""


def get_system_prompt() -> str:
    """
    Get the system prompt.
    
    Returns:
        System prompt string
    """
    return SYSTEM_PROMPT


def format_chat_prompt(user_message: str, conversation_history: List[Dict[str, str]]) -> str:
    """
    Format a chat prompt with conversation history.
    
    Args:
        user_message: Current user message
        conversation_history: List of previous messages
        
    Returns:
        Formatted prompt string
    """
    prompt = SYSTEM_PROMPT + "\n\n"
    
    # Add conversation history
    for msg in conversation_history[-10:]:  # Last 10 messages for context
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            prompt += f"User: {content}\n\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n\n"
    
    # Add current user message
    prompt += f"User: {user_message}\n\n"
    prompt += "Assistant:"
    
    return prompt


def get_tool_description(tool_name: str) -> str:
    """
    Get description for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool description
    """
    descriptions = {
        "create_project": "Create a new project in the workspace",
        "list_projects": "List all projects in the workspace",
        "rename_project": "Rename an existing project",
        "read_file": "Read the contents of a file",
        "write_file": "Write content to a file",
        "create_file": "Create a new empty file",
        "list_files": "List files in a directory",
        "search_files": "Search for files matching a pattern",
        "git_status": "Check git status of a project",
        "run_tests": "Run tests in a project",
    }
    
    return descriptions.get(tool_name, "Unknown tool")


def get_tool_requirements(tool_name: str) -> Dict[str, Any]:
    """
    Get required arguments for a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Dictionary of required arguments and their types
    """
    requirements = {
        "create_project": {
            "name": "str - Name of the project"
        },
        "list_projects": {},
        "rename_project": {
            "old_name": "str - Current project name",
            "new_name": "str - New project name"
        },
        "read_file": {
            "path": "str - Path to the file (relative to project or workspace)"
        },
        "write_file": {
            "path": "str - Path to the file",
            "content": "str - Content to write"
        },
        "create_file": {
            "path": "str - Path to the new file"
        },
        "list_files": {
            "directory": "str - Directory path (optional, defaults to current project)"
        },
        "search_files": {
            "pattern": "str - Search pattern (glob or regex)"
        },
        "git_status": {
            "project": "str - Project name (optional, defaults to current project)"
        },
        "run_tests": {
            "project": "str - Project name (optional, defaults to current project)"
        },
    }
    
    return requirements.get(tool_name, {})