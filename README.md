# Jarvis AI Assistant

A production-quality local AI assistant built with Python that chats with a local Ollama model while safely managing files inside a dedicated workspace.

## Features

- **Terminal-based UI**: Built with Textual for a modern terminal interface
- **Local AI**: Connects to Ollama for local LLM inference
- **Safe File Management**: All file operations are confined to a dedicated workspace
- **Tool System**: Structured tool requests with validation and approval flow
- **SQLite Memory**: Persistent conversation and action history
- **Safety First**: Path validation, command whitelisting, and user confirmations

## Architecture

```
jarvis/
├── app.py                 # Main entry point
├── config.py              # Configuration settings
├── logger.py              # Logging configuration
├── requirements.txt       # Python dependencies
│
├── ui/                    # Textual UI layer
│   ├── app.py            # Main application
│   ├── dialogs.py        # Confirmation dialogs
│   └── __init__.py
│
├── brain/                 # AI/LLM layer
│   ├── ollama.py         # Ollama client
│   ├── chat.py           # Chat management
│   ├── parser.py         # Response parser
│   ├── prompts.py        # System prompts
│   ├── agent.py          # Agent loop
│   └── __init__.py
│
├── tools/                 # Tool execution layer
│   ├── registry.py       # Tool registry
│   ├── projects.py       # Project management
│   ├── files.py          # File operations
│   ├── commands.py       # Command execution
│   ├── search.py         # Search tools
│   ├── dispatcher.py     # Tool dispatcher
│   ├── register_tools.py # Tool registration
│   └── __init__.py
│
├── safety/                # Safety validation layer
│   ├── paths.py          # Path validation
│   ├── whitelist.py      # Command whitelist
│   ├── validator.py      # Safety validator
│   └── __init__.py
│
├── memory/                # SQLite database layer
│   ├── database.py       # Database manager
│   ├── history.py        # History management
│   └── __init__.py
│
├── workspace/             # User workspace (created at runtime)
└── logs/                  # Application logs (created at runtime)
```

## Installation

1. **Clone or download the project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install and run Ollama**:
   - Download from https://ollama.ai/
   - Pull a model: `ollama pull llama2`
   - Ensure Ollama is running on `http://localhost:11434`

4. **Run Jarvis**:
   ```bash
   python -m jarvis.app
   ```

## Configuration

Edit `jarvis/config.py` to customize:

- `workspace_root`: Where projects are stored (default: `~/JarvisWorkspace`)
- `ollama_url`: Ollama API URL (default: `http://localhost:11434`)
- `ollama_model`: Model to use (default: `llama2`)
- `log_level`: Logging level (default: `INFO`)

## Usage

### Basic Chat
Simply type your message and press Enter or click Send.

### Tool Requests
Jarvis can perform actions using tools. When a tool requires confirmation, you'll see a dialog.

Example requests:
- "Create a new project called my-app"
- "List all my projects"
- "Read the README.md file"
- "Search for all Python files"

### Safety Features

- **Path Validation**: All file operations are confined to the workspace
- **Command Whitelisting**: Only safe commands are allowed
- **User Confirmation**: Destructive operations require approval
- **Blocked Commands**: Dangerous commands like `rm`, `shutdown`, `curl` are blocked

### Available Tools

**Project Management:**
- `create_project`: Create a new project (requires confirmation)
- `list_projects`: List all projects
- `rename_project`: Rename a project (requires confirmation)

**File Operations:**
- `read_file`: Read a file
- `write_file`: Write content to a file (requires confirmation)
- `create_file`: Create an empty file (requires confirmation)
- `list_files`: List files in a directory
- `search_files`: Search for files by pattern

**Commands:**
- `git_status`: Check git status
- `run_tests`: Run tests (requires confirmation)

## Development

### Project Structure

The project follows a layered architecture:

1. **UI Layer**: Textual-based terminal interface
2. **Brain Layer**: Ollama integration and chat management
3. **Tools Layer**: Tool registry and execution
4. **Safety Layer**: Validation and whitelisting
5. **Memory Layer**: SQLite database for persistence

### Adding New Tools

1. Create a new tool class inheriting from `BaseTool` in `jarvis/tools/`
2. Implement the `execute` method
3. Register the tool in `jarvis/tools/register_tools.py`

### Logging

Logs are stored in:
- `jarvis/logs/jarvis_YYYYMMDD.log` - All logs
- `jarvis/logs/jarvis_errors_YYYYMMDD.log` - Errors only

## Safety & Security

Jarvis is designed with security in mind:

- **No arbitrary code execution**: Only whitelisted commands can run
- **Workspace isolation**: All file operations are confined to the workspace
- **Path traversal prevention**: Paths are validated to prevent escaping the workspace
- **User confirmation**: Destructive operations require explicit approval
- **Command blocking**: Dangerous commands are completely blocked

## Requirements

- Python 3.12+
- Ollama (running locally)
- Textual >= 0.44.0
- httpx >= 0.25.0
- pydantic >= 2.0.0

## License

MIT License

## Contributing

Contributions are welcome! Please ensure all code follows PEP 8 and includes proper type hints and docstrings.