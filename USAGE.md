# Jarvis CLI — Usage Guide

## Getting Started

```bash
pip install -e .
ollama pull tinyllama
jarvis
```

You'll see a banner with workspace/model info, then a `›` prompt. Type naturally or use slash commands.

## Examples

### Chat

```
› Hello, what can you do?
› Create a new project called my-app
› List all my projects
› Read README.md in my-app
```

### One-shot

```bash
jarvis ask "what projects do I have?"
jarvis -y ask "create a project called quick-test"
```

### Approval flow

When Jarvis wants to run a risky action (write file, create project, etc.):

```
┌─ Action requires approval ─────────────────────────
│ Tool:  create_project
│ Risk:  MEDIUM
│ Why:   User requested creation of a new project
│ Args:
│   name: my-app
└──────────────────────────────────────────────────
Approve? [y/N]:
```

Press `y` to approve, `Enter` or `n` to reject.

## Slash Commands

- `/help` — show commands
- `/clear` — reset conversation history
- `/projects` — list projects in workspace
- `/tools` — list available tools
- `/status` — check Ollama connection
- `/quit` — exit

## Configuration

**CLI flags:**
- `-m, --model` — Ollama model name
- `-w, --workspace` — workspace directory
- `--ollama-url` — Ollama API URL
- `-y, --yes` — auto-approve tool actions
- `-q, --quiet` — minimal output

**Environment:**
```bash
export OLLAMA_MODEL=tinyllama
export JARVIS_WORKSPACE=~/my-workspace  # optional; defaults to ~
jarvis
```

## Troubleshooting

**Cannot connect to Ollama**
```bash
ollama serve          # start the server
jarvis status         # verify connection
ollama pull tinyllama    # ensure model is available
```

**Model not found**
```bash
ollama list
ollama pull tinyllama
jarvis -m tinyllama
```

**Actions always rejected**
- Approval is required by default for write/create operations
- Type `y` at the prompt, or use `-y` flag

**Logs**
- `jarvis/logs/jarvis_YYYYMMDD.log`
