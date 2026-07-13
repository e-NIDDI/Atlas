# Jarvis AI Assistant — Deployment Guide

## Prerequisites

- **Python 3.12+** (`python3 --version`)
- **Ollama** installed and running (`ollama serve`)
- **A local LLM model** pulled in Ollama

## Quick Install

```bash
# 1. Clone or navigate to the jarvis directory
cd /home/edb/code/Atlas/jarvis

# 2. Install the package and dependencies
pip install -e .

# 3. Pull at least one Ollama model (recommended)
ollama pull qwen2.5:1.5b        # Default model (~1GB)
ollama pull nomic-embed-text     # For RAG embeddings (~274MB, optional)

# 4. Run Jarvis
jarvis
```

## Required Packages

The following Python packages are required (installed automatically via `pip install -e .`):

| Package | Purpose | Required |
|---------|---------|----------|
| `httpx` | HTTP client for Ollama API | Yes |
| `pydantic` | Data validation | Yes |
| `pyyaml` | YAML config parsing | Yes |
| `pypdf` | PDF document reading | Yes |
| `python-docx` | DOCX document reading | Yes |

## Folder Structure

```
jarvis/
├── jarvis/                      # Python package root
│   ├── __init__.py              # Package metadata
│   ├── app.py                   # CLI entry point
│   ├── config.py                # Configuration
│   ├── logger.py                # Logging setup
│   ├── brain/                   # LLM interaction layer
│   │   ├── agent.py             # Agent loop
│   │   ├── chat.py              # Chat management
│   │   ├── errors.py            # Error formatting
│   │   ├── intent.py            # Intent detection
│   │   ├── ollama.py            # Ollama client
│   │   ├── parser.py            # Response parsing
│   │   ├── prompts.py           # System prompts
│   │   └── sanitize.py          # Response sanitization
│   ├── cli/                     # CLI interface
│   │   ├── app.py               # Main CLI
│   │   ├── approval.py          # Confirmation prompts
│   │   └── display.py           # Terminal display
│   ├── memory/                  # Memory & RAG layer
│   │   ├── database.py          # SQLite database
│   │   ├── history.py           # Action/conversation history
│   │   ├── embeddings.py        # Embedding generation
│   │   ├── vector_store.py      # Vector database
│   │   └── rag.py               # RAG pipeline
│   ├── safety/                  # Safety layer
│   │   ├── paths.py             # Path validation
│   │   ├── validator.py         # Request validation
│   │   ├── whitelist.py         # Command whitelist
│   │   ├── permissions.py       # Permission system
│   │   └── audit.py             # Audit logging
│   ├── tools/                   # Tool implementations
│   │   ├── registry.py          # Tool registry
│   │   ├── dispatcher.py        # Tool dispatcher
│   │   ├── register_tools.py    # Tool registration
│   │   ├── filesystem.py        # Filesystem operations
│   │   ├── documents.py         # Document intelligence
│   │   ├── secretary.py         # Secretary features
│   │   ├── projects.py          # Project management
│   │   ├── commands.py          # Command execution
│   │   └── search.py            # Search utilities
│   └── ui/                      # (deprecated, CLI now)
├── logs/                        # Log files (auto-generated)
├── requirements.txt             # Dependencies
├── pyproject.toml               # Package config
├── INSTALL.md                   # This file
└── COMPREHENSIVE_REVIEW.md      # Architecture analysis
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_WORKSPACE` | `$HOME` | Workspace root directory |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Default LLM model |
| `OLLAMA_EMBEDDINGS_MODEL` | `nomic-embed-text` | Model for embeddings |
| `JARVIS_LOG_LEVEL` | `INFO` | Logging level |
| `JARVIS_SAFE_DIRS` | `` | Comma-separated safe directories |
| `JARVIS_RAG_ENABLED` | `false` | Enable RAG features |
| `JARVIS_MAX_FILE_SIZE_MB` | `50` | Max file read size |

## Configuration File

Jarvis supports a `config.yaml` in the workspace root:

```yaml
# ~/jarvis_config.yaml
workspace: /home/user/projects
ollama:
  url: http://localhost:11434
  model: llama3.2:3b
  embeddings_model: nomic-embed-text
safe_directories:
  - /home/user/projects
  - /home/user/documents
rag:
  enabled: false
  chunk_size: 512
  chunk_overlap: 32
```

## CLI Usage

```bash
# Interactive chat
jarvis

# Single message
jarvis ask "list my projects"

# Check status
jarvis status

# List available tools
jarvis tools

# Use a different model
jarvis -m llama3.2:3b

# Auto-approve actions (use with caution)
jarvis -y
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Test specific module
python -m pytest tests/test_filesystem.py -v

# Manual integration test
jarvis ask "create a folder called test_folder"
jarvis ask "create a file called test_folder/hello.txt with content 'Hello World'"
jarvis ask "read test_folder/hello.txt"
jarvis ask "list files in test_folder"
jarvis ask "get metadata for test_folder/hello.txt"
jarvis ask "delete test_folder/hello.txt"
jarvis ask "delete test_folder"
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'jarvis'"
```bash
pip install -e .
```

### "Cannot connect to Ollama"
```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### "Model not found"
```bash
ollama pull qwen2.5:1.5b
```

### "Package 'jarvis' not found in setup.py"
The `pyproject.toml` now uses `[tool.setuptools.packages.find]` which auto-discovers packages. Run:
```bash
pip install -e . --force-reinstall