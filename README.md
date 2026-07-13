# Jarvis AI Assistant

A local AI workspace assistant that chats with Ollama and safely manages projects and files in a dedicated workspace.

## Features

- **CLI-first**: Simple interactive terminal — no TUI framework required
- **Local AI**: Connects to Ollama (tinyllama and other models)
- **Safe file management**: All operations confined to a dedicated workspace
- **Tool system**: Structured tool requests with validation and approval prompts
- **SQLite memory**: Persistent conversation and action history
- **Streaming responses**: Token-by-token output for normal chat

## Quick Start

```bash
# Install dependencies
pip install -e .

# Pull a model (if you haven't already)
ollama pull tinyllama

# Start Ollama (if not already running)
ollama serve

# Launch interactive chat
jarvis
```

## CLI Usage

```bash
# Interactive chat (default)
jarvis
jarvis chat

# Single message, then exit
jarvis ask "list my projects"

# Check Ollama connection and model availability
jarvis status

# List available tools
jarvis tools

# Options
jarvis -m tinyllama -w ~/my-workspace
jarvis -y ask "create a project called demo"   # auto-approve actions
jarvis --ollama-url http://localhost:11434
```

### In-chat commands

| Command     | Description                    |
|-------------|--------------------------------|
| `/help`     | Show help                      |
| `/clear`    | Clear conversation history     |
| `/projects` | List workspace projects        |
| `/tools`    | List available tools           |
| `/status`   | Check Ollama connection        |
| `/quit`     | Exit                           |

### Environment variables

| Variable           | Default                    |
|--------------------|----------------------------|
| `OLLAMA_URL`       | `http://localhost:11434`   |
| `OLLAMA_MODEL`     | `tinyllama`                |
| `JARVIS_WORKSPACE` | `~`                        |
| `JARVIS_LOG_LEVEL` | `INFO`                     |

## Architecture

```
jarvis/
├── app.py                 # Entry point
├── cli/                   # CLI interface
│   ├── app.py            # Main CLI + chat loop
│   ├── approval.py       # Tool approval prompts
│   └── display.py        # Terminal formatting
├── brain/                 # Ollama + agent loop
├── tools/                 # Tool registry + execution
├── safety/                # Path validation + whitelists
└── memory/                # SQLite persistence
```

## Safety

- Path validation keeps all file ops inside the workspace
- Command whitelisting blocks dangerous shell commands
- Destructive tool actions prompt for approval (`y/N`)
- Use `-y` only when you trust the action

## Requirements

- Python 3.12+
- Ollama running locally
- httpx >= 0.25.0
- pydantic >= 2.0.0

## License

MIT
